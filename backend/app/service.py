import copy
import threading
from fastapi import HTTPException
from sqlalchemy import select,update
from .db import now,tx
from .models import Attempt,Item,Challenge,Job,User,Path,LearningResource,AppSetting
from .catalog import skill,digest,canonical_payload
from .config import LLM_READY
from .execution import RunnerUnavailable
from .evaluation import evaluate,visible_evaluation
from .verification import decide
from .game import award,activity,celebrate,notify
from .security import audit,rate
from .resources import published_resources,resource_details

LOCK=threading.RLock()

def enqueue(db,kind,target):
    if not db.scalar(select(Job).where(Job.target==target)):db.add(Job(kind=kind,target=target))

def substantive(c,p):
    if c['type']=='sql':return bool(p.get('query','').strip())
    if c['type']=='scenario':return bool(p.get('answers'))
    if c['type']=='trust':return bool(p.get('decisions'))
    return bool(p.get('code','').strip()) and p['code'].strip()!=c.get('starter','').strip()

def finalize(db,a,reason):
    if a.status!='in_progress':return
    for i in db.scalars(select(Item).where(Item.attempt_id==a.id)):
        if i.submission is not None:continue
        c=db.get(Challenge,i.challenge_id).content
        if substantive(c,i.draft):i.submission=canonical_payload(c,i.id,i.draft);i.status='submitted';enqueue(db,'evaluate',i.id)
        else:i.status='not_attempted'
    a.status='evaluating';a.reason=reason
    audit(db,None,'attempt.finalized',a.id)

