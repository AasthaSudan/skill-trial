from contextlib import asynccontextmanager
import asyncio
import copy
from datetime import datetime,timezone,timedelta,time as day_time
import io
import json
import logging
import os
from pathlib import Path as FilePath
import random
import re
import secrets
import smtplib
import threading
import time
from email.message import EmailMessage
import zipfile
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError

from fastapi import FastAPI,Request,Response,UploadFile,File,HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse,StreamingResponse,FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select,func,delete,update
from sqlalchemy.exc import IntegrityError

from .config import VAR,ENV,COOKIE_SECURE,COOLDOWN_H,GRACE,ROOT,RUN_BACKGROUND_WORKER,LLM_READY,LLM_MODEL
from .db import Base,engine,tx,now,uid
from .models import User,AuthSession,Token,Resume,Claim,Challenge,Attempt,Item,Job,XP,Activity,Path,Quest,Audit,Idempotency,Celebration,InboxNotification,OrbitProgress,Notice,ReportShare,ReportShareItem,ShareAccess,AppSetting,LeagueMember,LearningResource,BadgeDefinition,BadgeAward
from .security import HASHER,DUMMY,CRYPT,auth,owned,hashed,fail,rate,password_ok,issue_token,audit
from .catalog import SKILLS,LEVELS,skill,policy,seed,public_content,validate,digest,canonical_payload,opaque
from .parsing import read_resume,extract
from .service import LOCK,enqueue,finalize,complete,tick,substantive,seed_resources
from .game import award,activity,progress,quests,badges,celebrate,orbit_map,cosmetics,weekly_recap,seed_badges
from .evaluation import run,visible_evaluation
from .execution import code_run,RunnerUnavailable,equivalent
from .reports import pdf
from .validation import executable_validation
from .llm import extract_claims,propose_challenge,LLMUnavailable,PROPOSAL_TYPES
from .admin_catalog import router as catalog_admin_router
from .resources import resource_details,check_link

STOP=threading.Event()
def smtp_send(msg):
    host=os.environ.get('SMTP_HOST')
    if not host:raise RuntimeError('SMTP delivery is not configured.')
    port=int(os.environ.get('SMTP_PORT','587'));ssl_mode=os.environ.get('SMTP_SSL','false').lower()=='true'
    smtp=smtplib.SMTP_SSL(host,port,timeout=10) if ssl_mode else smtplib.SMTP(host,port,timeout=10)
    with smtp:
        smtp.ehlo()
        if not ssl_mode and os.environ.get('SMTP_STARTTLS','true').lower()=='true':smtp.starttls();smtp.ehlo()
        if os.environ.get('SMTP_USER'):smtp.login(os.environ['SMTP_USER'],os.environ.get('SMTP_PASSWORD',''))
        smtp.send_message(msg)

def deliver_notice(notice_id):
    with LOCK,tx() as db:
        claim=db.execute(update(Notice).where(Notice.key==notice_id,Notice.status=='queued').values(status='sending'))
        if claim.rowcount!=1:return
        notice=db.get(Notice,notice_id);db.refresh(notice)
        user=db.get(User,notice.user_id)
        allowed_status=user and (user.status=='active' or user.status=='pending_deletion' and notice.kind=='deletion_scheduled')
        if not allowed_status or not user.verified:notice.status='cancelled';return
        email=user.email;kind=notice.kind;payload=copy.deepcopy(notice.payload)
    try:
        message=EmailMessage();message['From']=os.environ.get('SMTP_FROM','hello@skilltrial.local');message['To']=email
        if kind=='quest_reminder':
            message['Subject']='A small practice invitation from SkillTrial';message.set_content('If a practice run fits your day, your Practice Arena is ready. There is no streak penalty for taking a break.\n\n'+os.environ.get('PUBLIC_APP_URL','http://127.0.0.1:5173').rstrip('/')+'/app/practice')
        elif kind=='deletion_scheduled':
            message['Subject']='Your SkillTrial account deletion is scheduled';message.set_content('Your SkillTrial account is scheduled for deletion in seven days. Sign in during that period, open Settings, and choose Keep my account to cancel. Any report links were revoked when the request was made.')
        else:
            recap=payload;message['Subject']='Your SkillTrial week in orbit';message.set_content(f"Last week: {recap.get('practice_runs',0)} practice runs, {recap.get('waypoints',0)} learning steps, {recap.get('xp',0)} XP, and {recap.get('formal_trials',0)} formal Trials.\n\nYour account data and assessment details remain private.\n"+os.environ.get('PUBLIC_APP_URL','http://127.0.0.1:5173').rstrip('/')+'/app')
        if os.environ.get('SMTP_HOST'):smtp_send(message)
        elif ENV=='development':
            folder=VAR/'mail';folder.mkdir(exist_ok=True);(folder/(uid()+'.json')).write_text(json.dumps({'email':email,'kind':kind,'subject':message['Subject'],'url':os.environ.get('PUBLIC_APP_URL','http://127.0.0.1:5173')+'/app','created':now()}),encoding='utf-8')
        else:raise RuntimeError('Email delivery is not configured.')
    except Exception as error:
        logging.warning('Notification delivery failed: %s',type(error).__name__)
        with LOCK,tx() as db:
            notice=db.get(Notice,notice_id)
            if notice:notice.status='failed';notice.error=type(error).__name__
        return
    with LOCK,tx() as db:
        notice=db.get(Notice,notice_id)
        if notice:notice.status='sent';notice.delivered=now();notice.error=None

def worker():
    maintenance_at=0
    while not STOP.is_set():
        try:
            tick()
            if now()-maintenance_at>60:
                maintenance();maintenance_at=now()
        except Exception:logging.exception('Worker tick failed')
        STOP.wait(.5)

def maintenance():
    queued=[];deleted_resume_ids=set();live_resume_ids=set()
    with LOCK,tx() as db:
        for u in list(db.scalars(select(User).where(User.status=='pending_deletion',User.delete_at<=now()))):
            deleted_resume_ids.update(db.scalars(select(Resume.id).where(Resume.user_id==u.id)))
            for f in (VAR/'mail').glob('*.json'):
                try:
                    if json.loads(f.read_text(encoding='utf-8'))['email']==u.email:f.unlink()
                except (OSError,ValueError):pass
            attempt_ids=list(db.scalars(select(Attempt.id).where(Attempt.user_id==u.id)))
            if attempt_ids:
                item_ids=list(db.scalars(select(Item.id).where(Item.attempt_id.in_(attempt_ids))))
                if item_ids:db.execute(delete(Job).where(Job.target.in_(item_ids)))
            db.execute(update(Challenge).where(Challenge.author==u.id).values(author='deleted-user'))
            db.execute(update(Challenge).where(Challenge.reviewer==u.id).values(reviewer='deleted-user'))
            db.execute(update(LearningResource).where(LearningResource.author==u.id).values(author='deleted-user'))
            db.execute(update(LearningResource).where(LearningResource.reviewer==u.id).values(reviewer='deleted-user'))
            db.execute(update(BadgeDefinition).where(BadgeDefinition.author==u.id).values(author='deleted-user'))
            db.execute(update(AppSetting).where(AppSetting.updated_by==u.id).values(updated_by='deleted-user'))
            for event in db.scalars(select(Audit).where(Audit.actor==u.id)):
                event.actor='deleted-user';event.target=''
            db.delete(u)
        db.execute(delete(Token).where(Token.expires<now()))
        db.execute(delete(AuthSession).where(AuthSession.created<now()-604800))
        db.execute(delete(Idempotency).where(Idempotency.created<now()-86400))
        db.execute(update(Job).where(Job.status=='running',Job.updated<now()-180).values(status='queued',updated=now(),error='Recovered after worker lease expired'))
        db.execute(delete(ShareAccess).where(ShareAccess.created<now()-365*86400))
        db.execute(delete(Notice).where(Notice.status.in_(['sent','cancelled','failed']),Notice.created<now()-180*86400))
        db.execute(delete(ReportShare).where(ReportShare.expires<now()-365*86400,ReportShare.revoked.is_not(None)))
        for u in db.scalars(select(User).where(User.status=='active',User.verified==True)):
            prefs=u.preferences or {};tz=ZoneInfo(u.profile.get('timezone','UTC'));local=datetime.now(tz);day_key=local.date().isoformat()
            if prefs.get('gamification',True) and prefs.get('notify_quest_reminders') and 18<=local.hour<21:
                start=datetime.combine(local.date(),day_time.min,tzinfo=tz).timestamp();end=datetime.combine(local.date()+timedelta(days=1),day_time.min,tzinfo=tz).timestamp()
                practiced=db.scalar(select(Activity.key).where(Activity.user_id==u.id,Activity.kind=='practice',Activity.created>=start,Activity.created<end).limit(1))
                key=f'{u.id}:quest_reminder:{day_key}'
                if not practiced and not db.get(Notice,key):db.add(Notice(key=key,user_id=u.id,kind='quest_reminder',payload={'day':day_key}))
            if prefs.get('gamification',True) and prefs.get('notify_weekly_recap') and local.weekday()==0 and 9<=local.hour<21:
                recap_data=weekly_recap(db,u);key=f'{u.id}:weekly_recap:{recap_data["week_start"]}' if recap_data else None
                if recap_data and not db.get(Notice,key):db.add(Notice(key=key,user_id=u.id,kind='weekly_recap',payload=recap_data))
            retention=int(prefs.get('resume_retention_days',0) or 0)
            if retention:
                cutoff=now()-retention*86400
                for resume in list(db.scalars(select(Resume).where(Resume.user_id==u.id,Resume.created<cutoff))):
                    for claim in db.scalars(select(Claim).where(Claim.resume_id==resume.id)):
                        claim.resume_id=None;claim.evidence=[]
                    deleted_resume_ids.add(resume.id);db.delete(resume);audit(db,u,'resume.retention_deleted',resume.id)
        live_resume_ids=set(db.scalars(select(Resume.id)))
        db.flush();queued=[x.key for x in db.scalars(select(Notice).where(Notice.status=='queued').order_by(Notice.created).limit(20))]
    for resume_id in deleted_resume_ids:
        try:(VAR/'resumes'/(resume_id+'.bin')).unlink(missing_ok=True)
        except OSError:logging.warning('Resume file cleanup deferred after deletion: %s',resume_id)
    stale_before=now()-86400
    for file in (VAR/'resumes').glob('*.bin'):
        try:
            if file.stem not in live_resume_ids and file.stat().st_mtime<stale_before:file.unlink(missing_ok=True)
        except OSError:logging.warning('Orphan resume file cleanup deferred: %s',file.name)
    for notice_id in queued:deliver_notice(notice_id)
    check_due_resource_link()

def check_due_resource_link():
    with LOCK,tx() as db:
        row=next((row for row in db.scalars(select(LearningResource).where(LearningResource.status=='published')) if resource_details(row).get('url') and resource_details(row).get('link_checked_at',0)<now()-7*86400),None)
        if not row:return
        resource_id=row.id;url=resource_details(row)['url']
    result=check_link(url)
    with LOCK,tx() as db:
        row=db.get(LearningResource,resource_id)
        if row and resource_details(row).get('url')==url:
            row.details={**(row.details or {}),**result};audit(db,None,'learning_resource.link_checked',resource_id)

