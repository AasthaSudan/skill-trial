import copy
import json
import time
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.db import tx,now
from app.models import Attempt,Item,Challenge,User,Token,Job,XP,Path
from app.catalog import policy,public_content,validate
from app.verification import decide
from app.parsing import extract
from app.execution import sql_run,code_run
from app.main import app
from app.service import LOCK,finalize,tick
from conftest import signup,headers

def create(client,mode='formal',skill='sql'):
    if mode=='formal':
        c=client.post('/api/v1/me/skills',json={'skill':skill,'level':'intermediate'},headers=headers(client)).json()
        r=client.post('/api/v1/assessments',json={'claim_id':c['id'],'mode':mode},headers=headers(client))
    else:
        ch=next(c for c in client.get('/api/v1/practice').json() if c['skill']==skill and c['type']=='sql')
        r=client.post('/api/v1/assessments',json={'mode':mode,'challenge_id':ch['id']},headers=headers(client))
    assert r.status_code==201,r.text
    a=r.json();r=client.post('/api/v1/assessments/'+a['id']+'/start',headers=headers(client));assert r.status_code==200
    return client.get('/api/v1/assessments/'+a['id']).json()

def wait(client,id):
    for _ in range(120):
        a=client.get('/api/v1/assessments/'+id).json()
        if a['status']=='completed':return a
        time.sleep(.1)
    raise AssertionError('Evaluation did not complete')

def test_extraction_separates_skills_and_levels():
    rows={c['skill']:c for c in extract('Technical skills\nJava, JavaScript\nSpring Boot\nPython Python Python Python\nFamiliar with Docker; Expert in SQL\n5 years Python')}
    assert 'java' in rows and 'javascript' in rows and 'spring-boot' in rows
    assert rows['python']['level'] is None
    assert rows['docker']['level']=='beginner' and rows['sql']['level']=='advanced'
    assert 'java' not in {c['skill'] for c in extract('Built services in Spring Boot only.')}

def test_four_statuses():
    p=policy('python')
    def items(score,n=3):return [{'type':'coding','level':'intermediate','status':'evaluated','evaluation':{'status':'completed','ratio':score,'competencies':{c:score for c in p['required']}}} for _ in range(n)]
    assert decide(items(1),p,'intermediate')['status']=='verified'
    assert decide(items(0),p,'intermediate')['status']=='not_verified'
    assert decide(items(1,1),p,'intermediate')['status']=='insufficient_evidence'
    partial=items(.8)
    for i in partial:i['evaluation']['competencies']['edge_cases']=.2
    assert decide(partial,p,'intermediate')['status']=='partially_verified'
    assert decide([{'status':'infra_error','evaluation':{'status':'infra_error'}}],p,'intermediate')['status']=='insufficient_evidence'

@pytest.mark.parametrize('query',['DROP TABLE x','ATTACH DATABASE ":memory:" AS x','PRAGMA database_list','SELECT load_extension("x")','SELECT 1; SELECT 2','INSERT INTO x VALUES (2)'])
def test_sql_readonly(query):
    r=sql_run('CREATE TABLE x(a); INSERT INTO x VALUES (1);',query)
    assert r['status']!='ok'

def test_sql_nulls_duplicates_and_deadline():
    r=sql_run('CREATE TABLE x(a); INSERT INTO x VALUES (NULL),(1),(1);','SELECT a FROM x ORDER BY a')
    assert r['rows']==[[None],[1],[1]]
    r=sql_run('CREATE TABLE x(a);','WITH RECURSIVE r(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM r) SELECT sum(x) FROM r')
    assert r['status']=='timeout'