def complete(db,a):
    items=list(db.scalars(select(Item).where(Item.attempt_id==a.id).order_by(Item.ordinal)))
    if a.status!='evaluating' or any(i.status not in ['evaluated','infra_error','not_attempted'] for i in items):return
    claimed=db.execute(update(Attempt).where(Attempt.id==a.id,Attempt.status=='evaluating').values(status='completing'))
    if claimed.rowcount!=1:return
    db.refresh(a)
    u=db.get(User,a.user_id)
    facts=[];snapitems=[]
    for i in items:
        ch=db.get(Challenge,i.challenge_id);ev=i.evaluation
        facts.append({'type':ch.type,'level':ch.level,'status':i.status,'evaluation':ev})
        snapitems.append({'id':i.id,'title':ch.content['title'],'type':ch.type,'difficulty':ch.level,'version':ch.version,'content_hash':digest(ch.content),'status':i.status,'evaluation':visible_evaluation(ev,a.mode=='practice')})
        if ev and ev['status']=='completed':
            ratio=ev['ratio'];passed=ratio>=.7
            if passed:award(db,u,'pass:'+ch.family,round((20 if ch.level=='beginner' else 35)*max(.25,1-.25*i.hints)),'Challenge passed',a.id)
            if ratio==1:award(db,u,'perfect:'+ch.family,10,'Perfect solution',a.id)
            if ev.get('counterexample_valid'):award(db,u,'ce:'+ch.family,15,'Valid counterexample',a.id)
            activity(db,u,'item:'+i.id,'practice' if a.mode=='practice' else 'formal_item',{'family':ch.family,'skill':a.skill,'ratio':ratio,'edge_passed':sum(t.get('passed',False) and 'edge_cases' in t.get('competencies',[]) for t in ev.get('tests',[])),'counterexample':ev.get('counterexample_valid',False)})
    a.completed=now();a.status='completed'
    result=decide(facts,a.policy,a.level) if a.mode=='formal' else {'status':'practice','overall':facts[0]['evaluation']['ratio'] if facts and facts[0]['evaluation'] and facts[0]['evaluation']['status']=='completed' else None,'competencies':[],'reasons':['Practice does not change formal verification.'],'infra_incident':any(i.status=='infra_error' for i in items)}
    ai_assisted=any(bool((i.evaluation or {}).get('ai_assisted')) for i in items)
    limitations=['Short, timed tasks assess only the competencies shown.','This assessment was not proctored and does not detect AI use or establish code authorship.','This report is not a professional certification or a guarantee of job performance.']
    if ai_assisted:limitations.append('An optional written-explanation criterion used AI feedback, capped at 20% of that scenario score; review the cited evidence with human judgment.')
    if a.skill=='sql':limitations.append('SQL tasks use the SQLite dialect.')
    if a.policy.get('content_preview'):limitations.append('Development preview: this content has a matching validation attestation but has not completed independent publication review.')
    a.result={'schema':1,'ref':'ST-'+a.id[:8].upper(),'candidate':u.name,'skill':a.skill,'skill_name':skill(a.skill)['name'],'level':a.level,'claim':a.claim_snapshot,'mode':a.mode,'date':a.completed,'policy':copy.deepcopy(a.policy),'result':result,'challenges':snapitems,'limitations':limitations}
    a.report_hash=digest(a.result)
    if a.mode=='formal':
        notify(db,u,'report:'+a.id,'Your evidence report is ready',f'Your {skill(a.skill)["name"]} Trial report is ready to review.','/app/assessments/'+a.id+'/result','report')
        if result['evaluable']:award(db,u,'assess:'+a.id,50,'Assessment completed',a.id)
        activity(db,u,'assessment:'+a.id,'formal',{'verified':result['status']=='verified'})
        if result['status']=='verified':celebrate(db,u,'verified:'+a.skill,'Skill verified',skill(a.skill)['name']+' reached the assessed level.',2)
        gaps=[c for c in result['competencies'] if c['status']!='demonstrated']
        if gaps:
            pathitems=[]
            practices=list(db.scalars(select(Challenge).where(Challenge.skill==a.skill,Challenge.pool=='practice',Challenge.status=='published')))
            for comp in gaps[:3]:
                name=comp['name'];related=[p for p in practices if name in p.content['competencies']]
                linked=[db.get(Challenge,resource_details(r).get('challenge_id')) for r in published_resources(db,a.skill,name) if resource_details(r)['kind']=='practice_challenge']
                linked=[challenge for challenge in linked if challenge and challenge.status=='published' and challenge.pool=='practice' and challenge.skill==a.skill]
                if linked:related=linked
                pathitems.append({'id':name+':read','type':'resource','competency':name,'status':'available','opened':None,**resource_snapshot(db,a.skill,name)})
                if related:pathitems.append({'id':name+':practice','type':'practice','competency':name,'title':related[0].content['title'],'challenge_id':related[0].id,'status':'available'})
            db.add(Path(user_id=u.id,attempt_id=a.id,skill=a.skill,items=pathitems))
    else:
        for path in db.scalars(select(Path).where(Path.user_id==u.id,Path.skill==a.skill,Path.archived==False)):
            changed=copy.deepcopy(path.items)
            for position,p in enumerate(changed):
                unlocked=all(previous.get('status')=='completed' for previous in changed[:position])
                if unlocked and p.get('challenge_id')==items[0].challenge_id and result['overall'] is not None and result['overall']>=.6:p['status']='completed'
            path.items=changed
    audit(db,None,'attempt.completed',a.id)

