from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo
from sqlalchemy import select,func
from .db import now
from .models import XP,Activity,Quest,Celebration,OrbitProgress,Attempt,InboxNotification,BadgeDefinition,BadgeAward,Claim

RANKS=[(1,'Spark'),(3,'Ember'),(5,'Flare'),(8,'Comet'),(11,'Nova'),(15,'Pulsar'),(20,'Supernova')]
BADGE_METRICS={'confirmed_steps','passed_families','edge_case_tests','valid_counterexamples','verified_results','current_streak'}
BADGE_RULES={metric:{'metric':metric,'label':metric.replace('_',' ').title(),'params':{'thresholds':{'type':'integer_array','min_items':1,'max_items':3,'minimum':1,'maximum':100000}}} for metric in sorted(BADGE_METRICS)}
DEFAULT_BADGES=[
    {'slug':'first-light','name':'First steps','description':'Complete your profile and confirm your claims.','icon':'Sparkles','metric':'confirmed_steps','thresholds':[2,4,6]},
    {'slug':'problem-solver','name':'Problem Solver','description':'Pass challenges from different families.','icon':'Code2','metric':'passed_families','thresholds':[5,10,15]},
    {'slug':'edge-explorer','name':'Edge Case Explorer','description':'Pass edge-case tests.','icon':'ScanLine','metric':'edge_case_tests','thresholds':[12,24,36]},
    {'slug':'trust-analyst','name':'AI Trust Analyst','description':'Execute valid counterexamples.','icon':'ShieldCheck','metric':'valid_counterexamples','thresholds':[3,6,9]},
    {'slug':'first-verification','name':'Evidence in hand','description':'Earn a Verified formal assessment result.','icon':'Award','metric':'verified_results','thresholds':[1,2,3]},
    {'slug':'week-streak','name':'Steady orbit','description':'Maintain an activity streak.','icon':'Flame','metric':'current_streak','thresholds':[7,14,21]},
]

def seed_badges(db):
    for item in DEFAULT_BADGES:
        if not db.get(BadgeDefinition,item['slug']):db.add(BadgeDefinition(**item,author='system'))

def badge_snapshot(badge):
    return {'version':(badge.details or {}).get('version',1),'name':badge.name,'description':badge.description,'icon':badge.icon,'category':(badge.details or {}).get('category','behavior'),'metric':badge.metric,'thresholds':list(badge.thresholds)}

def celebrate(db,u,key,title,message,tier=1):
    key=f'{u.id}:{key}'
    if not db.get(Celebration,key):
        db.add(Celebration(key=key,user_id=u.id,title=title,message=message,tier=tier))
        if not db.get(InboxNotification,key):
            db.add(InboxNotification(key=key,user_id=u.id,kind='celebration',title=title,message=message,target='/app/achievements'))
        db.flush()

def notify(db,u,key,title,message,target='/app',kind='update'):
    key=f'{u.id}:{key}'
    if db.get(InboxNotification,key):return
    db.add(InboxNotification(key=key,user_id=u.id,kind=kind,title=title,message=message,target=target));db.flush()

def award(db,u,key,points,label,source=''):
    key=f'{u.id}:{key}'
    if not db.get(XP,key):
        before=db.scalar(select(func.coalesce(func.sum(XP.points),0)).where(XP.user_id==u.id))
        db.add(XP(key=key,user_id=u.id,points=points,label=label,source=source));db.flush();after=before+points
        old=1
        while before>=50*old*(old+1):old+=1
        new=1
        while after>=50*new*(new+1):new+=1
        for level in range(old+1,new+1):
            rank=[r for threshold,r in RANKS if level>=threshold][-1]
            celebrate(db,u,f'level:{level}',f'Level {level} reached',f'Your steady practice brought you to {rank}.',2)