def test_full_sql_journey_reports_and_idempotency(client):
    signup(client)
    sample=b'Alex Morgan\nTechnical skills\nIntermediate SQL\nProjects\nDeveloped reporting queries with joins and aggregation for payment reconciliation.\n'
    r=client.post('/api/v1/resumes',files={'file':('resume.txt',sample,'text/plain')},headers=headers(client));assert r.status_code==201,r.text
    cs=client.get('/api/v1/me/skills').json();assert cs and cs[0]['status']=='pending_review'
    client.patch('/api/v1/me/skills/'+cs[0]['id'],json={'status':'confirmed'},headers=headers(client))
    a=create(client)
    with LOCK,tx() as db:
        solutions={i.id:copy.deepcopy(db.get(Challenge,i.challenge_id).content) for i in db.scalars(select(Item).where(Item.attempt_id==a['id']))}
    for item in a['items']:
        c=solutions[item['id']]
        payload={'query':c['reference']} if c['type']=='sql' else {'answers':c['answers']}
        url=f"/api/v1/assessments/{a['id']}/items/{item['id']}/submit"
        key=str(uuid4());h=headers(client,key)
        r=client.post(url,json={'payload':payload},headers=h);assert r.status_code==202,r.text
        assert client.post(url,json={'payload':payload},headers=h).json()==r.json()
    # Complete early evaluations before finalization: finalizer must not revisit them.
    time.sleep(1)
    r=client.post('/api/v1/assessments/'+a['id']+'/finish',headers=headers(client,str(uuid4())));assert r.status_code==200,r.text
    complete=wait(client,a['id']);assert complete['result']['status']=='verified',complete
    snap=client.get('/api/v1/reports/'+a['id']).json()
    assert all(i['status']=='evaluated' for i in complete['items'])
    assert all('input' not in t for c in snap['snapshot']['challenges'] for t in (c['evaluation'] or {}).get('tests',[]) if t['visibility']=='hidden')
    assert client.get('/api/v1/reports/'+a['id']+'/pdf').status_code==403
    messages=client.get('/api/v1/dev/mail').json();token=messages[0]['url'].split('token=')[1]
    assert client.post('/api/v1/auth/token',json={'token':token}).status_code==200
    pdf=client.get('/api/v1/reports/'+a['id']+'/pdf');assert pdf.content.startswith(b'%PDF-')
    assert client.get('/api/v1/reports/'+a['id']).json()==snap
    assert client.get('/api/v1/me/export').content.startswith(b'PK')
    with LOCK,tx() as db:
        count=db.scalar(select(func.count()).select_from(XP));assert count>0
    client.get('/api/v1/reports/'+a['id']+'/pdf')
    with LOCK,tx() as db:assert db.scalar(select(func.count()).select_from(XP))==count

def test_deadline_autosubmit_and_claim_snapshot(client):
    signup(client);a=create(client);item=next(i for i in a['items'] if i['challenge']['type']=='sql')
    url=f"/api/v1/assessments/{a['id']}/items/{item['id']}/draft"
    assert client.put(url,json={'payload':{'query':'SELECT 1'},'revision':1},headers=headers(client)).status_code==200
    assert client.put(url,json={'payload':{'query':'SELECT 2'},'revision':1},headers=headers(client)).status_code==409
    with LOCK,tx() as db:db.get(Attempt,a['id']).deadline=now()-10
    assert client.put(url,json={'payload':{'query':'SELECT 3'},'revision':2},headers=headers(client)).status_code==409
    client.get('/api/v1/assessments/'+a['id'])
    done=wait(client,a['id']);assert done['result']['status']=='insufficient_evidence'
    with LOCK,tx() as db:assert db.get(Item,item['id']).submission=={'query':'SELECT 1'}

def test_auth_ownership_and_csrf(client):
    signup(client);a=create(client)
    assert client.patch('/api/v1/me/profile',json={'goal':'x'}).status_code==403
    first_cookies=dict(client.cookies);client.cookies.clear();signup(client,email='someoneelse@example.com')
    for path in ['/assessments/','/reports/']:
        assert client.get('/api/v1'+path+a['id']).status_code==404
    assert client.get('/api/v1/admin/challenges').status_code==403
    assert client.post('/api/v1/auth/login',json={'email':'candidate@example.com','password':'no'}).status_code==401

def test_content_and_no_secret_dtos(client):
    with tx() as db:
        for c in db.scalars(select(Challenge)):
            assert validate(c.content)['ok']
            out=public_content(c)
            # Check secret field names recursively. Technical prose may legitimately
            # mention a C++ reference or an acceptable design without exposing a key.
            def field_names(value):
                if isinstance(value,dict):
                    return set(value).union(*(field_names(v) for v in value.values()))
                if isinstance(value,list):
                    return set().union(*(field_names(v) for v in value))
                return set()
            fields=field_names({k:v for k,v in out.items() if k!='samples'})
            assert fields.isdisjoint({'reference','answers','acceptable','expected_output','dataset','answer_rationale','practice_tests'})

def test_practice_never_changes_verification(client):
    signup(client);a=create(client,mode='practice');item=a['items'][0]
    with tx() as db:solution=db.get(Challenge,item['challenge']['id']).content['reference']
    client.post(f"/api/v1/assessments/{a['id']}/items/{item['id']}/submit",json={'payload':{'query':solution}},headers=headers(client,str(uuid4())))
    client.post('/api/v1/assessments/'+a['id']+'/finish',headers=headers(client,str(uuid4())))
    assert wait(client,a['id'])['result']['status']=='practice'
    assert client.get('/api/v1/dashboard').json()['counts']['verified']==0