def resource_text(name):
    texts={
        'null_handling':'NULL means unknown, not zero or an empty string. Use IS NULL instead of = NULL. A NOT IN subquery containing NULL can make comparisons unknown. Prefer NOT EXISTS or a LEFT JOIN with an IS NULL check on the joined primary key. Test missing relationships as well as missing values.',
        'duplicates':'Two equal amounts can be two legitimate transactions. SUM(DISTINCT amount) discards values, not duplicate business events. Define which key makes an event unique, preserve meaningful repeated rows, and test joins that multiply rows.',
        'joins':'An INNER JOIN keeps matching rows. A LEFT JOIN preserves every row on the left, filling missing matches with NULL. A WHERE filter on the right table can unintentionally remove those preserved rows. Compare customers with zero, one, and multiple orders.',
        'aggregation':'GROUP BY defines one result per group. WHERE filters before grouping; HAVING filters groups afterward. Use COALESCE when an empty aggregate should be zero. Check whether joins introduce extra rows before summing.',
        'filtering':'Translate every condition explicitly. >= includes the boundary, > excludes it. ORDER BY needs a tie-breaker when the task requires a deterministic order. Test values below, at, and above the threshold.',
        'collections':'Choose a collection that matches the requirement. A set expresses distinct membership; a sequence preserves order and repeated occurrences. Ask whether duplicates are meaningful before removing them.',
        'algorithms':'Write the expected behavior before choosing an algorithm. Trace a small example, then consider empty input and repeated values. Check the numeric range of intermediate results and the cost of repeated sorting or scanning.',
        'validation':'Put request constraints on a dedicated DTO with Bean Validation annotations such as @NotBlank and @Positive. Trigger validation at the controller boundary with @Valid, then map field failures to a stable 4xx response. Verify that invalid requests never reach the service layer.',
        'rest_apis':'Define a stable HTTP contract with request and response DTOs, deliberate status codes, and narrow resource routes. Keep persistence entities out of the wire format. For retryable writes, bind an idempotency key to the caller, operation, and request digest, then return the stored outcome for a matching retry.',
        'services':'Keep business use cases in an injected service bean, with the transaction boundary around the operation that owns the full write. Calls that rely on Spring proxy advice must cross the proxy boundary; a same-instance call can bypass it. Verify committed and rolled-back state through the Spring context.',
        'persistence':'Load only the data required by the use case. Use a targeted projection, entity graph, or fetch join to avoid repeated lazy-load queries, and map results to response DTOs inside the service boundary. Check query counts and preserve pagination behavior when choosing a fetch plan.',
        'transactions':'Put a transaction around the service operation that owns a consistent database write. Make rollback rules explicit for the exceptions the application uses, and ensure calls cross the Spring proxy. Do not assume a database transaction can roll back an external payment or email; use an explicit recovery or outbox workflow when coordinating external effects.',
        'exceptions':'Use narrow domain exceptions and a centralized @RestControllerAdvice to map them to a stable HTTP contract. Return safe error details and a correlation identifier for unexpected failures; never expose stack traces to callers. Test status codes and response bodies at the HTTP boundary.',
        'edge_cases':'Turn each boundary in the specification into a test: empty input, one value, all equal values, mixed signs, large values, and fractional results. State the expected result before execution so a passing program is not mistaken for a correct one.'}
    return texts.get(name,'State the expected behavior, construct a counterexample, and verify it with a repeatable test.')

def seed_resources(db):
    pools={'sql':['filtering','joins','aggregation','null_handling','duplicates']}
    pools.update({slug:['collections','algorithms','edge_cases'] for slug in ['python','java','javascript']})
    pools['spring-boot']=['rest_apis','validation','services','persistence','transactions','exceptions']
    spring_checks={
        'rest_apis':('How should a matching retry of a POST be handled?',['Return the stored outcome for the same idempotency key and request.','Create a second resource for every retry.','Keep retry state only in controller memory.'],0),
        'validation':('Where should request-body constraints be enforced?',['On a validated DTO at the controller boundary.','Only after the entity has been saved.','Only in client-side form code.'],0),
        'services':('Where should a multi-step business write and its transaction boundary live?',['In an injected service operation that owns the use case.','In response serialization after the controller returns.','In a static helper with no Spring proxy.'],0),
        'persistence':('How should an endpoint avoid repeated lazy-load queries?',['Fetch required fields for the use case and verify query counts.','Serialize all entities with every relation eager.','Load the whole table and paginate in memory.'],0),
        'transactions':('What makes rollback behavior dependable?',['Use a clear service transaction boundary, explicit rollback rules, and a call through the Spring proxy.','Assume every same-class annotated call is intercepted.','Catch and ignore failures after writes.'],0),
        'exceptions':('How should expected API errors reach clients?',['Through narrow exception mappings with stable status and safe bodies.','As HTTP 200 responses containing stack traces.','By returning the raw database exception message.'],0),
    }
    for slug,competencies in pools.items():
        for competency in competencies:
            key=f'{slug}-{competency}-guide'
            if db.scalar(select(LearningResource).where(LearningResource.slug==key).order_by(LearningResource.version.desc())):continue
            question,options,answer=spring_checks.get(competency,('Which approach gives stronger, repeatable evidence?',['Assume a typical example represents every case.','Test the stated behavior, including relevant boundary cases.'],1))
            db.add(LearningResource(slug=key,skill=slug,competency=competency,title=competency.replace('_',' ').title()+': a practical guide',body=resource_text(competency),question=question,options=options,answer=answer,status='published',validation={'ok':True,'source':'curated-starter'},author='system',reviewer='system'))

