import copy
from sqlalchemy import select,func,text
from app.db import tx,now
from app.models import User,Attempt,Claim,Challenge,Item,Quest,XP,Path
from app.main import maintenance
from app.catalog import public_content,canonical_payload
from app.service import LOCK
from conftest import signup,headers,DUMMY_TEST_PASSWORD
from test_core import create,wait
from uuid import uuid4

def test_trust_ids_are_per_item_and_do_not_reveal_keys(client):
    with tx() as db:
        c=db.scalar(select(Challenge).where(Challenge.type=='trust'))
        a,b=public_content(c,item_id='attempt-one'),public_content(c,item_id='attempt-two')
        assert {x['id'] for x in a['suggestions']}.isdisjoint(x['id'] for x in b['suggestions'])
        first=a['suggestions'][0]['id']
        canonical=canonical_payload(c.content,'attempt-one',{'decisions':{first:'reject'},'target':first})
        assert canonical['target'] in {s['id'] for s in c.content['suggestions']}

def test_reference_validation_and_independent_review(client):
    user=signup(client,email='author@example.com')
    with LOCK,tx() as db:db.get(User,user['id']).role='admin'
    content=next(c['content'] for c in client.get('/api/v1/admin/challenges').json() if c['type']=='sql')
    content['slug']='new-sql-author-test'
    r=client.post('/api/v1/admin/challenges',json={'content':content,'pool':'practice'},headers=headers(client));assert r.status_code==200,r.text
    id=r.json()['id']
    assert client.post(f'/api/v1/admin/challenges/{id}/publish',headers=headers(client)).status_code==409
    assert client.post(f'/api/v1/admin/challenges/{id}/review',headers=headers(client)).status_code==409
    r=client.post(f'/api/v1/admin/challenges/{id}/validate',headers=headers(client));assert r.json()['ok'] and r.json()['executed']
    assert client.post(f'/api/v1/admin/challenges/{id}/review',headers=headers(client)).status_code==409
    client.cookies.clear();reviewer=signup(client,email='reviewer@example.com')
    with LOCK,tx() as db:db.get(User,reviewer['id']).role='admin'
    assert client.post(f'/api/v1/admin/challenges/{id}/review',headers=headers(client)).status_code==200
    assert client.post(f'/api/v1/admin/challenges/{id}/publish',headers=headers(client)).status_code==200

def test_pending_deletion_can_be_cancelled_and_due_deletion_erases(client):
    user=signup(client);a=create(client)
    r=client.post('/api/v1/me/delete-account',json={'password':DUMMY_TEST_PASSWORD},headers=headers(client));assert r.status_code==200
    assert client.get('/api/v1/dashboard').status_code==409
    assert client.post('/api/v1/me/cancel-deletion',headers=headers(client)).status_code==200
    assert client.get('/api/v1/dashboard').status_code==200
    with LOCK,tx() as db:u=db.get(User,user['id']);u.status='pending_deletion';u.delete_at=now()-1
    maintenance()
    with tx() as db:
        assert db.get(User,user['id']) is None
        assert db.get(Attempt,a['id']) is None
        assert not list(db.scalars(select(Claim).where(Claim.user_id==user['id'])))

def test_allowed_dev_proxy_and_rejected_cross_origin(client):
    assert client.post('/api/v1/auth/forgot-password',json={'email':'none@example.com'},headers={'Origin':'http://127.0.0.1:5173'}).status_code==202
    assert client.post('/api/v1/auth/forgot-password',json={'email':'none@example.com'},headers={'Origin':'https://attacker.example'}).status_code==403

def test_verification_links_use_configured_app_url(client,monkeypatch):
    monkeypatch.delenv('PUBLIC_APP_URL',raising=False)
    monkeypatch.setenv('APP_URL','https://skilltrial.example/')
    signup(client,email='url-check@example.com')
    messages=client.get('/api/v1/dev/mail').json()
    assert messages and all(m['url'].startswith('https://skilltrial.example/verify-email?token=') for m in messages)

def test_report_is_database_immutable(client):
    signup(client);a=create(client)
    client.post('/api/v1/assessments/'+a['id']+'/finish',headers=headers(client,str(uuid4())))
    wait(client,a['id'])
    rejected=False
    try:
        with tx() as db:db.execute(text('UPDATE attempts SET result=:result WHERE id=:id'),{'result':'{}','id':a['id']})
    except Exception:rejected=True
    assert rejected

def test_learning_quick_check_and_reward_cannot_be_bypassed(client):
    user=signup(client);a=create(client)
    client.post('/api/v1/assessments/'+a['id']+'/finish',headers=headers(client,str(uuid4())))
    wait(client,a['id'])
    paths=client.get('/api/v1/learning/paths').json();assert paths
    path=paths[0];resource=next(i for i in path['items'] if i['type']=='resource')
    assert 'answer' not in resource
    url=f"/api/v1/learning/paths/{path['id']}/items/{resource['id']}"
    assert client.post(url+'/complete',json={'answer':1},headers=headers(client)).status_code==422
    assert client.post(url+'/open',json={},headers=headers(client)).status_code==200
    assert client.post(url+'/complete',json={'answer':1},headers=headers(client)).status_code==422
    with LOCK,tx() as db:
        stored=db.get(Path,path['id']);items=copy.deepcopy(stored.items)
        next(i for i in items if i['id']==resource['id'])['opened']=now()-31;stored.items=items
    assert client.post(url+'/complete',json={'answer':0},headers=headers(client)).status_code==422
    assert client.post(url+'/complete',json={'answer':1},headers=headers(client)).status_code==200
    with tx() as db:xp_before=db.scalar(select(func.sum(XP.points)).where(XP.user_id==user['id']))
    assert client.post(url+'/complete',json={'answer':1},headers=headers(client)).status_code==200
    with tx() as db:assert db.scalar(select(func.sum(XP.points)).where(XP.user_id==user['id']))==xp_before