def initialize():
    from sqlalchemy import inspect,text
    if ENV=='production':
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        scripts=ScriptDirectory.from_config(Config(str(ROOT/'backend'/'alembic.ini')))
        expected=set(scripts.get_heads())
        inspector=inspect(engine)
        if not inspector.has_table('alembic_version'):
            raise RuntimeError('Production schema is not migrated. Run Alembic upgrade before starting the API.')
        with engine.connect() as conn:
            applied=set(conn.execute(text('SELECT version_num FROM alembic_version')).scalars().all())
        if not expected or applied!=expected:
            raise RuntimeError(f'Production schema revisions {sorted(applied)!r} do not match migration heads {sorted(expected)!r}.')
    else:
        Base.metadata.create_all(engine)
        columns={column['name'] for column in inspect(engine).get_columns('learning_paths')}
        if 'archived' not in columns:
            with engine.begin() as conn:conn.execute(text('ALTER TABLE learning_paths ADD COLUMN archived BOOLEAN NOT NULL DEFAULT FALSE'))
        for table in ['learning_resources','badge_definitions']:
            if 'details' not in {column['name'] for column in inspect(engine).get_columns(table)}:
                with engine.begin() as conn:conn.execute(text(f"ALTER TABLE {table} ADD COLUMN details JSON NOT NULL DEFAULT '{{}}'"))
    if engine.dialect.name=='sqlite':
        with engine.begin() as conn:conn.execute(text("CREATE TRIGGER IF NOT EXISTS frozen_reports BEFORE UPDATE OF result ON attempts WHEN OLD.result IS NOT NULL AND OLD.result != 'null' AND NEW.result != OLD.result BEGIN SELECT RAISE(ABORT, 'completed report is immutable'); END"))
    with LOCK,tx() as db:
        seed(db)
        seed_resources(db);seed_badges(db)
        for key,value in [('registration_open',True),('reassess_cooldown_hours',COOLDOWN_H),('llm_enabled',False)]:
            if not db.get(AppSetting,key):db.add(AppSetting(key=key,value={'value':value}))
        db.execute(update(Job).where(Job.status=='running',Job.updated<now()-180).values(status='queued',updated=now(),error='Recovered after worker lease expired'))

@asynccontextmanager
async def lifespan(app):
    initialize();t=None
    if RUN_BACKGROUND_WORKER:
        STOP.clear();t=threading.Thread(target=worker,daemon=True);t.start()
    yield
    if t:STOP.set();t.join(timeout=5)

app=FastAPI(title='SkillTrial API',version='0.1.0',lifespan=lifespan)

@app.middleware('http')
async def headers(request,call_next):
    request.state.request_id=uid()
    # Cookie mutations are same-origin. API is served behind the frontend proxy.
    if request.method not in ['GET','HEAD','OPTIONS']:
        origin=request.headers.get('origin')
        if origin:
            from urllib.parse import urlparse
            allowed=set(os.environ.get('ALLOWED_ORIGINS','http://127.0.0.1:5173,http://localhost:5173' if ENV=='development' else '').split(','))
            if urlparse(origin).netloc!=request.headers.get('host') and origin not in allowed:
                return JSONResponse({'error':{'code':'ORIGIN_REJECTED','message':'Cross-origin requests are not permitted.'}},403)
    response=await call_next(request)
    response.headers.update({'X-Request-Id':request.state.request_id,'X-Server-Time':str(now()),'X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin','X-Frame-Options':'DENY','Cache-Control':'no-store'})
    if request.url.path.startswith('/api/v1/public/shares/'):response.headers['X-Robots-Tag']='noindex, nofollow, noarchive'
    return response

@app.exception_handler(HTTPException)
async def domain_error(request,e):
    error=e.detail if isinstance(e.detail,dict) else {'code':'REQUEST_FAILED','message':str(e.detail)}
    return JSONResponse({'error':{**error,'request_id':getattr(request.state,'request_id','')}},e.status_code)

@app.exception_handler(RequestValidationError)
async def invalid(request,e):return JSONResponse({'error':{'code':'VALIDATION_FAILED','message':'Check the form fields and try again.','details':[{'field':str(x['loc'][-1]),'message':x['msg']} for x in e.errors()],'request_id':request.state.request_id}},422)

@app.exception_handler(IntegrityError)
async def conflict(request,e):return JSONResponse({'error':{'code':'CONFLICT','message':'This change conflicts with an existing record. Refresh and try again.','request_id':request.state.request_id}},409)

class Model(BaseModel):model_config=ConfigDict(extra='forbid')
class Credentials(Model):
    email:str=Field(min_length=5,max_length=254)
    password:str=Field(min_length=1,max_length=200)
class Registration(Credentials):
    name:str=Field(min_length=2,max_length=80)
    accept_privacy:bool
    demo_completed:bool=False
class ClaimBody(Model):
    skill:str
    level:str|None=None
class ClaimPatch(Model):
    level:str|None=None
    status:str|None=None
    selected:bool|None=None
class AssessmentBody(Model):
    claim_id:str|None=None
    challenge_id:str|None=None
    level:str='intermediate'
    mode:str='formal'
    acknowledge:bool=True
    path_id:str|None=None
    path_item_id:str|None=None
    ai_explanation_opt_in:bool=False
class Draft(Model):
    payload:dict
    revision:int=Field(ge=1)
class Submission(Model):payload:dict

def user_view(u):return {'id':u.id,'email':u.email,'name':u.name,'role':u.role,'verified':u.verified,'profile':u.profile,'preferences':{'gamification':True,'celebrations':'subtle','theme':'observatory','sounds':False,'notify_quest_reminders':False,'notify_weekly_recap':False,'resume_retention_days':0,'ai_resume_extraction':False,'ai_explanation_feedback':False,**(u.preferences or {})},'status':u.status,'delete_at':u.delete_at,'development':ENV=='development'}
def claim_view(c):return {'id':c.id,'skill':c.skill,'name':skill(c.skill)['name'],'competencies':skill(c.skill)['competencies'],'level':c.level,'original_level':c.original_level,'status':c.status,'selected':c.selected,'evidence':c.evidence,'confidence':c.confidence,'source':c.source}
def attempt_summary(a):return {'id':a.id,'skill':a.skill,'skill_name':skill(a.skill)['name'],'level':a.level,'mode':a.mode,'status':a.status,'deadline':a.deadline,'created':a.created,'completed':a.completed,'result':a.result['result'] if a.result else None,'ref':a.result['ref'] if a.result else None,'ai_explanation_opt_in':bool((a.policy or {}).get('ai_explanation_opt_in',False))}

def setting_value(db,key,default):
    row=db.get(AppSetting,key);return row.value.get('value',default) if row else default

def week_window(tz=timezone.utc):
    local=datetime.now(tz);monday=local.date()-timedelta(days=local.weekday())
    return datetime.combine(monday,day_time.min,tzinfo=tz).timestamp(),datetime.combine(monday+timedelta(days=7),day_time.min,tzinfo=tz).timestamp(),monday

LEAGUE_ADJECTIVES=['amber','bright','calm','cosmic','curious','distant','gentle','golden','lunar','quiet','steady','violet']
LEAGUE_NOUNS=['comet','fox','meteor','nebula','orbit','otter','panda','pulsar','quasar','raven','star','turtle']
LEAGUE_BLOCKED={'admin','moderator','support','staff','skilltrial','fuck','shit','bitch','asshole','cunt','nazi'}
def league_alias():return random.choice(LEAGUE_ADJECTIVES)+'_'+random.choice(LEAGUE_NOUNS)+'_'+str(secrets.randbelow(90)+10)