def resource_snapshot(db,slug,competency):
    row=next((row for row in published_resources(db,slug,competency) if resource_details(row)['kind']!='practice_challenge'),None)
    if row:return {'resource_id':row.id,'resource_version':row.version,'title':row.title,'body':row.body,'question':row.question,'options':list(row.options),'answer':row.answer,**resource_details(row)}
    return {'title':competency.replace('_',' ').title()+': a practical guide','body':resource_text(competency),'question':'Which approach gives stronger evidence?','options':['Only testing an ordinary input','Testing the stated behavior including boundary cases'],'answer':1}

def tick():
    with LOCK,tx() as db:
        for a in db.scalars(select(Attempt).where(Attempt.status=='in_progress',Attempt.deadline<now()-5)):finalize(db,a,'deadline_reached')
        for a in db.scalars(select(Attempt).where(Attempt.status=='evaluating')):complete(db,a)
        candidate=db.execute(select(Job.id,Job.target).where(Job.status=='queued').order_by(Job.updated).limit(1)).first()
        if not candidate:return
        jid,target=candidate
        claim=db.execute(update(Job).where(Job.id==jid,Job.status=='queued').values(status='running',tries=Job.tries+1,updated=now()))
        if claim.rowcount!=1:return
        i=db.get(Item,target)
        if not i or i.evaluation is not None:
            db.execute(update(Job).where(Job.id==jid).values(status='completed',updated=now()));return
        c=copy.deepcopy(db.get(Challenge,i.challenge_id).content);payload=copy.deepcopy(i.submission);attempt=db.get(Attempt,i.attempt_id);candidate=db.get(User,attempt.user_id)
        ai_setting=db.get(AppSetting,'llm_enabled');ai_enabled=bool(attempt.policy.get('ai_explanation_opt_in') and LLM_READY and ai_setting and ai_setting.value.get('value') is True and candidate and (candidate.preferences or {}).get('ai_explanation_feedback',False))
        if ai_enabled and c.get('type')=='scenario' and payload.get('explanation','').strip():
            try:rate('ai-feedback:'+attempt.user_id,20,86400)
            except HTTPException:ai_enabled=False
    try:ev=evaluate(c,payload,ai_enabled=ai_enabled,ai_opted_in=bool(attempt.policy.get('ai_explanation_opt_in')))
    except RunnerUnavailable as e:ev={'status':'infra_error','message':str(e),'ratio':None,'tests':[],'competencies':{}}
    except Exception:
        import logging
        logging.exception('Evaluation failed; candidate work retained')
        ev={'status':'infra_error','message':'Evaluation could not be completed. Your work is retained; a free retake is available.','ratio':None,'tests':[],'competencies':{}}
    with LOCK,tx() as db:
        job=db.get(Job,jid);i=db.get(Item,target)
        if i:
            i.evaluation=ev;i.status='evaluated' if ev['status']=='completed' else 'infra_error'
            complete(db,db.get(Attempt,i.attempt_id))
        job.status='completed';job.updated=now()
