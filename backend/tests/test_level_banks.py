import copy
import pytest
from sqlalchemy import select
from app.catalog import SKILLS,LEVELS,policy,practice_variant
from app.db import tx
from app.models import Challenge,Attempt,Item
from app.main import assessment_levels
from app.service import LOCK
from conftest import signup,headers
from test_core import wait
from uuid import uuid4

def test_every_catalog_skill_has_distinct_complete_level_briefings(client):
 signup(client)
 catalog=client.get('/api/v1/skills').json()
 assert len(catalog)==21 and all(s['assessable'] for s in catalog)
 for skill in catalog:
  assert skill['levels']==LEVELS
  claim=client.post('/api/v1/me/skills',json={'skill':skill['slug'],'level':'intermediate'},headers=headers(client)).json()
  sets=[]
  for level in LEVELS:
   r=client.get('/api/v1/assessments/briefing/'+claim['id']+'?level='+level)
   assert r.status_code==200,r.text
   body=r.json();tasks=body['tasks']
   assert tasks and all(t['level']==level for t in tasks)
   assert len(tasks)>=policy(skill['slug'],level)['min_items']
   assert set(skill['competencies'])<={x for t in tasks for x in t['competencies']}
   sets.append({t['id'] for t in tasks})
  assert all(sets[i].isdisjoint(sets[j]) for i in range(3) for j in range(i+1,3))

@pytest.mark.parametrize('level',LEVELS)
def test_created_trials_use_only_selected_level_for_every_skill(client,level):
 signup(client)
 for skill in SKILLS:
  claim=client.post('/api/v1/me/skills',json={'skill':skill['slug'],'level':level},headers=headers(client)).json()
  briefing=client.get('/api/v1/assessments/briefing/'+claim['id']+'?level='+level).json()
  r=client.post('/api/v1/assessments',json={'claim_id':claim['id'],'mode':'formal','level':level},headers=headers(client))
  assert r.status_code==201,r.text
  body=client.get('/api/v1/assessments/'+r.json()['id']).json()
  assert {i['challenge']['id'] for i in body['items']}=={t['id'] for t in briefing['tasks']}
  assert all(i['challenge']['level']==level for i in body['items'])
  assert all('answers' not in i['challenge'] and 'answer_rationale' not in i['challenge'] and 'practice_tests' not in i['challenge'] for i in body['items'])

@pytest.mark.parametrize('level',LEVELS)
def test_new_cpp_scenario_trial_evaluates_and_produces_a_formal_report(client,level):
 signup(client)
 claim=client.post('/api/v1/me/skills',json={'skill':'cpp','level':level},headers=headers(client)).json()
 r=client.post('/api/v1/assessments',json={'claim_id':claim['id'],'mode':'formal','level':level},headers=headers(client));assert r.status_code==201
 aid=r.json()['id'];assert client.post('/api/v1/assessments/'+aid+'/start',headers=headers(client)).status_code==200
 body=client.get('/api/v1/assessments/'+aid).json()
 for item in body['items']:
  with tx() as db:answers=copy.deepcopy(db.get(Challenge,item['challenge']['id']).content['answers'])
  url=f"/api/v1/assessments/{aid}/items/{item['id']}/submit"
  assert client.post(url,json={'payload':{'answers':answers}},headers=headers(client,str(uuid4()))).status_code==202
 assert client.post('/api/v1/assessments/'+aid+'/finish',headers=headers(client,str(uuid4()))).status_code==200
 completed=wait(client,aid)
 assert completed['result']['status']=='verified' and completed['result']['overall']==1
 report=client.get('/api/v1/reports/'+aid).json()['snapshot']
 assert all(c['difficulty']==level and c['type']=='scenario' for c in report['challenges'])

def test_missing_level_content_never_falls_back_to_another_level(client):
 with LOCK,tx() as db:
  for c in db.scalars(select(Challenge).where(Challenge.skill=='python',Challenge.pool=='assessment',Challenge.level=='beginner')):c.status='unpublished'
  db.flush();assert assessment_levels(db,'python')==['intermediate','advanced']
 signup(client)
 claim=client.post('/api/v1/me/skills',json={'skill':'python','level':'beginner'},headers=headers(client)).json()
 response=client.get('/api/v1/assessments/briefing/'+claim['id']+'?level=beginner')
 assert response.status_code==409 and response.json()['error']['code']=='LEVEL_UNAVAILABLE'

def test_explicit_beginner_practice_tests_preserve_their_own_contract(client):
 with tx() as db:
  formal=db.scalar(select(Challenge).where(Challenge.slug=='python-beginner-count-even',Challenge.pool=='assessment'))
  practice=practice_variant(formal.content)
  assert 'practice_tests' not in practice
  assert practice['tests']!=formal.content['tests']
  assert all(t['expected']==sum(n%2==0 for n in t['input']) for t in practice['tests'])
