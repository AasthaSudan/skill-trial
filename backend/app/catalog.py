"""Versioned content is loaded from YAML, validated, and stored before use."""
import hashlib
import copy
import random
import json
from pathlib import Path
import yaml
from sqlalchemy import select
from .config import ROOT,DEMO_CONTENT
from .models import Challenge

SKILLS = [
    {'slug':'sql','name':'SQL','category':'database','color':'#64d9c0','glyph':'database','description':'Make sense of data. Write queries that stay correct around NULLs, joins, and duplicates.','competencies':['filtering','joins','aggregation','null_handling','duplicates'],'aliases':['SQL','Structured Query Language','PostgreSQL','MySQL','SQLite','T-SQL']},
    {'slug':'python','name':'Python','category':'language','color':'#e7c779','glyph':'code','description':'Clear thinking, expressed in code. Work with collections, edge cases, and practical algorithms.','competencies':['collections','algorithms','edge_cases'],'aliases':['Python','Python3']},
    {'slug':'java','name':'Java','category':'language','color':'#e3a38a','glyph':'coffee','description':'Build reliable solutions with collections, algorithms, and careful edge-case handling.','competencies':['collections','algorithms','edge_cases'],'aliases':['Java','Core Java']},
    {'slug':'javascript','name':'JavaScript','category':'language','color':'#dcca75','glyph':'braces','description':'Reason about arrays, transformations, correctness, and the cases that are easy to miss.','competencies':['collections','algorithms','edge_cases'],'aliases':['JavaScript','ECMAScript','JS']},
    {'slug':'spring-boot','name':'Spring Boot','category':'framework','color':'#a4d19a','glyph':'leaf','description':'Assess API contracts, validation, service boundaries, persistence, transactions, and exception handling through practical framework scenarios.','competencies':['rest_apis','validation','services','persistence','transactions','exceptions'],'aliases':['Spring Boot','SpringBoot']},
]

# Additional skills use explicit scenario assessments rather than unsupported code runtimes.
SCENARIO_SKILLS = {'react': {'name': 'React', 'competencies': ['components_state', 'effects_data', 'rendering_accessibility']}, 'docker': {'name': 'Docker', 'competencies': ['images_builds', 'containers_networking', 'volumes_security']}, 'git': {'name': 'Git', 'competencies': ['branching_history', 'merges_conflicts', 'collaboration_safety']}, 'nodejs': {'name': 'Node.js', 'competencies': ['async_execution', 'http_services', 'dependencies_security']}, 'aws': {'name': 'AWS', 'competencies': ['identity_access', 'compute_scaling', 'storage_reliability']}, 'mongodb': {'name': 'MongoDB', 'competencies': ['documents_queries', 'indexes_performance', 'consistency_updates']}, 'typescript': {'name': 'TypeScript', 'competencies': ['types_narrowing', 'generics_contracts', 'runtime_boundaries']}, 'fastapi': {'name': 'FastAPI', 'competencies': ['request_validation', 'dependencies_auth', 'async_persistence']}, 'kubernetes': {'name': 'Kubernetes', 'competencies': ['workloads_services', 'configuration_security', 'reliability_operations']}, 'redis': {'name': 'Redis', 'competencies': ['structures_expiry', 'atomic_operations', 'cache_reliability']}, 'html': {'name': 'HTML', 'competencies': ['document_structure', 'forms_validation', 'semantics_accessibility']}, 'css': {'name': 'CSS', 'competencies': ['cascade_selectors', 'layout_responsiveness', 'accessibility_motion']}, 'csharp': {'name': 'C#', 'competencies': ['types_nullability', 'collections_linq', 'async_resources']}, 'cpp': {'name': 'C++', 'competencies': ['ownership_lifetimes', 'containers_algorithms', 'bounds_correctness']}, 'go': {'name': 'Go', 'competencies': ['values_interfaces', 'goroutines_channels', 'errors_context']}, 'dotnet': {'name': '.NET', 'competencies': ['dependency_injection', 'api_configuration', 'data_lifetimes']}}
for slug,entry in SCENARIO_SKILLS.items():
    SKILLS.append({'slug':slug,'name':entry['name'],'category':'language' if slug in ['typescript','csharp','cpp','go'] else 'tool','color':'#a69cc9','glyph':'code','description':'Assess '+entry['name']+' decisions and reasoning through level-specific scenarios. Full application/code execution is not part of this skill assessment.','competencies':entry['competencies'],'aliases':[entry['name'],'Golang'] if slug=='go' else [entry['name']],'assessment_format':'scenario'})

