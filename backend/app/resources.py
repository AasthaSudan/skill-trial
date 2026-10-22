"""Versioned resource metadata, quick checks, and bounded HTTPS link checks."""
import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urlsplit, urljoin

from sqlalchemy import select
from .catalog import skill
from .db import now
from .models import Challenge, LearningResource

KINDS = {'article', 'video', 'guide', 'interactive', 'practice_challenge'}

def resource_details(row):
    details = dict(row.details or {})
    details.setdefault('kind', 'guide')
    details.setdefault('competencies', [row.competency])
    details.setdefault('difficulty', 'beginner')
    details.setdefault('estimated_minutes', 5)
    # Preserve already-published single-question guides and old path snapshots.
    details.setdefault('checks', [{'question': row.question, 'options': row.options, 'answer': row.answer}] if row.question else [])
    details.setdefault('url', '')
    details.setdefault('challenge_id', None)
    details.setdefault('link_status', 'unchecked' if details['url'] else 'not_applicable')
    return details

def resource_view(row):
    return {'id': row.id, 'slug': row.slug, 'version': row.version, 'skill': row.skill,
            'competency': row.competency, 'title': row.title, 'body': row.body,
            'question': row.question, 'options': row.options, 'answer': row.answer,
            'status': row.status, 'validation': row.validation, 'author': row.author,
            'reviewer': row.reviewer, 'created': row.created, **resource_details(row)}

def https_url(value):
    if not isinstance(value, str) or len(value) > 2000 or any(ord(c) < 33 for c in value):
        return False
    try:
        url = urlsplit(value)
        return bool(url.scheme == 'https' and url.hostname and '.' in url.hostname
                    and not url.username and not url.password and url.port in (None, 443)
                    and not url.hostname.endswith(('.local', '.localhost')))
    except ValueError:
        return False

def validate_resource(body, db=None, legacy=False):
    checks = []
    known = skill(body.get('skill'))
    competencies = body.get('competencies', [body.get('competency')])
    kind = body.get('kind', 'guide')
    questions = body.get('checks')
    if questions is None:
        questions = [{'question': body.get('question'), 'options': body.get('options'), 'answer': body.get('answer')}] if body.get('question') else []
    checks.append({'name': 'Known skill and competencies', 'passed': bool(known and isinstance(competencies, list) and 1 <= len(competencies) <= 12 and all(isinstance(c, str) and c in known['competencies'] for c in competencies) and len(set(competencies)) == len(competencies))})
    checks.append({'name': 'Title and resource kind', 'passed': isinstance(body.get('title'), str) and 5 <= len(body['title'].strip()) <= 120 and isinstance(kind, str) and kind in KINDS})
    text = body.get('body', '')
    checks.append({'name': 'Markdown content or HTTPS link', 'passed': isinstance(text, str) and len(text) <= 8000 and isinstance(body.get('url', ''), str) and (kind == 'practice_challenge' or bool(https_url(body.get('url', ''))) or len(text.strip()) >= 80) and (not body.get('url') or https_url(body['url']))})
    minutes = body.get('estimated_minutes', 5)
    checks.append({'name': 'Difficulty and duration', 'passed': body.get('difficulty', 'beginner') in ['beginner', 'intermediate', 'advanced'] and isinstance(minutes, int) and not isinstance(minutes, bool) and 1 <= minutes <= 240})
    valid_questions = isinstance(questions, list) and (len(questions) == 0 or (1 if legacy else 2) <= len(questions) <= 5)
    if valid_questions:
        for q in questions:
            if not isinstance(q, dict):valid_questions = False;break
            options = q.get('options')
            valid_questions = bool(isinstance(q.get('question'), str) and 10 <= len(q['question'].strip()) <= 240 and isinstance(options, list) and 2 <= len(options) <= 5 and all(isinstance(x, str) and 1 <= len(x.strip()) <= 250 for x in options) and len({x.strip() for x in options}) == len(options) and isinstance(q.get('answer'), int) and not isinstance(q['answer'], bool) and 0 <= q['answer'] < len(options))
            if not valid_questions:break
    checks.append({'name': 'Optional quick check: two to five valid questions', 'passed': valid_questions})
    if kind == 'practice_challenge':
        challenge = db.get(Challenge, body.get('challenge_id')) if db and isinstance(body.get('challenge_id'), str) else None
        checks.append({'name': 'Published practice challenge for this skill and competencies', 'passed': bool(challenge and challenge.pool == 'practice' and challenge.status == 'published' and challenge.skill == body.get('skill') and isinstance(competencies, list) and set(competencies) <= set(challenge.content.get('competencies', [])))})
    return {'ok': all(c['passed'] for c in checks), 'checks': checks}

def published_resources(db, slug, competency):
    return [row for row in db.scalars(select(LearningResource).where(LearningResource.skill == slug, LearningResource.status == 'published').order_by(LearningResource.created.desc(), LearningResource.version.desc()))
            if competency in resource_details(row)['competencies'] and resource_details(row)['link_status'] != 'broken']

class _PinnedHTTPS(http.client.HTTPSConnection):
    def connect(self):
        addresses = socket.getaddrinfo(self.host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError('Only public HTTPS destinations may be checked.')
        self.sock = socket.create_connection((addresses[0][4][0], 443), self.timeout)
        self.sock = ssl.create_default_context().wrap_socket(self.sock, server_hostname=self.host)

def check_link(url):
    """No cookies, proxies, bodies or private destinations; validate every redirect."""
    for _ in range(4):
        if not https_url(url):return {'link_status': 'broken', 'link_checked_at': now(), 'link_note': 'Invalid HTTPS URL'}
        connection = None
        try:
            parts = urlsplit(url)
            connection = _PinnedHTTPS(parts.hostname, timeout=4)
            connection.request('HEAD', (parts.path or '/') + ('?' + parts.query if parts.query else ''), headers={'User-Agent': 'SkillTrial-LinkCheck/1.0'})
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                url = urljoin(url, response.getheader('Location', ''));continue
            state = 'healthy' if response.status < 400 else 'broken' if response.status in (404, 410) else 'unreachable'
            return {'link_status': state, 'link_checked_at': now(), 'link_note': 'HTTP ' + str(response.status)}
        except (OSError, ValueError, http.client.HTTPException):
            return {'link_status': 'unreachable', 'link_checked_at': now(), 'link_note': 'Could not verify this link'}
        finally:
            if connection:connection.close()
    return {'link_status': 'broken', 'link_checked_at': now(), 'link_note': 'Too many redirects'}