def activity(db,u,key,kind,facts=None):
    key=f'{u.id}:{key}'
    if not db.get(Activity,key):
        facts=facts or {};db.add(Activity(key=key,user_id=u.id,kind=kind,facts=facts));db.flush()
        if kind=='practice' and facts.get('skill'):
            orbit_day=datetime.now(ZoneInfo(u.profile.get('timezone','UTC'))).date().isoformat();family=facts.get('family','practice');once_key=f'{u.id}:orbit:{facts["skill"]}:{family}:{orbit_day}'
            if not db.get(Activity,once_key):
                points=8+(4 if facts.get('ratio',0)>=.7 else 0);db.add(Activity(key=once_key,user_id=u.id,kind='orbit_award',facts={'skill':facts['skill'],'family':family,'points':points}));orbit_key=f'{u.id}:{facts["skill"]}';row=db.get(OrbitProgress,orbit_key);before=orbit_level(row.points if row else 0)['level']
                if row:row.points+=points;row.updated=now()
                else:db.add(OrbitProgress(key=orbit_key,user_id=u.id,skill=facts['skill'],points=points))
                db.flush();after=orbit_level(row.points if row else points)['level']
                if after>before:celebrate(db,u,f'orbit:{facts["skill"]}:{after}',f'{facts["skill"].replace("-"," ").title()} reached Orbit {after}','Practice is building familiarity. Assessment evidence still determines verification.',1)
        tz=ZoneInfo(u.profile.get('timezone','UTC'));today=datetime.now(tz).date()
        recent=list(db.scalars(select(Activity).where(Activity.user_id==u.id,Activity.key!=key)))
        last=max((datetime.fromtimestamp(a.created,tz).date() for a in recent),default=today)
        if (today-last).days==2 and u.profile.get('streak_shields',0)>0:
            shield_key=f'{u.id}:streak-shield:{today.isoformat()}'
            db.add(Activity(key=shield_key,user_id=u.id,kind='streak_shield',facts={'protected_day':(today-timedelta(days=1)).isoformat()},created=datetime.combine(today-timedelta(days=1),time(12),tzinfo=tz).timestamp()))
            u.profile={**u.profile,'streak_shields':u.profile.get('streak_shields',0)-1};db.flush()
            celebrate(db,u,'shield-used:'+today.isoformat(),'Your streak stayed bright','A streak shield protected one missed day.',2)
        evaluate_badges(db,u)

def progress(db,u):
    xp=db.scalar(select(func.coalesce(func.sum(XP.points),0)).where(XP.user_id==u.id));level=1
    while xp>=50*(level+1)*level:level+=1
    tz=ZoneInfo(u.profile.get('timezone','UTC'))
    days=sorted({datetime.fromtimestamp(a.created,tz).date() for a in db.scalars(select(Activity).where(Activity.user_id==u.id))},reverse=True)
    today=datetime.now(tz).date();streak=0
    if days and (today-days[0]).days<=1:
        current=days[0]
        for d in days:
            if d!=current:break
            streak+=1;current-=timedelta(days=1)
    return {'xp':xp,'level':level,'rank':[r for l,r in RANKS if level>=l][-1],'floor':50*level*(level-1),'ceiling':50*(level+1)*level,'streak':streak,'shields':u.profile.get('streak_shields',0),'today_done':bool(days and days[0]==today)}

def quests(db,u):
    tz=ZoneInfo(u.profile.get('timezone','UTC'));day=datetime.now(tz).replace(hour=0,minute=0,second=0,microsecond=0)
    week=day-timedelta(days=day.weekday())
    for kind,title,target,points,start,end in [('practice','Complete a Practice Run',1,20,day,day+timedelta(days=1)),('pass','Pass a Practice Run',1,30,day,day+timedelta(days=1)),('edge','Pass three edge-case tests in practice',3,25,day,day+timedelta(days=1)),('weekly','Complete five Practice Runs',5,100,week,week+timedelta(days=7))]:
        key=f'{u.id}:{kind}:{start.date()}'
        if not db.get(Quest,key):db.add(Quest(key=key,user_id=u.id,kind=kind,title=title,target=target,points=points,start=start.timestamp(),end=end.timestamp()))
    db.flush();out=[]
    for q in db.scalars(select(Quest).where(Quest.user_id==u.id,Quest.end>now())):
        events=list(db.scalars(select(Activity).where(Activity.user_id==u.id,Activity.kind=='practice',Activity.created>=q.start,Activity.created<q.end)))
        value=sum(e.facts.get('edge_passed',0) for e in events) if q.kind=='edge' else sum(e.facts.get('ratio',0)>=.7 for e in events) if q.kind=='pass' else len(events)
        out.append({'id':q.key,'title':q.title,'kind':q.kind,'target':q.target,'progress':min(value,q.target),'points':q.points,'claimed':q.claimed,'end':q.end})
    return out