LEVELS = ['beginner','intermediate','advanced']
def skill(slug):
    return next((s for s in SKILLS if s['slug']==slug), None)

def policy(slug, level='intermediate'):
    return {'version':1,'family':f'{slug}.{level}','required':skill(slug)['competencies'],'min_items':2 if level=='beginner' else 4 if level=='advanced' else 3,'coverage':1 if level=='beginner' else .9 if level=='advanced' else .8,'item_pass':.75 if level=='advanced' else .7,'competency_pass':.75 if level=='advanced' else .7,'overall':.8 if level=='advanced' else .75,'at_level':3 if level=='advanced' else 1 if level=='beginner' else 2,'trust_required':False}

def validate(c):
    checks=[]
    def check(name,ok): checks.append({'name':name,'passed':bool(ok)})
    check('Statement and title', c.get('title') and len(c.get('statement',''))>=40)
    check('Supported challenge type', c.get('type') in ['coding','sql','debugging','scenario','trust'])
    check('Known skill and competencies', skill(c.get('skill')) and c.get('competencies') and all(x in skill(c['skill'])['competencies']+['ai_judgment','testing','debugging'] for x in c.get('competencies',[])))
    if c.get('type') in ['coding','sql','debugging']:
        tests=c.get('tests',[])
        check('Sample and hidden tests', any(t.get('visibility')=='sample' for t in tests) and sum(t.get('visibility')=='hidden' for t in tests)>=3)
        check('Expected result on every test', all('expected' in t for t in tests))
        check('Tests cover all declared competencies', all(any(x in t.get('competencies',[]) for t in tests) for x in c.get('competencies',[])))
    if c.get('type')=='scenario':
        check('Every question has an answer key', all(q['id'] in c.get('answers',{}) for q in c.get('questions',[])))
    if c.get('type')=='trust':
        check('Correct and flawed suggestions', len(c.get('suggestions',[]))>=3 and any(s.get('acceptable') for s in c.get('suggestions',[])) and sum(not s.get('acceptable') for s in c.get('suggestions',[]))>=2)
        check('Counterexample reference and domain', bool(c.get('reference')) and bool(c.get('tests')))
    return {'ok':all(x['passed'] for x in checks),'checks':checks}

PUBLIC = {'title','statement','type','skill','level','minutes','competencies','starter','language','schema','sample_rows','questions','categories','hints','explanation_prompt'}
def public_content(ch, hint_count=0, item_id=''):
    c=ch.content
    out={k:v for k,v in c.items() if k in PUBLIC and k!='hints'}
    out.update(id=ch.id,slug=ch.slug,version=ch.version,pool=ch.pool,family=ch.family)
    out['hints']=c.get('hints',[])[:hint_count]
    out['hint_total']=len(c.get('hints',[]))
    if ch.type in ['coding','sql','debugging']:
        out['samples']=[{k:t[k] for k in ['input','expected','label'] if k in t} for t in c.get('tests',[]) if t['visibility']=='sample']
    if ch.type=='trust':
        out['suggestions']=[{'id':opaque(item_id,s['id']),'code':s['code']} for s in c['suggestions']]
        random.Random(item_id).shuffle(out['suggestions'])
    if ch.type=='scenario':
        out['questions']=copy.deepcopy(out['questions'])
        for q in out['questions']:random.Random(item_id+q['id']).shuffle(q['options'])
    return out

def opaque(item_id,key):return hashlib.sha256((item_id+':'+key).encode()).hexdigest()[:16] if item_id else key

def canonical_payload(content,item_id,payload):
    p=copy.deepcopy(payload)
    if content['type']=='trust':
        mapping={opaque(item_id,s['id']):s['id'] for s in content['suggestions']}
        for field in ['decisions','categories']:
            p[field]={mapping[k]:v for k,v in p.get(field,{}).items() if k in mapping}
        p['target']=mapping.get(p.get('target'))
    return p

