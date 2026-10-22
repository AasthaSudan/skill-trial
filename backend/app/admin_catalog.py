"""Administration for versioned learning content and activity rewards."""
import re
from fastapi import APIRouter, Request
from sqlalchemy import select

from .db import tx, now
from .models import LearningResource, BadgeDefinition, User
from .resources import resource_view, validate_resource, check_link
from .game import BADGE_METRICS, BADGE_RULES, badge_snapshot, evaluate_badges
from .security import auth, audit, fail
from .service import LOCK

router = APIRouter(prefix='/api/v1/admin')
RESOURCE_FIELDS = {'slug', 'skill', 'competency', 'competencies', 'title', 'body', 'kind', 'url', 'difficulty', 'estimated_minutes', 'checks', 'question', 'options', 'answer', 'challenge_id'}

def resource_payload(body, db):
    if set(body) - RESOURCE_FIELDS:fail('INVALID_FIELD', 'The resource contains an unsupported field.', 422)
    report = validate_resource(body, db)
    if not report['ok']:fail('RESOURCE_INVALID', 'Complete the resource requirements before saving.', 422, checks=report['checks'])
    competencies = body.get('competencies', [body.get('competency')])
    checks = body.get('checks')
    if checks is None:checks = [{'question': body['question'], 'options': body['options'], 'answer': body['answer']}] if body.get('question') else []
    details = {'kind': body.get('kind', 'guide'), 'competencies': competencies,
               'url': body.get('url', '').strip(), 'difficulty': body.get('difficulty', 'beginner'),
               'estimated_minutes': body.get('estimated_minutes', 5), 'challenge_id': body.get('challenge_id'),
               'checks': [{'question': q['question'].strip(), 'options': [x.strip() for x in q['options']], 'answer': q['answer']} for q in checks]}
    first = details['checks'][0] if details['checks'] else {'question': '', 'options': [], 'answer': 0}
    return {'skill': body['skill'], 'competency': competencies[0], 'title': body['title'].strip(),
            'body': body.get('body', '').strip(), **first, 'details': details}, report

@router.get('/resources')
def resources(request: Request):
    with tx() as db:
        auth(db, request, 'content.read')
        return [resource_view(row) for row in db.scalars(select(LearningResource).order_by(LearningResource.skill, LearningResource.slug, LearningResource.version.desc()))]

@router.post('/resources')
def create_resource(body: dict, request: Request):
    with LOCK, tx() as db:
        user = auth(db, request, 'content.manage')
        fields, report = resource_payload(body, db)
        slug = body.get('slug') or f"{fields['skill']}-{fields['competency']}-resource"
        if not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,79}', slug):fail('INVALID_SLUG', 'Use a lowercase resource slug.', 422)
        versions = list(db.scalars(select(LearningResource.version).where(LearningResource.slug == slug)))
        row = LearningResource(slug=slug, version=max(versions, default=0) + 1, **fields, status='draft', validation=report, author=user.id)
        db.add(row);db.flush();audit(db, user, 'learning_resource.created', row.id)
        return resource_view(row)

@router.patch('/resources/{id}')
def edit_resource(id: str, body: dict, request: Request):
    with LOCK, tx() as db:
        user = auth(db, request, 'content.manage');row = db.get(LearningResource, id)
        if not row:fail('NOT_FOUND', 'Learning resource not found.', 404)
        if row.status != 'draft':fail('NEW_VERSION_REQUIRED', 'Create a new revision to edit a reviewed or published resource.', 409)
        if body.get('slug', row.slug) != row.slug:fail('IMMUTABLE_SLUG', 'Keep the resource slug when editing a draft.', 422)
        fields, report = resource_payload(body, db)
        for key, value in fields.items():setattr(row, key, value)
        row.validation = report;row.reviewer = None;row.author = user.id
        audit(db, user, 'learning_resource.updated', row.id)
        return resource_view(row)

