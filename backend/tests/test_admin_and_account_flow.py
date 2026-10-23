from urllib.parse import parse_qs,urlparse
from sqlalchemy import select
from app.db import tx
from app.models import User,BadgeAward
from conftest import signup,headers,DUMMY_TEST_PASSWORD

def elevate(user_id,permissions=None):
 with tx() as db:
  u=db.get(User,user_id);u.role='admin'
  if permissions is not None:u.profile={**u.profile,'admin_permissions':permissions}

def test_password_reset_invalidates_sessions_and_accepts_new_password(client):
 user=signup(client)
 r=client.post('/api/v1/auth/forgot-password',json={'email':user['email']});assert r.status_code==202
 messages=client.get('/api/v1/dev/mail').json();token=parse_qs(urlparse(next(m['url'] for m in messages if m['kind']=='reset')).query)['token'][0]
 new='Different-reset-test-password-27'
 assert client.post('/api/v1/auth/token',json={'token':token,'password':new}).status_code==200
 assert client.get('/api/v1/me').status_code==401
 assert client.post('/api/v1/auth/login',json={'email':user['email'],'password':DUMMY_TEST_PASSWORD}).status_code==401
 assert client.post('/api/v1/auth/login',json={'email':user['email'],'password':new}).status_code==200
 assert client.post('/api/v1/auth/token',json={'token':token,'password':new}).status_code==422

def test_resource_review_and_publication_with_multiple_quick_checks(client):
 author=signup(client,email='resource-author@example.test');elevate(author['id'])
 body={'slug':'qa-two-check-guide','skill':'sql','competencies':['joins','null_handling'],'title':'A guide to preserved join rows','body':'A LEFT JOIN preserves every row from the left relation. Check missing relationships, multiple matches and NULL values before deciding the query is correct.','kind':'guide','difficulty':'beginner','estimated_minutes':5,'checks':[{'question':'Which join preserves the left relation?','options':['LEFT JOIN','INNER JOIN'],'answer':0},{'question':'How should missing values be checked?','options':['IS NULL','= NULL'],'answer':0}]}
 r=client.post('/api/v1/admin/resources',json=body,headers=headers(client));assert r.status_code==200,r.text
 row=r.json();url='/api/v1/admin/resources/'+row['id']
 assert client.post(url+'/publish',headers=headers(client)).status_code==409
 assert client.post(url+'/validate',headers=headers(client)).json()['status']=='validated'
 assert client.post(url+'/review',headers=headers(client)).status_code==409
 client.cookies.clear();reviewer=signup(client,email='resource-reviewer@example.test');elevate(reviewer['id'])
 assert client.post(url+'/review',headers=headers(client)).json()['status']=='reviewed'
 assert client.post(url+'/publish',headers=headers(client)).json()['status']=='published'
 assert client.patch(url,json=body,headers=headers(client)).status_code==409
 revised=client.post('/api/v1/admin/resources',json=body,headers=headers(client));assert revised.json()['version']==2
 assert client.post(url+'/archive',headers=headers(client)).json()['status']=='archived'

def test_badge_rules_version_and_earned_tiers_are_persistent(client):
 user=signup(client,email='badge-admin@example.test');elevate(user['id'])
 assert client.patch('/api/v1/me/profile',json={'onboarded':True},headers=headers(client)).status_code==200
 body={'slug':'qa-onboard-badge','name':'First direction','description':'Complete one meaningful setup step.','metric':'confirmed_steps','thresholds':[1,2],'category':'milestone','icon':'Award'}
 assert client.post('/api/v1/admin/badges',json=body,headers=headers(client)).status_code==200
 earned=next(b for b in client.get('/api/v1/me/badges').json() if b['id']==body['slug']);assert earned['tier']==1
 updated=client.patch('/api/v1/admin/badges/'+body['slug'],json={'version':1,'thresholds':[10,20]},headers=headers(client));assert updated.json()['version']==2
 assert client.patch('/api/v1/admin/badges/'+body['slug'],json={'version':1,'thresholds':[30]},headers=headers(client)).status_code==409
 assert client.patch('/api/v1/admin/badges/'+body['slug'],json={'status':'archived'},headers=headers(client)).status_code==200
 kept=next(b for b in client.get('/api/v1/me/badges').json() if b['id']==body['slug'])
 assert kept['earned'] and kept['tier']==1 and kept['archived'] and kept['awards'][0]['version']==1

def test_scoped_admin_and_suspension_are_server_enforced(client):
 candidate=signup(client,email='suspend-me@example.test');candidate_cookies=dict(client.cookies)
 client.cookies.clear();admin=signup(client,email='scoped-admin@example.test');elevate(admin['id'],['content.read'])
 assert client.get('/api/v1/admin/challenges').status_code==200
 assert client.get('/api/v1/admin/users').status_code==403
 assert client.get('/api/v1/admin/stats').status_code==403
 elevate(admin['id'],['users.manage'])
 r=client.patch('/api/v1/admin/users/'+candidate['id'],json={'status':'suspended'},headers=headers(client));assert r.status_code==200
 admin_cookies=dict(client.cookies);client.cookies.clear();client.cookies.update(candidate_cookies)
 assert client.get('/api/v1/me').status_code==401
 client.cookies.clear();client.cookies.update(admin_cookies)
 assert client.patch('/api/v1/admin/users/'+candidate['id'],json={'status':'active'},headers=headers(client)).status_code==200
 assert client.post('/api/v1/auth/login',json={'email':candidate['email'],'password':DUMMY_TEST_PASSWORD}).status_code==200

def test_league_leave_response_matches_saved_membership(client):
 signup(client)
 assert client.patch('/api/v1/me/league',json={'joined':True},headers=headers(client)).json()['joined']
 response=client.patch('/api/v1/me/league',json={'joined':False},headers=headers(client))
 assert response.status_code==200 and response.json()['joined'] is False
 assert client.get('/api/v1/me/league').json()['joined'] is False