def seed(db):
    manifest_path=ROOT/'content'/'validation.json'
    attestations=json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    for f in sorted((ROOT/'content'/'challenges').glob('*.yaml')):
        c=yaml.safe_load(f.read_text(encoding='utf-8'))
        for pool in ['assessment','practice']:
            slug=c['slug'] if pool=='assessment' else c['slug']+'-practice'
            version_content=practice_variant(c) if pool=='practice' else c
            existing=db.scalar(select(Challenge).where(Challenge.slug==slug).order_by(Challenge.version.desc()))
            report=validate(version_content)
            if not report['ok']: raise ValueError(f'Invalid content {f.name}: {report}')
            attested=attestations.get(digest(version_content))
            # Development preview makes all attested seed features usable locally.
            # It never changes the manifest's independent publication approval.
            approved=bool(attested and attested.get('publication','approved')=='approved')
            if attested and attested.get('ok') and attested.get('executed'):report=copy.deepcopy(attested)
            preview=bool(DEMO_CONTENT and report.get('executed') and not approved)
            if preview:report['demo_preview']=True
            if existing and digest(existing.content)==digest(version_content):
                if existing.reviewer=='development-preview' and not preview:
                    existing.status='published' if approved and report.get('executed') else 'draft';existing.reviewer=None;existing.validation=report
                elif preview and existing.author in ['system','seed'] and existing.status=='draft':
                    existing.status='published';existing.reviewer='development-preview';existing.validation=report
                continue
            if existing:existing.status='unpublished'
            db.add(Challenge(slug=slug,version=existing.version+1 if existing else 1,skill=c['skill'],type=c['type'],pool=pool,family=c['family'],level=c.get('level','intermediate'),status='published' if report.get('executed') and (approved or preview) else 'draft',reviewer='development-preview' if preview else None,content=version_content,validation=report))

def practice_variant(content):
    c=copy.deepcopy(content)
    c['title']='Practice: '+c['title']
    explicit_tests=c.pop('practice_tests',None)
    if explicit_tests is not None:
        c['tests']=explicit_tests
        return c
    if c['type']=='sql':
        from .sql_worker import execute
        for t in c['tests']:
            t['dataset']+=" INSERT INTO customers VALUES (10,'Practice customer',NULL); INSERT INTO orders VALUES (20,1,43);"
            t['expected']=execute(t['dataset'],c['reference'])['rows']
    elif c['type'] in ['coding','debugging']:
        inputs=[[14,19,19,5],[8,8],[5],[-40,-10,-20],[2000000000,-2000000000]]
        for t,inp in zip(c['tests'],inputs):
            t['input']=inp
            if 'second-largest' in c['slug']:
                values=sorted(set(inp));t['expected']=values[-2] if len(values)>1 else None
            elif 'unique-count' in c['slug']:t['expected']=len(set(inp))
            elif 'window-triple-maximum' in c['slug']:
                t['expected']=max((sum(inp[i:i+3]) for i in range(len(inp)-2)),default=None)
            elif 'longest-rising-run' in c['slug']:
                best=current=1 if inp else 0
                for i in range(1,len(inp)):
                    current=current+1 if inp[i]>inp[i-1] else 1;best=max(best,current)
                t['expected']=best
            elif 'nondecreasing-removals' in c['slug']:
                from bisect import bisect_right
                tails=[]
                for value in inp:
                    i=bisect_right(tails,value)
                    if i==len(tails):tails.append(value)
                    else:tails[i]=value
                t['expected']=len(inp)-len(tails)
            elif 'closest-distinct-gap' in c['slug']:
                values=sorted(set(inp));t['expected']=min((values[i]-values[i-1] for i in range(1,len(values))),default=None)
            else:t['expected']=sum(n for n in inp if n>0)
    elif c['type']=='trust':
        for t,inp in zip(c['tests'],[[],[4,7],[-5,3],[200000,900000]]):t['input']=inp;t['expected']=sum(inp)/len(inp) if inp else 0
    return c

def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