def league_view(db,u):
    member=db.get(LeagueMember,u.id);joined=bool(member);alias=member.alias if member else None
    if not joined:return {'joined':False,'alias':alias,'leaderboard':[],'rank':None,'week_start':datetime.now(timezone.utc).date().isoformat()}
    start,end,monday=week_window();my_level=progress(db,u)['level'];band=my_level//5
    eligible=[m for m in db.scalars(select(LeagueMember)) if m.user_id==u.id or (db.get(User,m.user_id) and db.get(User,m.user_id).status=='active' and progress(db,db.get(User,m.user_id))['level']//5==band)];entries=[]
    for entry in eligible:
        earned=db.scalars(select(Activity).where(Activity.user_id==entry.user_id,Activity.kind=='orbit_award',Activity.created>=start,Activity.created<end));points=sum(int(e.facts.get('points',0)) for e in earned)
        entries.append({'alias':entry.alias,'weekly_xp':points,'you':entry.user_id==u.id})
    entries.sort(key=lambda x:(-x['weekly_xp'],x['alias'].casefold()))
    own=next((i+1 for i,x in enumerate(entries) if x['you']),None);visible=entries[:20]
    if own and own>20:visible.append(entries[own-1])
    return {'joined':True,'alias':alias,'rank':own,'rank_band':band,'week_start':monday.isoformat(),'leaderboard':visible,'group_size':len(entries)}

def share_public_view(db,share):
    owner=db.get(User,share.user_id);options=share.options or {};reports=[]
    for link in db.scalars(select(ReportShareItem).where(ReportShareItem.share_id==share.id)):
        attempt=db.get(Attempt,link.attempt_id)
        if not attempt or not attempt.result:continue
        snap=attempt.result;result=snap.get('result',{});row={'ref':snap.get('ref'),'date':snap.get('date'),'skill':snap.get('skill_name'),'level':snap.get('level'),'status':result.get('status'),'overall':result.get('overall'),'claim':snap.get('claim'),'fingerprint':attempt.report_hash,'limitations':snap.get('limitations',[])}
        if options.get('include_verification_reason',True):row['reasons']=result.get('reasons',[])
        if options.get('include_evidence_details',True):
            row['competencies']=[{'name':x.get('name'),'status':x.get('status'),'score':x.get('score')} for x in result.get('competencies',[])]
            row['challenges']=[{'title':x.get('title'),'type':x.get('type'),'difficulty':x.get('difficulty'),'status':x.get('status'),'ratio':(x.get('evaluation') or {}).get('ratio')} for x in snap.get('challenges',[])]
        reports.append(row)
    return {'label':share.label,'candidate':(owner.profile.get('share_display_name') or owner.name) if options.get('include_name') else 'Candidate','reports':reports,'created':share.created,'expires':share.expires,'fingerprint_note':'Each result is an immutable report snapshot. Private resumes, email addresses, submissions, source code, assessment history, and game data are not shared.'}
def challenge_view(c):return {'id':c.id,'slug':c.slug,'skill':c.skill,'type':c.type,'title':c.content['title'],'level':c.level,'minutes':c.content.get('minutes',12),'competencies':c.content['competencies'],'pool':c.pool}
def token_email(db,u,kind):
    token=issue_token(db,u,kind);base=os.environ.get('PUBLIC_APP_URL',os.environ.get('APP_URL','http://127.0.0.1:5173')).rstrip('/');url=f"{base}/{'reset-password' if kind=='reset' else 'verify-email'}?token={token}"
    if os.environ.get('SMTP_HOST'):
        msg=EmailMessage();msg['From']=os.environ.get('SMTP_FROM','hello@skilltrial.local');msg['To']=u.email;msg['Subject']='Reset your password' if kind=='reset' else 'Verify your SkillTrial email';msg.set_content(url);smtp_send(msg)
    elif ENV=='development':
        folder=VAR/'mail';folder.mkdir(exist_ok=True)
        (folder/(uid()+'.json')).write_text(json.dumps({'email':u.email,'kind':kind,'url':url,'created':now()}),encoding='utf-8')
    else:fail('SMTP_REQUIRED','Email delivery is not configured.',503)

@app.get('/healthz')
def health():return {'status':'ok','version':'0.1.0'}

@app.post('/api/v1/auth/register',status_code=202)
def register(body:Registration,request:Request):
    email=body.email.strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):fail('INVALID_EMAIL','Enter a valid email address.',422)
    rate('register:'+request.client.host,10,3600)
    if not body.accept_privacy:fail('PRIVACY_REQUIRED','Please accept the privacy notice.',422)
    password_ok(body.password,email)
    with LOCK,tx() as db:
        if not setting_value(db,'registration_open',True):fail('REGISTRATION_CLOSED','New account registration is temporarily closed.',403)
        if not db.scalar(select(User).where(User.email==email)):
            u=User(email=email,password=HASHER.hash(body.password),name=body.name.strip());db.add(u);db.flush();token_email(db,u,'verify');audit(db,u,'user.registered')
            if body.demo_completed:award(db,u,'mission:demo',15,'Spot the Bug demo')
    return {'message':'If this is a new address, your account is ready. Sign in and verify your email.'}

@app.post('/api/v1/auth/login')
def login(body:Credentials,request:Request,response:Response):
    rate('login:'+request.client.host,30,900)
    with LOCK,tx() as db:
        u=db.scalar(select(User).where(User.email==body.email.strip().lower()))
        if u and u.locked_until>now():fail('ACCOUNT_LOCKED','Too many attempts. Try again in 15 minutes.',423)
        try:HASHER.verify(u.password if u else DUMMY,body.password);valid=bool(u and u.status in ['active','pending_deletion'])
        except Exception:valid=False
        if not valid:
            if u:
                u.failures+=1
                if u.failures>=5:u.locked_until=now()+900;u.failures=0
                db.commit()
            fail('INVALID_CREDENTIALS','Email or password is incorrect.',401)
        u.failures=0;token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
        db.add(AuthSession(token=hashed(token),user_id=u.id,csrf=csrf));audit(db,u,'user.login')
        response.set_cookie('st_session',token,httponly=True,secure=COOKIE_SECURE,samesite='lax',max_age=604800,path='/')
        response.set_cookie('st_csrf',csrf,httponly=False,secure=COOKIE_SECURE,samesite='lax',max_age=604800,path='/')
        return user_view(u)

@app.post('/api/v1/auth/logout')
def logout(request:Request,response:Response):
    with LOCK,tx() as db:
        u=auth(db,request);db.execute(delete(AuthSession).where(AuthSession.token==hashed(request.cookies['st_session'])));audit(db,u,'user.logout')
    response.delete_cookie('st_session');response.delete_cookie('st_csrf');return {'ok':True}

@app.get('/api/v1/me')
def me(request:Request):
    with tx() as db:return user_view(auth(db,request))

@app.patch('/api/v1/me/profile')
def profile(body:dict,request:Request):
    allowed={'name','headline','roles','goal','timezone','onboarded'}
    if set(body)-allowed:fail('INVALID_FIELD','Unknown profile field.',422)
    if body.get('timezone'):
        try:ZoneInfo(body['timezone'])
        except (ZoneInfoNotFoundError,ValueError):fail('BAD_TIMEZONE','Choose a valid timezone.',422)
    if len(json.dumps(body))>3000:fail('TOO_LONG','Your profile is too long.',422)
    with LOCK,tx() as db:
        u=auth(db,request)
        if 'name' in body:
            name=str(body.pop('name')).strip()
            if not 2<=len(name)<=80:fail('INVALID_NAME','Use a display name of 2–80 characters.',422)
            u.name=name
        u.profile={**u.profile,**body}
        if body.get('onboarded'):award(db,u,'mission:onboard',20,'Create your Challenger');activity(db,u,'onboard','onboard')
        return user_view(u)

@app.patch('/api/v1/me/preferences')
def preferences(body:dict,request:Request):
    if set(body)-{'gamification','celebrations','theme','sounds','notify_quest_reminders','notify_weekly_recap','resume_retention_days','ai_resume_extraction','ai_explanation_feedback'}:fail('INVALID_FIELD','Unknown preference.',422)
    if 'theme' in body and body['theme'] not in ['observatory','daylight','high_contrast']:fail('INVALID_THEME','Choose an available theme.',422)
    if 'celebrations' in body and body['celebrations'] not in ['off','subtle','full']:fail('INVALID_CELEBRATION_STYLE','Choose full, subtle, or off.',422)
    if any(k in body and not isinstance(body[k],bool) for k in ['gamification','sounds','notify_quest_reminders','notify_weekly_recap','ai_resume_extraction','ai_explanation_feedback']):fail('INVALID_PREFERENCE','Choose a valid on or off setting.',422)
    if 'resume_retention_days' in body and body['resume_retention_days'] not in [0,30,90,365]:fail('INVALID_RETENTION','Choose never, 30, 90, or 365 days.',422)
    with LOCK,tx() as db:
        u=auth(db,request);u.preferences={**u.preferences,**body};return user_view(u)

@app.post('/api/v1/auth/token')
def consume_token(body:dict):
    with LOCK,tx() as db:
        t=db.get(Token,hashed(str(body.get('token',''))))
        if not t or t.expires<now():fail('TOKEN_INVALID','This link is invalid or expired.',422)
        u=db.get(User,t.user_id)
        if t.kind=='reset':
            password_ok(body.get('password',''),u.email);u.password=HASHER.hash(body['password']);db.execute(delete(AuthSession).where(AuthSession.user_id==u.id))
        else:u.verified=True
        db.delete(t);return {'ok':True}

@app.post('/api/v1/auth/forgot-password',status_code=202)
def forgot(body:dict,request:Request):
    rate('forgot:'+request.client.host,5,3600)
    with LOCK,tx() as db:
        u=db.scalar(select(User).where(User.email==str(body.get('email','')).lower()))
        if u:token_email(db,u,'reset')
    return {'message':'If the account exists, a reset link has been sent.'}

@app.post('/api/v1/auth/resend-verification')
def resend(request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);rate('verify:'+u.id,3,3600);token_email(db,u,'verify');return {'ok':True}

@app.get('/api/v1/dev/mail')
def mail(request:Request):
    if ENV!='development':fail('NOT_FOUND','Not found.',404)
    with tx() as db:
        u=auth(db,request);messages=[]
        for f in (VAR/'mail').glob('*.json'):
            m=json.loads(f.read_text(encoding='utf-8'))
            if m['email']==u.email:messages.append(m)
        return sorted(messages,key=lambda x:-x['created'])[:5]

@app.get('/api/v1/skills')
def skills():
    with tx() as db:
        return [{**s,'assessable':bool(assessment_levels(db,s['slug'])),'levels':assessment_levels(db,s['slug'])} for s in SKILLS]

@app.get('/api/v1/me/skills')
def claims(request:Request):
    with tx() as db:
        u=auth(db,request);return [claim_view(c) for c in db.scalars(select(Claim).where(Claim.user_id==u.id))]

@app.post('/api/v1/me/skills')
def add_claim(body:ClaimBody,request:Request):
    if not skill(body.skill):fail('SKILL_UNKNOWN','Choose a skill from the catalog.',422)
    if body.level is not None and body.level not in LEVELS:fail('INVALID_LEVEL','Choose a valid proficiency level.',422)
    with LOCK,tx() as db:
        u=auth(db,request);c=db.scalar(select(Claim).where(Claim.user_id==u.id,Claim.skill==body.skill))
        if c:c.status='confirmed';c.level=body.level
        else:c=Claim(user_id=u.id,skill=body.skill,level=body.level,status='confirmed');db.add(c)
        db.flush();activity(db,u,'confirmed:'+c.id,'confirmed',{'skill':c.skill});award(db,u,'mission:confirmed',30,'Confirm your claims');audit(db,u,'claim.added',c.id);return claim_view(c)

@app.patch('/api/v1/me/skills/{id}')
def patch_claim(id:str,body:ClaimPatch,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);c=owned(db,Claim,id,u)
        if 'level' in body.model_fields_set:
            if body.level is not None and body.level not in LEVELS:fail('INVALID_LEVEL','Choose a valid proficiency level.',422)
            c.level=body.level
        if body.status:
            if body.status not in ['confirmed','removed','pending_review']:fail('INVALID_STATUS','Unknown claim state.',422)
            c.status=body.status
        if body.selected is not None:
            if body.selected and c.status!='confirmed':fail('CONFIRM_CLAIM_FIRST','Confirm this claim first.',409)
            c.selected=body.selected
        if c.status=='confirmed':
            activity(db,u,'confirmed:'+c.id,'confirmed',{'skill':c.skill});award(db,u,'mission:confirmed',30,'Confirm your claims')
        audit(db,u,'claim.updated',c.id);return claim_view(c)

@app.post('/api/v1/resumes',status_code=201)
async def upload(request:Request,file:UploadFile=File(...)):
    with tx() as db:auth(db,request)
    data=await file.read(5*1024*1024+1);text,warnings=read_resume(data,file.filename or 'resume')
    found=extract(text)
    fingerprint=hashed(data.hex())
    with LOCK,tx() as db:
        candidate=auth(db,request)
        same=db.scalar(select(Resume).where(Resume.user_id==candidate.id,Resume.digest==fingerprint))
        if same:return {'id':same.id,'status':same.status,'detail':same.detail}
        rate('upload:'+candidate.id,10,86400);llm_allowed=bool(LLM_READY and setting_value(db,'llm_enabled',False) and (candidate.preferences or {}).get('ai_resume_extraction',False));candidate_name=candidate.name
    if llm_allowed:
        try:
            assisted=await asyncio.to_thread(extract_claims,text,[candidate_name])
            existing={item['skill'] for item in found}
            found.extend({**item,'source':'ai_assisted'} for item in assisted if item['skill'] not in existing)
        except LLMUnavailable:
            pass
    with LOCK,tx() as db:
        u=auth(db,request)
        same=db.scalar(select(Resume).where(Resume.user_id==u.id,Resume.digest==fingerprint))
        if same:return {'id':same.id,'status':same.status,'detail':same.detail}
        r=Resume(user_id=u.id,filename=FilePath(file.filename or 'resume').name,digest=fingerprint,status='parsed',detail={'claims':len(found),'warnings':warnings});db.add(r);db.flush()
        folder=VAR/'resumes';folder.mkdir(exist_ok=True);(folder/(r.id+'.bin')).write_bytes(CRYPT.encrypt(data))
        for x in found:
            c=db.scalar(select(Claim).where(Claim.user_id==u.id,Claim.skill==x['skill']))
            if not c:db.add(Claim(user_id=u.id,resume_id=r.id,skill=x['skill'],level=x['level'],original_level=x['level'],source=x.get('source','extracted'),evidence=x['evidence'],confidence=x['confidence'],status='pending_review'))
        award(db,u,'mission:resume',30,'Scan your resume');audit(db,u,'resume.uploaded',r.id)
        return {'id':r.id,'status':r.status,'detail':r.detail}

@app.get('/api/v1/resumes')
def resume_list(request:Request):
    with tx() as db:
        u=auth(db,request);return [{'id':r.id,'filename':r.filename,'status':r.status,'detail':r.detail,'created':r.created} for r in db.scalars(select(Resume).where(Resume.user_id==u.id).order_by(Resume.created.desc()))]

@app.delete('/api/v1/resumes/{id}')
def delete_resume(id:str,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);r=owned(db,Resume,id,u)
        for claim in list(db.scalars(select(Claim).where(Claim.resume_id==r.id))):
            if claim.status=='pending_review':db.delete(claim)
            else:
                claim.resume_id=None;claim.evidence=[]
        db.delete(r);audit(db,u,'resume.deleted',id)
    try:(VAR/'resumes'/(id+'.bin')).unlink(missing_ok=True)
    except OSError:logging.warning('Resume file cleanup deferred after deletion: %s',id)
    return {'ok':True}

@app.get('/api/v1/sample-resume')
def sample():return FileResponse(ROOT/'content'/'sample_resumes'/'sample_resume.txt',filename='skilltrial_sample_resume.txt')

def eligibility(db,u,slug):
    active=db.scalar(select(Attempt).where(Attempt.user_id==u.id,Attempt.skill==slug,Attempt.mode=='formal',Attempt.status.in_(['created','in_progress','evaluating'])))
    if active:return {'ok':False,'code':'ATTEMPT_ACTIVE','attempt_id':active.id}
    last=db.scalar(select(Attempt).where(Attempt.user_id==u.id,Attempt.skill==slug,Attempt.mode=='formal',Attempt.status=='completed').order_by(Attempt.completed.desc()))
    cooldown=float(setting_value(db,'reassess_cooldown_hours',COOLDOWN_H))
    if last and not last.result['result']['infra_incident'] and last.completed+cooldown*3600>now():return {'ok':False,'code':'REASSESS_COOLDOWN','available_at':last.completed+cooldown*3600}
    return {'ok':True}

def assessment_families(db,slug):
    rows=list(db.scalars(select(Challenge).where(Challenge.skill==slug,Challenge.pool=='assessment',Challenge.status=='published').order_by(Challenge.version)))
    latest={}
    for row in rows:latest[row.family]=row
    return list(latest.values())

def assessment_levels(db,slug):
    families=assessment_families(db,slug);required=set((skill(slug) or {}).get('competencies',[]))
    baseline=[ch for ch in families if ch.level!='advanced']
    covered=set(x for ch in baseline for x in ch.content.get('competencies',[]))
    levels=['beginner','intermediate'] if len(baseline)>=3 and required and required<=covered else []
    advanced=[ch for ch in families if ch.level=='advanced']
    advanced_coverage=set(x for ch in advanced for x in ch.content.get('competencies',[]))
    if len(advanced)>=4 and required and required<=advanced_coverage:levels.append('advanced')
    return levels

@app.get('/api/v1/assessments/briefing/{claim_id}')
def briefing(claim_id:str,request:Request,level:str|None=None):
    with tx() as db:
        u=auth(db,request);c=owned(db,Claim,claim_id,u)
        supported=assessment_levels(db,c.skill)
        if level is None:level=next((x for x in ['intermediate','beginner','advanced'] if x in supported),None)
        if level not in supported:fail('LEVEL_UNAVAILABLE','There is not enough published content for that assessment level.',409,supported_levels=supported)
        choices=assessment_families(db,c.skill)
        if level=='advanced':choices=[ch for ch in choices if ch.level=='advanced']
        else:choices=[ch for ch in choices if ch.level!='advanced']
        ai_available=bool(LLM_READY and setting_value(db,'llm_enabled',False) and (u.preferences or {}).get('ai_explanation_feedback',False) and any(x.content.get('explanation_rubric') for x in choices))
        return {'claim':claim_view(c),'level':level,'tasks':[challenge_view(x) for x in choices],'duration':sum(x.content.get('minutes',12)*60 for x in choices),'policy':policy(c.skill,level),'eligibility':eligibility(db,u,c.skill),'supported_levels':supported,'ai_explanation_available':ai_available,'content_preview':any(x.validation.get('demo_preview') for x in choices)}

@app.post('/api/v1/assessments',status_code=201)
def create_attempt(body:AssessmentBody,request:Request):
    if body.mode not in ['formal','practice'] or not body.acknowledge:fail('BRIEFING_REQUIRED','Read and acknowledge the assessment rules.',422)
    with LOCK,tx() as db:
        u=auth(db,request)
        if body.mode=='practice':
            ch=db.get(Challenge,body.challenge_id)
            if not ch or ch.pool!='practice' or ch.status not in ['published','unpublished']:fail('NOT_FOUND','Practice challenge not found.',404)
            if ch.status!='published' and not (body.path_id and body.path_item_id):fail('NOT_FOUND','Practice challenge not found.',404)
            if body.path_id or body.path_item_id:
                if not body.path_id or not body.path_item_id:fail('INVALID_FIELD','A learning path and waypoint are both required.',422)
                path=owned(db,Path,body.path_id,u)
                if path.archived:fail('PATH_ARCHIVED','Restore this learning path before starting its waypoint.',409)
                position=next((n for n,item in enumerate(path.items) if item['id']==body.path_item_id),None)
                if position is None or path.items[position].get('challenge_id')!=ch.id:fail('NOT_FOUND','Learning waypoint not found.',404)
                if any(item.get('status')!='completed' for item in path.items[:position]):fail('WAYPOINT_LOCKED','Complete the earlier learning waypoint first.',409)
            choices=[ch];slug=ch.skill;level=ch.level;claim={'level':None,'original_level':None}
        else:
            c=owned(db,Claim,body.claim_id,u)
            if c.status!='confirmed':fail('CONFIRM_CLAIM_FIRST','Confirm your claim before assessment.',409)
            slug=c.skill;level=body.level
            supported=assessment_levels(db,slug)
            if level not in supported:fail('CONTENT_INSUFFICIENT','There is not enough published content for that assessment level.',409,supported_levels=supported)
            e=eligibility(db,u,slug)
            if not e['ok']:fail(e['code'],'Resume your active assessment or wait until the reassessment cooldown ends.',409,**{key:value for key,value in e.items() if key!='code'})
            choices=assessment_families(db,slug)
            if level=='advanced':choices=[ch for ch in choices if ch.level=='advanced']
            else:choices=[ch for ch in choices if ch.level!='advanced']
            random.SystemRandom().shuffle(choices)
            covered=set(x for ch in choices for x in ch.content['competencies'])
            if len(choices)<3 or not set(skill(slug)['competencies'])<=covered:fail('CONTENT_INSUFFICIENT','There is not enough validated content for this skill.',503)
            claim={'level':c.level,'original_level':c.original_level,'confirmed_skill':slug}
        ai_available=bool(LLM_READY and setting_value(db,'llm_enabled',False) and (u.preferences or {}).get('ai_explanation_feedback',False) and any(c.content.get('explanation_rubric') for c in choices))
        if body.ai_explanation_opt_in and body.mode!='formal':fail('AI_NOT_AVAILABLE','Written-explanation AI feedback is available for formal Trials only.',409)
        if body.ai_explanation_opt_in and not ai_available:fail('AI_NOT_AVAILABLE','Optional AI explanation feedback is not enabled for this account and assessment.',409)
        attempt_policy=policy(slug,level);attempt_policy['ai_explanation_opt_in']=bool(body.ai_explanation_opt_in);attempt_policy['content_preview']=any(c.validation.get('demo_preview') for c in choices)
        a=Attempt(user_id=u.id,skill=slug,level=level,mode=body.mode,claim_snapshot=claim,policy=attempt_policy,duration=sum(c.content.get('minutes',12)*60 for c in choices));db.add(a);db.flush()
        for n,ch in enumerate(choices):db.add(Item(attempt_id=a.id,challenge_id=ch.id,ordinal=n))
        audit(db,u,'attempt.created',a.id);return attempt_summary(a)

@app.post('/api/v1/assessments/{id}/start')
def start(id:str,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);a=owned(db,Attempt,id,u)
        if a.status=='created':a.started=now();a.deadline=a.started+a.duration;a.status='in_progress';audit(db,u,'attempt.started',a.id)
        elif a.status!='in_progress':fail('ATTEMPT_NOT_ACTIVE','This assessment cannot be started.',409)
        return attempt_summary(a)

@app.get('/api/v1/assessments/{id}')
def attempt(id:str,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);a=owned(db,Attempt,id,u)
        if a.status=='in_progress' and now()>a.deadline+GRACE:finalize(db,a,'deadline_reached')
        out=attempt_summary(a);out['duration']=a.duration;out['server_time']=now()
        out['items']=[{'id':i.id,'ordinal':i.ordinal,'status':i.status,'revision':i.revision,'saved':i.saved,'draft':i.draft,'challenge':public_content(db.get(Challenge,i.challenge_id),i.hints,i.id),'evaluation':visible_evaluation(i.evaluation,a.mode=='practice') if a.status=='completed' else None} for i in db.scalars(select(Item).where(Item.attempt_id==a.id).order_by(Item.ordinal))]
        return out

def writable(db,u,id,item_id):
    a=owned(db,Attempt,id,u)
    if a.status!='in_progress' or now()>a.deadline+GRACE:fail('ATTEMPT_DEADLINE_PASSED','This assessment is no longer accepting work.',409)
    i=db.get(Item,item_id)
    if not i or i.attempt_id!=a.id:fail('NOT_FOUND','Task not found.',404)
    if i.submission is not None:fail('ITEM_ALREADY_SUBMITTED','This task already has a final submission.',409)
    return a,i,db.get(Challenge,i.challenge_id)

def validate_payload(p,c):
    if len(json.dumps(p).encode())>200000:fail('PAYLOAD_TOO_LARGE','Your response exceeds 200 KB.',422)
    fields={'code','query','answers','decisions','categories','counterexample','expected','target','explanation','defect_category','defect_lines'}
    if set(p)-fields:fail('INVALID_PAYLOAD','Unknown response fields.',422)
    for key in ['code','query','counterexample','expected','explanation']:
        if key in p and not isinstance(p[key],str):fail('INVALID_PAYLOAD','Response fields must have the expected format.',422)
    for key in ['answers','decisions','categories']:
        if key in p and not isinstance(p[key],dict):fail('INVALID_PAYLOAD','Choices must be structured answers.',422)

@app.put('/api/v1/assessments/{id}/items/{item_id}/draft')
def save_draft(id:str,item_id:str,body:Draft,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);a,i,c=writable(db,u,id,item_id);validate_payload(body.payload,c)
        if body.revision<=i.revision:fail('STALE_DRAFT','This task was updated in another tab. Reload to continue.',409,current_revision=i.revision)
        i.draft=body.payload;i.revision=body.revision;i.saved=now();i.status='in_progress'
        return {'revision':i.revision,'saved':i.saved}

def idem_begin(db,u,request,payload):
    raw=request.headers.get('Idempotency-Key','')
    if not 8<=len(raw)<=100:fail('IDEMPOTENCY_KEY_REQUIRED','A retry key is required.',422)
    key=u.id+':'+raw;value=digest({'path':request.url.path,'payload':payload});old=db.get(Idempotency,key)
    if old and old.digest!=value:fail('IDEMPOTENCY_KEY_REUSED','This retry key belongs to another request.',409)
    return key,value,old

@app.post('/api/v1/assessments/{id}/items/{item_id}/submit',status_code=202)
def submit(id:str,item_id:str,body:Submission,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);key,value,old=idem_begin(db,u,request,body.payload)
        if old:return old.response
        a,i,c=writable(db,u,id,item_id);validate_payload(body.payload,c)
        if not substantive(c.content,body.payload):fail('EMPTY_SUBMISSION','Complete the task before submitting, or leave it unattempted.',422)
        i.submission=canonical_payload(c.content,i.id,body.payload);i.draft=copy.deepcopy(body.payload);i.status='submitted';enqueue(db,'evaluate',i.id)
        result={'id':i.id,'status':'submitted'};db.add(Idempotency(key=key,user_id=u.id,digest=value,response=result));return result

@app.post('/api/v1/assessments/{id}/finish')
def finish(id:str,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);key,value,old=idem_begin(db,u,request,{})
        if old:return old.response
        a=owned(db,Attempt,id,u);finalize(db,a,'deadline_reached' if a.deadline and now()>a.deadline else 'candidate_finished');complete(db,a)
        out=attempt_summary(a);db.add(Idempotency(key=key,user_id=u.id,digest=value,response=out));return out

@app.post('/api/v1/assessments/{id}/items/{item_id}/run')
def run_item(id:str,item_id:str,body:dict,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);a,i,ch=writable(db,u,id,item_id);validate_payload(body.get('payload',{}),ch)
        if i.run_count>=30 or now()-i.last_run<2:fail('RUN_LIMIT','Wait a moment before running again. There are 30 runs per task.',429)
        i.run_count+=1;i.last_run=now();c=copy.deepcopy(ch.content)
    try:
        if c['type']=='trust':
            target=next((s for s in c['suggestions'] if opaque(item_id,s['id'])==body.get('suggestion')),None)
            if not target:fail('SUGGESTION_REQUIRED','Choose a suggestion.',422)
            inp=body.get('input',[])
            if not isinstance(inp,list) or len(inp)>10000 or not all(isinstance(x,int) and not isinstance(x,bool) and abs(x)<=1000000 for x in inp):fail('INVALID_INPUT','Use an array of at most 10,000 integers between -1,000,000 and 1,000,000.',422)
            return code_run(c['language'],target['code'],inp)
        return {'results':[{**run(c,body.get('payload',{}),t.get('input'),t.get('dataset')),'label':t['label'],'expected':t['expected']} for t in c.get('tests',[]) if t['visibility']=='sample']}
    except RunnerUnavailable as e:fail('RUNNER_UNAVAILABLE',str(e),503)

@app.post('/api/v1/assessments/{id}/items/{item_id}/hint')
def hint(id:str,item_id:str,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);a,i,ch=writable(db,u,id,item_id)
        if a.mode!='practice':fail('PRACTICE_ONLY','Hints are only available in practice.',403)
        i.hints=min(i.hints+1,len(ch.content.get('hints',[])));return {'hints':ch.content.get('hints',[])[:i.hints]}

@app.get('/api/v1/history')
def history(request:Request):
    with tx() as db:
        u=auth(db,request);return [attempt_summary(a) for a in db.scalars(select(Attempt).where(Attempt.user_id==u.id).order_by(Attempt.created.desc()))]

@app.get('/api/v1/history/compare')
def compare(request:Request,a:str,b:str):
    with tx() as db:
        u=auth(db,request);x,y=owned(db,Attempt,a,u),owned(db,Attempt,b,u)
        if not x.result or not y.result or x.mode!='formal' or y.mode!='formal':fail('RESULTS_REQUIRED','Select two completed formal assessments.',422)
        shape=lambda snapshot:sorted((c.get('type'),c.get('difficulty'),c.get('content_hash')) for c in snapshot.get('challenges',[]))
        same_scope=x.skill==y.skill and x.level==y.level and x.policy==y.policy
        same_tasks=bool(x.result and y.result and shape(x.result)==shape(y.result))
        status='comparable' if same_scope and same_tasks else 'partially_comparable' if x.skill==y.skill else 'not_comparable'
        note='Same skill, level, policy, and challenge versions were used.' if status=='comparable' else 'The skill matches, but the level, policy, or challenge versions differ. Compare competency evidence rather than treating total scores as a direct trend.' if status=='partially_comparable' else 'The skill differs. Scores do not represent a direct improvement comparison.'
        return {'comparability':status,'before':x.result,'after':y.result,'notes':[note]}

@app.get('/api/v1/reports/{id}')
def report(id:str,request:Request):
    with tx() as db:
        u=auth(db,request);a=owned(db,Attempt,id,u)
        if not a.result:fail('RESULT_NOT_READY','Your assessment is still being evaluated.',409)
        return {'snapshot':a.result,'fingerprint':a.report_hash}

@app.get('/api/v1/reports/{id}/pdf')
def report_pdf(id:str,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);a=owned(db,Attempt,id,u)
        if not u.verified:fail('EMAIL_VERIFICATION_REQUIRED','Verify your email in Settings before downloading reports.',403)
        if not a.result or a.mode!='formal':fail('RESULT_NOT_READY','A completed formal assessment is required.',409)
        data=pdf(a.result,a.report_hash);award(db,u,'mission:report',20,'Download your first report');celebrate(db,u,'report:'+a.id,'Your report is ready','Your evidence report was downloaded.',1);audit(db,u,'report.downloaded',a.id)
        return Response(data,media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="SkillTrial_{a.skill}_{a.result["ref"]}.pdf"'})

@app.get('/api/v1/me/shares')
def share_list(request:Request):
    with tx() as db:
        u=auth(db,request);return [{'id':x.id,'label':x.label,'token_hint':x.token_hint,'created':x.created,'expires':x.expires,'revoked':x.revoked,'access_count':x.access_count,'last_accessed':x.last_accessed} for x in db.scalars(select(ReportShare).where(ReportShare.user_id==u.id).order_by(ReportShare.created.desc()))]

@app.post('/api/v1/me/shares',status_code=201)
def share_create(body:dict,request:Request):
    if set(body)-{'report_ids','label','expires_days','options'}:fail('INVALID_FIELD','Check the share settings.',422)
    ids=body.get('report_ids');label=str(body.get('label','')).strip();days=body.get('expires_days',30);options=body.get('options',{})
    if not isinstance(ids,list) or not 1<=len(ids)<=10 or any(not isinstance(x,str) for x in ids) or len(set(ids))!=len(ids):fail('INVALID_REPORTS','Choose one to ten unique reports.',422)
    if len(label)>80:fail('INVALID_LABEL','Use a label of 80 characters or less.',422)
    if days not in [7,14,30,60,90]:fail('INVALID_EXPIRY','Choose an expiry between 7 and 90 days.',422)
    if not isinstance(options,dict) or set(options)-{'include_name','include_evidence_details','include_verification_reason'} or any(not isinstance(v,bool) for v in options.values()):fail('INVALID_OPTIONS','Choose valid sharing options.',422)
    settings={'include_name':False,'include_evidence_details':True,'include_verification_reason':True,**options}
    with LOCK,tx() as db:
        u=auth(db,request)
        if not u.verified:fail('EMAIL_VERIFICATION_REQUIRED','Verify your email before creating a report link.',403)
        rate('shares:'+u.id,10,86400)
        reports=list(db.scalars(select(Attempt).where(Attempt.user_id==u.id,Attempt.id.in_(ids))))
        if len(reports)!=len(ids) or any(not a.result or a.mode!='formal' or a.status!='completed' for a in reports):fail('INVALID_REPORTS','Choose only your completed formal reports.',404)
        token=secrets.token_urlsafe(32);share=ReportShare(token_hash=hashed(token),token_hint=token[:8],user_id=u.id,label=label or 'SkillTrial evidence',options=settings,expires=now()+days*86400)
        db.add(share);db.flush()
        for a in reports:db.add(ReportShareItem(share_id=share.id,attempt_id=a.id))
        audit(db,u,'share.created',share.id);base=os.environ.get('PUBLIC_APP_URL','http://127.0.0.1:5173').rstrip('/')
        return {'id':share.id,'url':base+'/r/'+token,'expires':share.expires,'token_hint':share.token_hint}

@app.delete('/api/v1/me/shares/{id}')
def share_revoke(id:str,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);share=owned(db,ReportShare,id,u)
        if not share.revoked:share.revoked=now();audit(db,u,'share.revoked',share.id)
        return {'ok':True,'revoked':share.revoked}

@app.get('/api/v1/public/shares/{token}')
def public_share(token:str,request:Request):
    if not re.fullmatch(r'[A-Za-z0-9_-]{24,128}',token):fail('SHARE_UNAVAILABLE','This report link is unavailable.',404)
    rate('public-share:'+request.client.host,50,3600)
    outcome=None;payload=None;sid=None
    with LOCK,tx() as db:
        share=db.scalar(select(ReportShare).where(ReportShare.token_hash==hashed(token)))
        if not share:outcome='not_found'
        else:
            sid=share.id
            if share.revoked:outcome='revoked'
            elif share.expires<=now():outcome='expired'
            else:
                owner=db.get(User,share.user_id)
                if not owner or owner.status not in ['active','pending_deletion']:outcome='not_found'
                else:
                    first_view=share.access_count==0;share.access_count+=1;share.last_accessed=now();outcome='ok';payload=share_public_view(db,share)
                    if first_view:celebrate(db,owner,'share-viewed:'+share.id,'Your report link was opened','A person viewed the evidence you chose to share. Their identity is not collected.',1)
        db.add(ShareAccess(share_id=sid,outcome=outcome or 'not_found'))
    if outcome!='ok':fail('SHARE_UNAVAILABLE','This report link is unavailable.',404)
    return payload

@app.get('/api/v1/practice')
def practice(request:Request):
    with tx() as db:
        auth(db,request);return [challenge_view(c) for c in db.scalars(select(Challenge).where(Challenge.pool=='practice',Challenge.status=='published'))]

def path_view(p):
    items=[];blocked=False
    for item in p.items:
        clean={k:v for k,v in item.items() if k!='answer'}
        if 'checks' in clean:clean['checks']=[{k:v for k,v in check.items() if k!='answer'} for check in clean['checks']]
        clean['locked']=blocked;items.append(clean);blocked=blocked or item.get('status')!='completed'
    return {'id':p.id,'skill':p.skill,'attempt_id':p.attempt_id,'created':p.created,'archived':p.archived,'items':items}

@app.get('/api/v1/learning/paths')
def paths(request:Request):
    with tx() as db:
        u=auth(db,request);include=request.query_params.get('archived')=='true';return [path_view(p) for p in db.scalars(select(Path).where(Path.user_id==u.id,Path.archived==include).order_by(Path.created.desc()))]

@app.patch('/api/v1/learning/paths/{id}')
def archive_path(id:str,body:dict,request:Request):
    if set(body)!={'archived'} or not isinstance(body['archived'],bool):fail('INVALID_FIELD','Choose whether to archive this path.',422)
    with LOCK,tx() as db:
        u=auth(db,request);p=owned(db,Path,id,u);p.archived=body['archived'];return path_view(p)

@app.post('/api/v1/learning/paths/{id}/items/{item_id}/{action}')
def learning_action(id:str,item_id:str,action:str,body:dict,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);p=owned(db,Path,id,u);items=copy.deepcopy(p.items);i=next((x for x in items if x['id']==item_id),None)
        if not i or i['type']!='resource':fail('NOT_FOUND','Learning resource not found.',404)
        position=next(n for n,item in enumerate(items) if item['id']==item_id)
        if p.archived:fail('PATH_ARCHIVED','Restore this learning path before continuing.',409)
        if any(item.get('status')!='completed' for item in items[:position]):fail('WAYPOINT_LOCKED','Complete the earlier learning waypoint first.',409)
        if action=='open':i['opened']=i.get('opened') or now()
        elif action=='complete':
            if not i.get('opened') or now()-i['opened']<30:fail('RESOURCE_TOO_QUICK','Spend at least 30 seconds with the guide before completing the check.',422)
            checks=i.get('checks')
            if checks is None:checks=[{'answer':i['answer']}] if i.get('question') else []
            answers=body.get('answers',[body.get('answer')])
            if checks and (not isinstance(answers,list) or len(answers)!=len(checks) or any(not isinstance(answer,int) or isinstance(answer,bool) or answer!=check['answer'] for answer,check in zip(answers,checks))):fail('CHECK_NOT_PASSED','Review the resource and answer every quick-check question correctly.',422)
            i['status']='completed';award(db,u,'resource:'+p.skill+':'+i['competency'],15,'Learning waypoint completed',p.id);activity(db,u,'resource:'+id+':'+item_id,'learning')
            if all(item.get('status')=='completed' for item in items):
                celebrate(db,u,'path-complete:'+p.id,'Learning path completed',f'You completed every waypoint for {skill(p.skill)["name"]}.',2)
        else:fail('NOT_FOUND','Action not found.',404)
        p.items=items;return path_view(p)

@app.get('/api/v1/me/quests')
def quest_list(request:Request):
    with LOCK,tx() as db:return quests(db,auth(db,request))

@app.post('/api/v1/me/quests/{id}/claim')
def quest_claim(id:str,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);q=owned(db,Quest,id,u)
        current=next((x for x in quests(db,u) if x['id']==id),None)
        if not current or current['progress']<q.target:fail('QUEST_NOT_COMPLETE','Complete the quest before claiming.',409)
        if q.claimed:return {'ok':True,'shield_earned':False}
        shield_earned=q.kind=='weekly' and not u.profile.get('streak_shields',0)
        q.claimed=True;award(db,u,'quest:'+q.key,q.points,q.title)
        if shield_earned:u.profile={**u.profile,'streak_shields':1}
        celebrate(db,u,'quest:'+q.key,'Quest completed',q.title+' · +'+str(q.points)+' XP',1)
        if shield_earned:celebrate(db,u,'shield:'+q.key,'Streak shield earned','Your next weekly quest protects one missed day.',2)
        return {'ok':True,'shield_earned':shield_earned}

@app.get('/api/v1/me/celebrations')
def celebration_list(request:Request):
    with tx() as db:
        u=auth(db,request);return [{'key':c.key,'title':c.title,'message':c.message,'tier':c.tier,'created':c.created} for c in db.scalars(select(Celebration).where(Celebration.user_id==u.id,Celebration.seen==False).order_by(Celebration.created.desc()).limit(10))]

@app.post('/api/v1/me/celebrations/{id}/seen')
def celebration_seen(id:str,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);c=owned(db,Celebration,id,u);c.seen=True
        n=db.get(InboxNotification,id)
        if n and n.user_id==u.id:n.read=True
        return {'ok':True}

@app.get('/api/v1/me/notifications')
def notification_list(request:Request):
    with tx() as db:
        u=auth(db,request)
        # Backfill milestone inbox entries created before the inbox was introduced.
        celebrations=list(db.scalars(select(Celebration).where(Celebration.user_id==u.id).order_by(Celebration.created.desc()).limit(40)))
        for c in celebrations:
            if not db.get(InboxNotification,c.key):db.add(InboxNotification(key=c.key,user_id=u.id,kind='celebration',title=c.title,message=c.message,target='/app/achievements',read=c.seen,created=c.created))
        db.flush()
        rows=list(db.scalars(select(InboxNotification).where(InboxNotification.user_id==u.id).order_by(InboxNotification.created.desc()).limit(40)))
        unread=db.scalar(select(func.count()).select_from(InboxNotification).where(InboxNotification.user_id==u.id,InboxNotification.read==False)) or 0
        return {'unread':unread,'items':[{'key':n.key,'kind':n.kind,'title':n.title,'message':n.message,'target':n.target,'read':n.read,'created':n.created} for n in rows]}

@app.post('/api/v1/me/notifications/read-all')
def notification_read_all(request:Request):
    with LOCK,tx() as db:
        u=auth(db,request)
        db.execute(update(InboxNotification).where(InboxNotification.user_id==u.id,InboxNotification.read==False).values(read=True))
        db.execute(update(Celebration).where(Celebration.user_id==u.id,Celebration.seen==False).values(seen=True))
        return {'ok':True}

@app.post('/api/v1/me/notifications/{id}/read')
def notification_read(id:str,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);n=owned(db,InboxNotification,id,u);n.read=True
        c=db.get(Celebration,id)
        if c and c.user_id==u.id:c.seen=True
        return {'ok':True}

@app.get('/api/v1/me/badges')
def badge_list(request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);return badges(db,u)

@app.get('/api/v1/me/cosmetics')
def cosmetic_list(request:Request):
    with tx() as db:return cosmetics(db,auth(db,request))

@app.patch('/api/v1/me/cosmetics')
def cosmetic_equip(body:dict,request:Request):
    allowed={'frame','banner','title','editor_theme'}
    if not body or set(body)-allowed:fail('INVALID_FIELD','Choose an available cosmetic slot.',422)
    with LOCK,tx() as db:
        u=auth(db,request);inventory=cosmetics(db,u);equipped=dict(inventory['equipped'])
        for kind,value in body.items():
            unlocked={x['id'] for x in inventory['unlocked'][kind] if x['unlocked']}
            if value is not None and value not in unlocked:fail('COSMETIC_LOCKED','Earn this cosmetic before equipping it.',409)
            equipped[kind]=value or next(iter(unlocked))
        u.profile={**u.profile,'cosmetics':equipped};audit(db,u,'cosmetics.equipped',','.join(body));return cosmetics(db,u)

@app.get('/api/v1/me/league')
def league(request:Request):
    with tx() as db:return league_view(db,auth(db,request))

@app.patch('/api/v1/me/league')
def league_membership(body:dict,request:Request):
    if set(body)-{'joined','alias'} or not isinstance(body.get('joined'),bool):fail('INVALID_FIELD','Choose whether to join the practice league.',422)
    alias=body.get('alias')
    if alias is not None:
        alias=str(alias).strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,24}',alias) or set(alias.split('_'))&LEAGUE_BLOCKED:fail('INVALID_ALIAS','Use a 3–24 character alias without personal details or offensive terms.',422)
    with LOCK,tx() as db:
        u=auth(db,request);member=db.get(LeagueMember,u.id)
        if not body['joined']:
            if member:db.delete(member);audit(db,u,'league.left',member.alias)
            db.flush()
            return league_view(db,u)
        selected=alias or (member.alias if member else None)
        if selected:
            clash=db.scalar(select(LeagueMember).where(LeagueMember.alias==selected,LeagueMember.user_id!=u.id))
            if clash:fail('ALIAS_TAKEN','That alias is already in use. Choose another.',409)
        else:
            for _ in range(100):
                selected=league_alias()
                if not db.scalar(select(LeagueMember).where(LeagueMember.alias==selected)):break
            else:fail('ALIAS_UNAVAILABLE','A private alias could not be generated. Try again.',503)
        if member:member.alias=selected
        else:db.add(LeagueMember(user_id=u.id,alias=selected))
        audit(db,u,'league.joined' if not member else 'league.alias_changed',selected);db.flush();return league_view(db,u)

@app.get('/api/v1/me/recap')
def recap(request:Request):
    with tx() as db:return weekly_recap(db,auth(db,request))

@app.get('/api/v1/dashboard')
def dashboard(request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);attempts=list(db.scalars(select(Attempt).where(Attempt.user_id==u.id).order_by(Attempt.created.desc())));latest={}
        for a in attempts:
            if a.result and a.mode=='formal' and a.skill not in latest:latest[a.skill]=attempt_summary(a)
        cs=[{**claim_view(c),'verification':latest.get(c.skill)} for c in db.scalars(select(Claim).where(Claim.user_id==u.id,Claim.status!='removed'))]
        ledger=list(db.scalars(select(XP).where(XP.user_id==u.id).order_by(XP.created.desc()).limit(12)))
        role_skills={'Backend Java Developer':['java','spring-boot'],'Data Analyst':['sql','python'],'Python Developer':['python'],'Full-stack Developer':['javascript','python','sql']}
        priorities=[]
        for role in u.profile.get('roles',[]):priorities.extend(role_skills.get(role,[]))
        goal=re.sub(r'[^a-z0-9+#]+',' ',str(u.profile.get('goal','')).lower())
        for word,slug in [('sql','sql'),('python','python'),('java','java'),('javascript','javascript')]:
            if word in goal.split():priorities.insert(0,slug)
        priorities=list(dict.fromkeys(priorities))
        goal_progress=[]
        if u.profile.get('roles'):
            for role in u.profile.get('roles',[]):
                targets=role_skills.get(role,[])
                if targets:goal_progress.append({'label':role,'skills':[{'skill':slug,'name':skill(slug)['name'],'claim':next((c['status'] for c in cs if c['skill']==slug),'not_added'),'assessable':bool(assessment_levels(db,slug)),'verification':latest.get(slug,{}).get('result',{}).get('status','not_assessed')} for slug in targets]})
        elif priorities:goal_progress.append({'label':'Skills in your career goal','skills':[{'skill':slug,'name':skill(slug)['name'],'claim':next((c['status'] for c in cs if c['skill']==slug),'not_added'),'assessable':bool(assessment_levels(db,slug)),'verification':latest.get(slug,{}).get('result',{}).get('status','not_assessed')} for slug in priorities]})
        focus=next((c for slug in priorities for c in cs if c['skill']==slug and c['status']!='removed' and (not latest.get(slug) or latest[slug]['result']['status']!='verified')),None)
        focus_copy='the roles you selected' if u.profile.get('roles') else 'the goal you described'
        recommendation={'title':'Build evidence for your career direction','text':f"{focus['name']} is connected to {focus_copy}." if focus and priorities else 'Add a skill connected to your career direction.' if priorities else 'Choose the skills that matter for your next role.', 'to':'/app/trials' if focus and focus['status']=='confirmed' else '/app/skills' if focus or priorities else '/app/onboarding','skill':focus['skill'] if focus else None,'reason':'role_priority' if priorities else 'set_role'}
        resumes=list(db.scalars(select(Resume).where(Resume.user_id==u.id)))
        completed_formal=any(a.mode=='formal' and a.result for a in attempts)
        completed_practice=any(a.mode=='practice' and a.status=='completed' for a in attempts)
        missions=[('direction','Choose your career direction',bool(u.profile.get('roles') or u.profile.get('goal')),'/app/onboarding'),('resume','Add a resume',bool(resumes),'/app/resumes'),('review','Review a skill claim',any(c['status']!='pending_review' for c in cs),'/app/skills'),('confirm','Confirm a skill',any(c['status']=='confirmed' for c in cs),'/app/skills'),('trial','Complete a formal Trial',completed_formal,'/app/trials'),('report','Download your evidence report',db.scalar(select(Audit.id).where(Audit.actor==u.id,Audit.action=='report.downloaded').limit(1)) is not None,'/app/reports'),('practice','Complete a practice run',completed_practice,'/app/practice')]
        missions=[{'id':i,'title':t,'completed':done,'to':to} for i,t,done,to in missions]
        unseen=[{'key':c.key,'title':c.title,'message':c.message,'tier':c.tier,'created':c.created} for c in db.scalars(select(Celebration).where(Celebration.user_id==u.id,Celebration.seen==False).order_by(Celebration.created.desc()).limit(5))]
        return {'user':user_view(u),'recommendation':recommendation,'goal_progress':goal_progress,'missions':missions,'celebrations':unseen,'progress':progress(db,u),'orbits':orbit_map(db,u),'recap':weekly_recap(db,u),'skills':cs,'attempts':[attempt_summary(a) for a in attempts[:12]],'latest':list(latest.values()),'counts':{'verified':sum(a['result']['status']=='verified' for a in latest.values()),'assessments':sum(a.mode=='formal' and a.status=='completed' for a in attempts),'confirmed':sum(c['status']=='confirmed' for c in cs)},'quests':quests(db,u),'badges':badges(db,u),'xp_history':[{'points':x.points,'label':x.label,'created':x.created} for x in ledger],'learning': [path_view(p) for p in db.scalars(select(Path).where(Path.user_id==u.id,Path.archived==False).order_by(Path.created.desc()).limit(3))]}

@app.post('/api/v1/me/change-password')
def change_password(body:dict,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request)
        try:HASHER.verify(u.password,body.get('current',''))
        except Exception:fail('PASSWORD_INCORRECT','Your current password is incorrect.',422)
        password_ok(body.get('password',''),u.email);u.password=HASHER.hash(body['password']);db.execute(delete(AuthSession).where(AuthSession.user_id==u.id,AuthSession.token!=hashed(request.cookies['st_session'])));audit(db,u,'password.changed');return {'ok':True}

@app.get('/api/v1/me/export')
def export(request:Request):
    with tx() as db:
        u=auth(db,request)
        if not u.verified:fail('EMAIL_VERIFICATION_REQUIRED','Verify your email before exporting data.',403)
        rate('export:'+u.id,2,86400);out=io.BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('account.json',json.dumps(user_view(u)));z.writestr('claims.json',json.dumps([claim_view(c) for c in db.scalars(select(Claim).where(Claim.user_id==u.id))]))
            for a in db.scalars(select(Attempt).where(Attempt.user_id==u.id)):
                z.writestr('attempts/'+a.id+'.json',json.dumps({'attempt':attempt_summary(a),'snapshot':a.result,'submissions':[{'id':i.id,'submission':i.submission,'draft':i.draft} for i in db.scalars(select(Item).where(Item.attempt_id==a.id))]}))
            for r in db.scalars(select(Resume).where(Resume.user_id==u.id)):
                f=VAR/'resumes'/(r.id+'.bin')
                if f.exists():z.writestr('resumes/'+r.id+FilePath(r.filename).suffix,CRYPT.decrypt(f.read_bytes()))
            z.writestr('xp.json',json.dumps([{'points':x.points,'label':x.label,'date':x.created} for x in db.scalars(select(XP).where(XP.user_id==u.id))]))
            z.writestr('badges.json',json.dumps([{'badge':x.badge_slug,'tier':x.tier,'rule_version':x.rule_version,'rule':x.snapshot,'source':x.source,'earned_at':x.created} for x in db.scalars(select(BadgeAward).where(BadgeAward.user_id==u.id))]))
            z.writestr('activities.json',json.dumps([{'kind':x.kind,'facts':x.facts,'date':x.created} for x in db.scalars(select(Activity).where(Activity.user_id==u.id))]))
            z.writestr('notifications.json',json.dumps([{'kind':x.kind,'title':x.title,'message':x.message,'target':x.target,'read':x.read,'date':x.created} for x in db.scalars(select(InboxNotification).where(InboxNotification.user_id==u.id))]))
            z.writestr('celebrations.json',json.dumps([{'title':x.title,'message':x.message,'tier':x.tier,'seen':x.seen,'date':x.created} for x in db.scalars(select(Celebration).where(Celebration.user_id==u.id))]))
            z.writestr('learning_paths.json',json.dumps([path_view(x) for x in db.scalars(select(Path).where(Path.user_id==u.id))]))
            z.writestr('quests.json',json.dumps([{'title':x.title,'kind':x.kind,'target':x.target,'points':x.points,'start':x.start,'end':x.end,'claimed':x.claimed} for x in db.scalars(select(Quest).where(Quest.user_id==u.id))]))
            z.writestr('report_shares.json',json.dumps([{'label':x.label,'options':x.options,'expires':x.expires,'revoked':x.revoked,'created':x.created,'access_count':x.access_count,'last_accessed':x.last_accessed,'reports':[i.attempt_id for i in db.scalars(select(ReportShareItem).where(ReportShareItem.share_id==x.id))]} for x in db.scalars(select(ReportShare).where(ReportShare.user_id==u.id))]))
            member=db.get(LeagueMember,u.id)
            if member:z.writestr('league.json',json.dumps({'alias':member.alias,'joined':member.joined}))
        return Response(out.getvalue(),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="SkillTrial_data.zip"'})

@app.post('/api/v1/me/delete-account')
def delete_account(body:dict,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request)
        try:HASHER.verify(u.password,body.get('password',''))
        except Exception:fail('PASSWORD_INCORRECT','Your password is incorrect.',422)
        u.status='pending_deletion';u.delete_at=now()+7*86400
        for share in db.scalars(select(ReportShare).where(ReportShare.user_id==u.id,ReportShare.revoked.is_(None))):share.revoked=now()
        for notice in db.scalars(select(Notice).where(Notice.user_id==u.id,Notice.status=='queued',Notice.kind!='deletion_scheduled')):notice.status='cancelled'
        db.add(Notice(key=f'{u.id}:deletion_scheduled:{int(now())}',user_id=u.id,kind='deletion_scheduled',payload={'delete_at':u.delete_at}))
        audit(db,u,'account.deletion_requested');return {'scheduled_for':u.delete_at}

@app.post('/api/v1/me/cancel-deletion')
def cancel_delete(request:Request):
    with LOCK,tx() as db:
        u=auth(db,request);u.status='active';u.delete_at=None
        for notice in db.scalars(select(Notice).where(Notice.user_id==u.id,Notice.status=='queued',Notice.kind=='deletion_scheduled')):notice.status='cancelled'
        return user_view(u)

@app.get('/api/v1/admin/challenges')
def admin_challenges(request:Request):
    with tx() as db:
        auth(db,request,'content.read');return [{**challenge_view(c),'status':c.status,'version':c.version,'author':c.author,'reviewer':c.reviewer,'validation':c.validation,'content':c.content} for c in db.scalars(select(Challenge).order_by(Challenge.skill,Challenge.slug))]

@app.post('/api/v1/admin/challenges')
def admin_create(body:dict,request:Request):
    with LOCK,tx() as db:
        u=auth(db,request,'content.manage');content=body.get('content',{});report=validate(content)
        if not skill(content.get('skill')):fail('INVALID_SKILL','Choose a catalog skill.',422)
        slug=str(content.get('slug',''))
        if not re.fullmatch(r'[a-z0-9-]{3,100}',slug):fail('INVALID_SLUG','Use a unique lowercase slug.',422)
        previous=list(db.scalars(select(Challenge).where(Challenge.slug==slug)))
        c=Challenge(slug=slug,skill=content['skill'],type=content.get('type','coding'),pool=body.get('pool','practice'),family=content.get('family',slug),level=content.get('level','intermediate'),version=max((x.version for x in previous),default=0)+1,content=content,author=u.id,validation=report)
        db.add(c);db.flush();audit(db,u,'challenge.created',c.id);return {'id':c.id,'validation':report}

@app.post('/api/v1/admin/ai/challenge-proposals')
def admin_ai_challenge_proposal(body:dict,request:Request):
    if set(body)-{'skill','type','brief'}:fail('INVALID_FIELD','Choose a skill, challenge type, and authoring brief.',422)
    slug=body.get('skill');kind=body.get('type');brief=body.get('brief')
    if not isinstance(brief,str) or not 20<=len(brief.strip())<=1500:fail('INVALID_BRIEF','Describe the learning objective in 20 to 1,500 characters.',422)
    if not isinstance(slug,str) or not isinstance(kind,str) or kind not in PROPOSAL_TYPES.get(slug,[]):fail('INVALID_CHALLENGE','Choose a supported challenge type for this skill.',422)
    with tx() as db:
        u=auth(db,request,'content.manage')
        if not LLM_READY or not setting_value(db,'llm_enabled',False):fail('AI_DISABLED','Optional AI authoring is not configured and enabled.',409)
        rate('ai-proposal:'+u.id,10,86400);author=u.id
    try:content=propose_challenge(slug,kind,brief.strip())
    except LLMUnavailable:fail('AI_UNAVAILABLE','The proposal service is unavailable. No content was saved.',503)
    except ValueError as error:fail('AI_PROPOSAL_INVALID',str(error),502)
    if not isinstance(content,dict) or len(json.dumps(content,ensure_ascii=False).encode())>250000:fail('AI_PROPOSAL_INVALID','The proposal did not fit the supported content format.',502)
    if content.get('skill')!=slug or content.get('type')!=kind or not re.fullmatch(r'[a-z0-9-]{3,100}',str(content.get('slug',''))):fail('AI_PROPOSAL_INVALID','The proposal must use the requested skill and type and include a valid slug.',502)
    try:report=validate(content)
    except (KeyError,TypeError,ValueError):fail('AI_PROPOSAL_INVALID','The proposal did not match the challenge schema. No content was saved.',502)
    if not report.get('ok'):fail('AI_PROPOSAL_INVALID','The proposal did not pass the content checks. No content was saved.',422,checks=report.get('checks',[]))
    if not valid_proposal_shape(content):fail('AI_PROPOSAL_INVALID','The proposal is missing required executable or scenario fields. No content was saved.',422)
    with LOCK,tx() as db:
        admin=db.get(User,author)
        if admin:audit(db,admin,'ai.challenge_proposed',content['slug'])
    return {'content':content,'validation':report,'pool':'practice','status':'proposal_only'}

@app.get('/api/v1/admin/ai/status')
def admin_ai_status(request:Request):
    with tx() as db:
        auth(db,request,'content.manage')
        return {'configured':LLM_READY,'enabled':bool(LLM_READY and setting_value(db,'llm_enabled',False)),'model':LLM_MODEL if LLM_READY else None,'types_by_skill':PROPOSAL_TYPES}

def valid_proposal_shape(content):
    if content.get('level') not in LEVELS or not isinstance(content.get('family'),str) or not 3<=len(content['family'])<=100:return False
    if not isinstance(content.get('minutes'),int) or isinstance(content.get('minutes'),bool) or not 5<=content['minutes']<=60:return False
    hints=content.get('hints')
    if not isinstance(hints,list) or not hints or any(not isinstance(hint,str) or not 3<=len(hint.strip())<=500 for hint in hints):return False
    if not isinstance(content.get('title'),str) or not 5<=len(content['title'].strip())<=120:return False
    if not isinstance(content.get('statement'),str) or len(content['statement'].strip())<40:return False
    if not isinstance(content.get('competencies'),list) or not content['competencies']:return False
    if content.get('type') in ['coding','debugging','sql']:
        tests=content.get('tests');reference=content.get('reference')
        if not isinstance(reference,str) or not reference.strip() or not isinstance(tests,list) or len(tests)<4:return False
        if content.get('type')=='sql' and (content.get('language')!='sql' or content.get('skill')!='sql'):return False
        if content.get('type')!='sql' and (content.get('language') not in ['python','javascript','java'] or content.get('skill')!=content.get('language')):return False
        for item in tests:
            if not isinstance(item,dict) or 'expected' not in item or not isinstance(item.get('label'),str) or item.get('visibility') not in ['sample','hidden']:return False
            if content.get('type')=='sql' and not isinstance(item.get('dataset'),str):return False
            if content.get('type')!='sql' and 'input' not in item:return False
    elif content.get('type')=='scenario':
        questions=content.get('questions');answers=content.get('answers')
        if not isinstance(questions,list) or len(questions)<3 or not isinstance(answers,dict):return False
        for question in questions:
            if not isinstance(question,dict) or not isinstance(question.get('id'),str) or not isinstance(question.get('prompt'),str):return False
            options=question.get('options')
            if not isinstance(options,list) or not 2<=len(options)<=5:return False
            option_ids={row.get('id') for row in options if isinstance(row,dict) and isinstance(row.get('id'),str) and isinstance(row.get('text'),str)}
            if len(option_ids)!=len(options) or answers.get(question['id']) not in option_ids:return False
    elif content.get('type')=='trust':
        if not isinstance(content.get('suggestions'),list) or len(content['suggestions'])<3 or not isinstance(content.get('tests'),list) or len(content['tests'])<4:return False
        if not isinstance(content.get('reference'),str) or not content['reference'].strip():return False
    return True

@app.post('/api/v1/admin/challenges/{id}/{action}')
def admin_transition(id:str,action:str,request:Request):
    with LOCK,tx() as db:
        permission={'validate':'content.validate','review':'content.review','publish':'content.publish','unpublish':'content.publish'}.get(action,'content.manage')
        u=auth(db,request,permission);c=db.get(Challenge,id)
        if not c:fail('NOT_FOUND','Challenge not found.',404)
        if action=='validate':
            try:c.validation=executable_validation(c.content)
            except RunnerUnavailable as e:fail('RUNNER_UNAVAILABLE',str(e),503)
            return c.validation
        if action=='review':
            if c.status!='draft' or not c.validation.get('ok') or not c.validation.get('executed'):fail('VALIDATION_REQUIRED','An executable-validated draft is required.',409)
            if c.author==u.id:fail('REVIEWER_MUST_DIFFER','A different administrator must review this challenge.',409)
            c.reviewer=u.id;c.status='validated'
        elif action=='publish':
            if c.status!='validated' or not c.reviewer:fail('REVIEW_REQUIRED','An independent review is required.',409)
            c.status='published'
        elif action=='unpublish':c.status='unpublished'
        else:fail('NOT_FOUND','Action not found.',404)
        audit(db,u,'challenge.'+action,c.id);return {'status':c.status}

app.include_router(catalog_admin_router)

@app.get('/api/v1/admin/stats')
def admin_stats(request:Request):
    with tx() as db:
        auth(db,request,'stats.read');coverage={}
        for c in db.scalars(select(Challenge).where(Challenge.status=='published')):
            row=coverage.setdefault(c.skill,{'formal':0,'practice':0,'types':{},'competencies':set()})
            row['formal' if c.pool=='assessment' else 'practice']+=1;row['types'][c.type]=row['types'].get(c.type,0)+1;row['competencies'].update(c.content.get('competencies',[]))
        coverage=[{'skill':s,'formal':v['formal'],'practice':v['practice'],'types':v['types'],'competencies':sorted(v['competencies'])} for s,v in sorted(coverage.items())]
        attempts=list(db.scalars(select(Attempt)));users=list(db.scalars(select(User)))
        return {'users':len(users),'assessments':len(attempts),'challenges':db.scalar(select(func.count()).select_from(Challenge)),'user_statuses':{key:sum(u.status==key for u in users) for key in sorted({u.status for u in users})},'attempt_statuses':{key:sum(a.status==key for a in attempts) for key in sorted({a.status for a in attempts})},'assessments_by_skill':{key:sum(a.skill==key for a in attempts) for key in sorted({a.skill for a in attempts})},'coverage':coverage,'audit':[{'action':a.action,'target':a.target,'date':a.created} for a in db.scalars(select(Audit).order_by(Audit.created.desc()).limit(30))]}

ADMIN_PERMISSIONS={'content.read','content.manage','content.validate','content.review','content.publish','stats.read','users.manage','settings.manage'}
@app.get('/api/v1/admin/users')
def admin_users(request:Request,q:str=''):
    if len(q)>80:fail('INVALID_SEARCH','Search is limited to 80 characters.',422)
    with tx() as db:
        auth(db,request,'users.manage');stmt=select(User).order_by(User.created.desc()).limit(100)
        users=list(db.scalars(stmt))
        if q:needle=q.casefold();users=[u for u in users if needle in u.email.casefold() or needle in u.name.casefold()]
        return [{'id':u.id,'email':u.email,'name':u.name,'role':u.role,'status':u.status,'verified':u.verified,'created':u.created,'permissions':u.profile.get('admin_permissions',['*']) if u.role=='admin' else []} for u in users]

@app.patch('/api/v1/admin/users/{id}')
def admin_user_update(id:str,body:dict,request:Request):
    if set(body)-{'status','permissions'} or not body:fail('INVALID_FIELD','Choose a user status or administrator permissions.',422)
    if 'status' in body and body['status'] not in ['active','suspended']:fail('INVALID_STATUS','Choose active or suspended.',422)
    if 'permissions' in body and (not isinstance(body['permissions'],list) or any(not isinstance(p,str) for p in body['permissions']) or len(set(body['permissions']))!=len(body['permissions']) or not set(body['permissions'])<=ADMIN_PERMISSIONS):fail('INVALID_PERMISSIONS','Choose from the available admin permissions.',422)
    with LOCK,tx() as db:
        actor=auth(db,request,'users.manage');target=db.get(User,id)
        if not target:fail('NOT_FOUND','User not found.',404)
        if target.id==actor.id:fail('SELF_ADMIN_CHANGE','You cannot change your own account from this screen.',409)
        if 'permissions' in body and target.role!='admin':fail('INVALID_ROLE','Only administrator permissions can be edited here.',409)
        needs_admin=target.role=='admin' and (body.get('status')=='suspended' or ('permissions' in body and '*' not in body['permissions']))
        if needs_admin:
            active_admins=[u for u in db.scalars(select(User).where(User.role=='admin',User.status=='active')) if u.id!=target.id and '*' in u.profile.get('admin_permissions',['*'])]
            if not active_admins:fail('LAST_ADMIN_REQUIRED','Keep at least one active full administrator.',409)
        if 'permissions' in body:target.profile={**target.profile,'admin_permissions':body['permissions']}
        if 'status' in body:
            target.status=body['status']
            target.delete_at=None
            if target.status!='active':db.execute(delete(AuthSession).where(AuthSession.user_id==target.id))
            if target.status=='active':
                for notice in db.scalars(select(Notice).where(Notice.user_id==target.id,Notice.status=='queued',Notice.kind=='deletion_scheduled')):notice.status='cancelled'
        audit(db,actor,'admin.user_updated',target.id);return {'id':target.id,'status':target.status,'permissions':target.profile.get('admin_permissions',['*']) if target.role=='admin' else []}

@app.get('/api/v1/admin/settings')
def admin_settings(request:Request):
    with tx() as db:
        auth(db,request,'settings.manage');return admin_settings_snapshot(db)

@app.put('/api/v1/admin/settings')
def admin_settings_update(body:dict,request:Request):
    if set(body)-{'registration_open','reassess_cooldown_hours','llm_enabled'} or not body:fail('INVALID_FIELD','Choose a supported platform setting.',422)
    if 'registration_open' in body and not isinstance(body['registration_open'],bool):fail('INVALID_SETTING','Registration must be on or off.',422)
    if 'reassess_cooldown_hours' in body and (not isinstance(body['reassess_cooldown_hours'],(float,int)) or isinstance(body['reassess_cooldown_hours'],bool) or not 0<=body['reassess_cooldown_hours']<=720):fail('INVALID_SETTING','Cooldown must be between zero and 720 hours.',422)
    if 'llm_enabled' in body and not isinstance(body['llm_enabled'],bool):fail('INVALID_SETTING','Optional AI must be enabled or disabled.',422)
    if body.get('llm_enabled') is True and not LLM_READY:fail('AI_NOT_CONFIGURED','Configure the AI provider key and model before enabling optional AI.',409)
    with LOCK,tx() as db:
        u=auth(db,request,'settings.manage')
        for key,value in body.items():
            row=db.get(AppSetting,key)
            if row:row.value={'value':value};row.updated_by=u.id;row.updated=now()
            else:db.add(AppSetting(key=key,value={'value':value},updated_by=u.id))
        audit(db,u,'admin.settings_updated',','.join(body));return admin_settings_snapshot(db)

def admin_settings_snapshot(db):return {'registration_open':setting_value(db,'registration_open',True),'reassess_cooldown_hours':setting_value(db,'reassess_cooldown_hours',COOLDOWN_H),'llm_configured':LLM_READY,'llm_enabled':bool(LLM_READY and setting_value(db,'llm_enabled',False)),'llm_model':LLM_MODEL if LLM_READY else None}

# The built SPA can be served by the API for a single-process local installation.
dist=ROOT/'frontend'/'dist'
if dist.exists():
    app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
    @app.get('/{path:path}')
    def frontend(path:str):
        if path.startswith('api/'):fail('NOT_FOUND','Endpoint not found.',404)
        return FileResponse(dist/'index.html')