def badge_values(db,u):
    events=list(db.scalars(select(Activity).where(Activity.user_id==u.id)))
    # Current claims preserve credit for accounts created before per-skill events.
    # Historical events preserve a completed step if a claim is later removed.
    confirmed={c for c in db.scalars(select(Claim.skill).where(Claim.user_id==u.id,Claim.status=='confirmed'))}
    confirmed.update(e.facts['skill'] for e in events if e.kind=='confirmed' and e.facts.get('skill'))
    legacy_confirmed=any(e.kind=='confirmed' for e in events)
    onboarded=bool(u.profile.get('onboarded') or any(e.kind=='onboard' for e in events))
    return {
        'confirmed_steps':int(onboarded)+max(len(confirmed),int(legacy_confirmed)),
        'passed_families':len({e.facts.get('family') for e in events if e.facts.get('family') and e.facts.get('ratio',0)>=.7}),
        'edge_case_tests':sum(int(e.facts.get('edge_passed',0) or 0) for e in events),
        'valid_counterexamples':sum(bool(e.facts.get('counterexample')) for e in events),
        'verified_results':sum(bool(e.facts.get('verified')) for e in events),
        'current_streak':progress(db,u)['streak'],
    }

def evaluate_badges(db,u,notify=True,definitions=None):
    values=badge_values(db,u)
    existing={a.key for a in db.scalars(select(BadgeAward).where(BadgeAward.user_id==u.id))}
    definitions=definitions if definitions is not None else list(db.scalars(select(BadgeDefinition).where(BadgeDefinition.enabled==True)))
    for badge in definitions:
        if not badge.enabled:continue
        for tier,threshold in enumerate(badge.thresholds or [],1):
            key=f'{u.id}:{badge.slug}:{tier}'
            if key in existing or values.get(badge.metric,0)<threshold:continue
            snapshot=badge_snapshot(badge)
            db.add(BadgeAward(key=key,user_id=u.id,badge_slug=badge.slug,tier=tier,rule_version=snapshot['version'],snapshot=snapshot,source={'metric':badge.metric,'value':values.get(badge.metric,0),'threshold':threshold}))
            existing.add(key)
            if notify:celebrate(db,u,f'badge:{badge.slug}:{tier}',f'{badge.name} · Tier {tier}','A practice achievement earned. It is separate from verified proficiency.',2)
    db.flush()

def badges(db,u):
    # Reconcile pre-existing activity once; awards remain after streak resets or rule edits.
    evaluate_badges(db,u,notify=False)
    values=badge_values(db,u)
    awards=list(db.scalars(select(BadgeAward).where(BadgeAward.user_id==u.id)))
    out=[]
    for badge in db.scalars(select(BadgeDefinition).order_by(BadgeDefinition.created,BadgeDefinition.slug)):
        owned=[a for a in awards if a.badge_slug==badge.slug]
        if not badge.enabled and not owned:continue
        thresholds=[int(x) for x in (badge.thresholds or []) if isinstance(x,int) and x>0]
        if not thresholds:continue
        value=values.get(badge.metric,0);tier=max((a.tier for a in owned),default=0)
        if tier>=len(thresholds):
            target=max(1,thresholds[-1]-(thresholds[-2] if len(thresholds)>1 else 0));within=target
        else:
            floor=thresholds[tier-1] if tier>0 else 0;target=max(1,thresholds[tier]-floor);within=min(target,max(0,value-floor))
        out.append({'id':badge.slug,'name':badge.name,'description':badge.description,'progress':within,'target':target,'earned':tier>0,'tier':tier,'max_tier':max(tier,len(thresholds)),'icon':badge.icon,'category':(badge.details or {}).get('category','behavior'),'version':(badge.details or {}).get('version',1),'metric':badge.metric,'thresholds':thresholds,'earned_at':max((a.created for a in owned),default=None),'archived':not badge.enabled,'awards':[{'tier':a.tier,'version':a.rule_version,'earned_at':a.created,'rule':a.snapshot} for a in owned]})
    return out

