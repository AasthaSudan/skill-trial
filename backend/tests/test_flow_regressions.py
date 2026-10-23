import copy
import pytest
from sqlalchemy import select,func
from app.catalog import seed
from app.db import tx,now
from app.game import quests
from app.models import User,Challenge,Activity,Path,XP
from app.service import LOCK
from conftest import signup,headers
from test_core import create,wait
from uuid import uuid4

@pytest.mark.parametrize('profile,targets',[
 ({'roles':['Data Analyst']},['sql','python']),
 ({'roles':['Backend Java Developer']},['java','spring-boot']),
 ({'roles':['Full-stack Developer']},['javascript','python','sql']),
 ({'goal':'Improve SQL for my next role'},['sql']),
])
def test_dashboard_after_real_onboarding(client,profile,targets):
 signup(client)
 assert client.patch('/api/v1/me/profile',json={**profile,'onboarded':True},headers=headers(client)).status_code==200
 r=client.get('/api/v1/dashboard')
 assert r.status_code==200,r.text
 rows=r.json()['goal_progress'][0]['skills']
 assert [x['skill'] for x in rows]==targets
 assert all(isinstance(x['assessable'],bool) for x in rows)
 assert client.get('/api/v1/dashboard').json()['counts']['verified']==0

def test_existing_seed_drafts_become_development_previews(client):
 with LOCK,tx() as db:
  row=next(c for c in db.scalars(select(Challenge)) if c.validation.get('demo_preview'))
  row.status='draft';row.reviewer=None;row.author='seed';row.validation={k:v for k,v in row.validation.items() if k!='demo_preview'};key=row.id
  seed(db)
 with tx() as db:
  row=db.get(Challenge,key)
  assert row.status=='published'
  assert row.reviewer=='development-preview'
  assert row.validation['demo_preview'] is True

def test_weekly_quest_claim_does_not_refill_a_used_shield(client):
 user=signup(client)
 with LOCK,tx() as db:
  u=db.get(User,user['id'])
  for i in range(5):db.add(Activity(key=u.id+':test-practice:'+str(i),user_id=u.id,kind='practice',facts={'ratio':1},created=now()))
  db.flush();weekly=next(q for q in quests(db,u) if q['kind']=='weekly')
 url='/api/v1/me/quests/'+weekly['id']+'/claim'
 assert client.post(url,headers=headers(client)).json()['shield_earned'] is True
 with LOCK,tx() as db:
  u=db.get(User,user['id']);u.profile={**u.profile,'streak_shields':0}
  before=db.scalar(select(func.sum(XP.points)).where(XP.user_id==u.id))
 assert client.post(url,headers=headers(client)).json()['shield_earned'] is False
 with tx() as db:
  assert db.get(User,user['id']).profile.get('streak_shields',0)==0
  assert db.scalar(select(func.sum(XP.points)).where(XP.user_id==user['id']))==before

@pytest.mark.parametrize('path_state,expected',[('locked','available'),('archived','available'),('unlocked','completed')])
def test_standalone_practice_preserves_waypoint_gates(client,path_state,expected):
 user=signup(client);a=create(client,mode='practice');item=a['items'][0]
 with LOCK,tx() as db:
  solution=db.get(Challenge,item['challenge']['id']).content['reference']
  path=Path(user_id=user['id'],attempt_id=a['id'],skill='sql',archived=path_state=='archived',items=[{'id':'read','type':'resource','status':'completed' if path_state!='locked' else 'available'},{'id':'practice','type':'practice','challenge_id':item['challenge']['id'],'status':'available'}])
  db.add(path);db.flush();path_id=path.id
 assert client.post(f"/api/v1/assessments/{a['id']}/items/{item['id']}/submit",json={'payload':{'query':solution}},headers=headers(client,str(uuid4()))).status_code==202
 assert client.post('/api/v1/assessments/'+a['id']+'/finish',headers=headers(client,str(uuid4()))).status_code==200
 assert wait(client,a['id'])['result']['overall']==1
 with tx() as db:assert db.get(Path,path_id).items[-1]['status']==expected

def test_active_and_cooldown_trial_guards_return_domain_errors(client):
 signup(client);a=create(client)
 claim=next(c for c in client.get('/api/v1/me/skills').json() if c['skill']=='sql')
 body={'claim_id':claim['id'],'mode':'formal','level':'intermediate'}
 r=client.post('/api/v1/assessments',json=body,headers=headers(client))
 assert r.status_code==409 and r.json()['error']['code']=='ATTEMPT_ACTIVE'
 assert r.json()['error']['details']['attempt_id']==a['id']
 assert client.post('/api/v1/assessments/'+a['id']+'/finish',headers=headers(client,str(uuid4()))).status_code==200
 wait(client,a['id'])
 r=client.post('/api/v1/assessments',json=body,headers=headers(client))
 assert r.status_code==409 and r.json()['error']['code']=='REASSESS_COOLDOWN'
 assert r.json()['error']['details']['available_at']>now()

def test_distinct_confirmed_skills_make_all_first_steps_tiers_reachable(client):
 user=signup(client)
 assert client.patch('/api/v1/me/profile',json={'onboarded':True},headers=headers(client)).status_code==200
 ids=[]
 for slug in ['sql','python','java','javascript','spring-boot']:
  r=client.post('/api/v1/me/skills',json={'skill':slug,'level':'intermediate'},headers=headers(client))
  assert r.status_code==200;ids.append(r.json()['id'])
 badge=next(b for b in client.get('/api/v1/me/badges').json() if b['id']=='first-light')
 assert badge['tier']==3
 with tx() as db:before=db.scalar(select(func.sum(XP.points)).where(XP.user_id==user['id']))
 for claim_id in ids:
  assert client.patch('/api/v1/me/skills/'+claim_id,json={'status':'confirmed'},headers=headers(client)).status_code==200
 with tx() as db:assert db.scalar(select(func.sum(XP.points)).where(XP.user_id==user['id']))==before
 assert client.patch('/api/v1/me/skills/'+ids[0],json={'status':'removed'},headers=headers(client)).status_code==200
 assert next(b for b in client.get('/api/v1/me/badges').json() if b['id']=='first-light')['tier']==3

def test_legacy_confirmation_event_is_not_double_counted(client):
 from app.game import badge_values
 user=signup(client)
 for slug in ['sql','python']:
  assert client.post('/api/v1/me/skills',json={'skill':slug},headers=headers(client)).status_code==200
 with LOCK,tx() as db:
  db.add(Activity(key=user['id']+':confirmed',user_id=user['id'],kind='confirmed',facts={}))
  db.flush();assert badge_values(db,db.get(User,user['id']))['confirmed_steps']==2