@router.delete('/resources/{id}')
def delete_resource(id: str, request: Request):
    with LOCK, tx() as db:
        user = auth(db, request, 'content.manage');row = db.get(LearningResource, id)
        if not row:fail('NOT_FOUND', 'Learning resource not found.', 404)
        if row.status != 'draft':fail('ARCHIVE_REQUIRED', 'Archive reviewed or published resources instead.', 409)
        db.delete(row);audit(db, user, 'learning_resource.deleted', id)
        return {'ok': True}

@router.post('/resources/{id}/{action}')
def resource_action(id: str, action: str, request: Request):
    permissions = {'validate': 'content.validate', 'review': 'content.review', 'publish': 'content.publish', 'unpublish': 'content.publish', 'archive': 'content.publish', 'check-link': 'content.validate'}
    if action not in permissions:fail('NOT_FOUND', 'Action not found.', 404)
    with LOCK, tx() as db:
        user = auth(db, request, permissions[action]);row = db.get(LearningResource, id)
        if not row:fail('NOT_FOUND', 'Learning resource not found.', 404)
        if action == 'check-link':
            url = (row.details or {}).get('url')
            if not url:fail('NO_RESOURCE_LINK', 'This resource has no external URL.', 422)
        elif action == 'validate':
            if row.status != 'draft':fail('INVALID_TRANSITION', 'Only draft resources can be validated.', 409)
            row.validation = validate_resource(resource_view(row), db, legacy='checks' not in (row.details or {}))
            row.status = 'validated' if row.validation['ok'] else 'draft'
        elif action == 'review':
            if row.status != 'validated':fail('VALIDATION_REQUIRED', 'Validate this resource before independent review.', 409)
            if row.author == user.id:fail('REVIEWER_MUST_DIFFER', 'A different administrator must review this resource.', 409)
            row.reviewer = user.id;row.status = 'reviewed'
        elif action == 'publish':
            if row.status != 'reviewed' or not row.reviewer:fail('REVIEW_REQUIRED', 'Independent review is required before publication.', 409)
            if not validate_resource(resource_view(row), db, legacy='checks' not in (row.details or {}))['ok']:fail('RESOURCE_INVALID', 'Resource requirements changed; create a corrected revision.', 409)
            for old in db.scalars(select(LearningResource).where(LearningResource.slug == row.slug, LearningResource.status == 'published')):old.status = 'archived'
            row.status = 'published'
        elif action == 'archive':row.status = 'archived'
        else:row.status = 'unpublished'
        if action != 'check-link':
            audit(db, user, 'learning_resource.' + action, row.id)
            return resource_view(row)
        actor_id = user.id
    result = check_link(url)
    with LOCK, tx() as db:
        row = db.get(LearningResource, id)
        if not row:fail('NOT_FOUND', 'Learning resource not found.', 404)
        row.details = {**(row.details or {}), **result}
        audit(db, db.get(User, actor_id), 'learning_resource.link_checked', id)
        return resource_view(row)

def badge_view(row):
    return {'slug': row.slug, 'name': row.name, 'description': row.description, 'icon': row.icon,
            'metric': row.metric, 'rule': row.metric, 'thresholds': row.thresholds, 'params': {'thresholds': row.thresholds},
            'enabled': row.enabled, 'status': 'active' if row.enabled else 'archived',
            'category': (row.details or {}).get('category', 'behavior'), 'version': (row.details or {}).get('version', 1),
            'history': (row.details or {}).get('history', []), 'author': row.author, 'created': row.created, 'updated': row.updated}