def orbit_level(points):
    level=1
    while level<10 and points>=12.5*(level+1)*level:level+=1
    floor=12.5*level*(level-1);ceiling=12.5*(level+1)*level
    return {'level':level,'points':points,'floor':floor,'ceiling':ceiling,'progress':1 if level==10 else max(0,min(1,(points-floor)/(ceiling-floor)))}

def orbit_map(db,u):
    rows=db.scalars(select(OrbitProgress).where(OrbitProgress.user_id==u.id))
    return {row.skill:orbit_level(row.points) for row in rows}

def cosmetics(db,u):
    p=progress(db,u);orbits=orbit_map(db,u);earned=badges(db,u);rank=p['level']
    frames=[{'id':'spark','name':'Spark ring','unlocked':True}]
    frames += [{'id':item,'name':name,'unlocked':rank>=threshold} for item,name,threshold in [('ember','Ember ring',3),('comet','Comet tail',8),('nova','Nova burst',11),('supernova','Supernova halo',20)]]
    banners=[{'id':'none','name':'No banner','unlocked':True}]
    banners += [{'id':'skill:'+slug,'name':label+' constellation','unlocked':orbits.get(slug,{}).get('level',1)>=5} for slug,label in [('java','Java'),('python','Python'),('sql','SQL'),('javascript','JavaScript')]]
    titles=[{'id':'none','name':'No title','unlocked':True}]
    titles += [{'id':'title:'+b['id'],'name':b['name'],'unlocked':b['tier']>0} for b in earned]
    themes=[{'id':'midnight','name':'Midnight','unlocked':rank>=1},{'id':'aurora','name':'Aurora','unlocked':rank>=5},{'id':'solar','name':'Solar','unlocked':rank>=11}]
    unlocked={kind:[x['id'] for x in values if x['unlocked']] for kind,values in [('frame',frames),('banner',banners),('title',titles),('editor_theme',themes)]}
    current=u.profile.get('cosmetics',{})
    equipped={kind:(current.get(kind) if current.get(kind) in options else options[0]) for kind,options in unlocked.items()}
    return {'unlocked':{'frame':frames,'banner':banners,'title':titles,'editor_theme':themes},'equipped':equipped,'orbits':orbits}

def weekly_recap(db,u,reference=None):
    tz=ZoneInfo(u.profile.get('timezone','UTC'));local=(reference or datetime.now(tz)).astimezone(tz)
    monday=local.date()-timedelta(days=local.weekday());start_day=monday-timedelta(days=7)
    start=datetime.combine(start_day,time.min,tzinfo=tz).timestamp();end=datetime.combine(monday,time.min,tzinfo=tz).timestamp()
    practices=db.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id==u.id,Attempt.mode=='practice',Attempt.status=='completed',Attempt.completed>=start,Attempt.completed<end)) or 0
    waypoints=db.scalar(select(func.count()).select_from(Activity).where(Activity.user_id==u.id,Activity.kind=='learning',Activity.created>=start,Activity.created<end)) or 0
    xp=db.scalar(select(func.coalesce(func.sum(XP.points),0)).where(XP.user_id==u.id,XP.created>=start,XP.created<end)) or 0
    verified=db.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id==u.id,Attempt.mode=='formal',Attempt.status=='completed',Attempt.completed>=start,Attempt.completed<end)) or 0
    dates=sorted({datetime.fromtimestamp(a.created,tz).date() for a in db.scalars(select(Activity).where(Activity.user_id==u.id,Activity.created<end))},reverse=True)
    week_end_day=monday-timedelta(days=1);streak=0;cursor=week_end_day
    date_set=set(dates)
    while cursor in date_set:streak+=1;cursor-=timedelta(days=1)
    if not any([practices,waypoints,xp,verified]):return None
    return {'week_start':start_day.isoformat(),'week_end':(monday-timedelta(days=1)).isoformat(),'practice_runs':practices,'waypoints':waypoints,'xp':xp,'streak_at_week_end':streak,'formal_trials':verified}