def validate_badge(body, creating=False):
    allowed = {'name', 'description', 'icon', 'metric', 'thresholds', 'enabled', 'status', 'category', 'version'} | ({'slug'} if creating else set())
    if not body or set(body) - allowed:fail('INVALID_FIELD', 'The badge contains an unsupported field.', 422)
    if creating and not {'slug', 'name', 'description', 'metric', 'thresholds'} <= set(body):fail('INVALID_BADGE', 'Provide a slug, name, description, rule, and thresholds.', 422)
    for key, minimum, maximum in [('name', 3, 80), ('description', 8, 240)]:
        if key in body and (not isinstance(body[key], str) or not minimum <= len(body[key].strip()) <= maximum):fail('INVALID_BADGE', f'Check the badge {key} length.', 422)
    if 'icon' in body and body['icon'] not in ['Award', 'Sparkles', 'Code2', 'ScanLine', 'ShieldCheck', 'Flame']:fail('INVALID_BADGE', 'Choose a supported icon.', 422)
    if 'category' in body and body['category'] not in ['skill', 'behavior', 'milestone']:fail('INVALID_BADGE', 'Choose a supported category.', 422)
    if 'metric' in body and (not isinstance(body['metric'], str) or body['metric'] not in BADGE_METRICS):fail('INVALID_BADGE_METRIC', 'Choose a rule from the registry.', 422)
    if 'thresholds' in body:
        items = body['thresholds']
        if not isinstance(items, list) or not 1 <= len(items) <= 3 or any(not isinstance(x, int) or isinstance(x, bool) or not 1 <= x <= 100000 for x in items) or items != sorted(set(items)):fail('INVALID_BADGE_THRESHOLDS', 'Use one to three increasing positive tier thresholds.', 422)
    if 'enabled' in body and not isinstance(body['enabled'], bool):fail('INVALID_BADGE', 'Enabled must be true or false.', 422)
    if 'status' in body and body['status'] not in ['active', 'archived']:fail('INVALID_BADGE', 'Choose active or archived.', 422)
    if creating and (not isinstance(body['slug'], str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,59}', body['slug'])):fail('INVALID_SLUG', 'Use a lowercase badge slug.', 422)

@router.get('/badge-rules')
def badge_rules(request: Request):
    with tx() as db:auth(db, request, 'content.read');return list(BADGE_RULES.values())

@router.get('/badges')
def badges(request: Request):
    with tx() as db:
        auth(db, request, 'content.read')
        return [badge_view(row) for row in db.scalars(select(BadgeDefinition).order_by(BadgeDefinition.created, BadgeDefinition.slug))]

@router.post('/badges')
def create_badge(body: dict, request: Request):
    validate_badge(body, True)
    with LOCK, tx() as db:
        user = auth(db, request, 'content.manage')
        if db.get(BadgeDefinition, body['slug']):fail('BADGE_EXISTS', 'That badge slug already exists.', 409)
        row = BadgeDefinition(slug=body['slug'], name=body['name'].strip(), description=body['description'].strip(), icon=body.get('icon', 'Award'), metric=body['metric'], thresholds=body['thresholds'], enabled=body.get('status', 'active') == 'active' and body.get('enabled', True), details={'version': 1, 'category': body.get('category', 'behavior'), 'history': []}, author=user.id)
        db.add(row);db.flush();audit(db, user, 'badge.created', row.slug)
        return badge_view(row)

@router.patch('/badges/{slug}')
def update_badge(slug: str, body: dict, request: Request):
    validate_badge(body)
    with LOCK, tx() as db:
        user = auth(db, request, 'content.manage');row = db.get(BadgeDefinition, slug)
        if not row:fail('NOT_FOUND', 'Badge definition not found.', 404)
        details = dict(row.details or {});version = details.get('version', 1)
        if 'version' in body and body['version'] != version:fail('STALE_BADGE_VERSION', 'This badge changed. Reload before editing.', 409)
        changed = any(key in body and body[key] != getattr(row, key) for key in ['metric', 'thresholds'])
        # Materialize legacy earned rewards using the old rules before changing them.
        if changed or body.get('enabled') is False or body.get('status') == 'archived':
            for candidate in db.scalars(select(User)):evaluate_badges(db, candidate, notify=False, definitions=[row])
        if changed:
            details['history'] = [*details.get('history', []), badge_snapshot(row)]
            details['version'] = version + 1
        if 'category' in body:details['category'] = body['category']
        for key in ['name', 'description', 'icon', 'metric', 'thresholds', 'enabled']:
            if key in body:setattr(row, key, body[key].strip() if isinstance(body[key], str) else body[key])
        if 'status' in body:row.enabled = body['status'] == 'active'
        row.details = details;row.updated = now()
        audit(db, user, 'badge.rule_version_created' if changed else 'badge.updated', slug)
        return badge_view(row)
