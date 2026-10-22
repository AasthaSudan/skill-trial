import json
import math
from .execution import code_run,sql_run,equivalent,RunnerUnavailable
from .llm import grade_explanation,LLMUnavailable

def run(c,p,inp=None,dataset=None):
    if c['type']=='sql':return sql_run(dataset or c['tests'][0]['dataset'],p.get('query',''))
    return code_run(c['language'],p.get('code',''),inp)

def evaluate(c,p,ai_enabled=False,ai_opted_in=False):
    results=[]
    if c['type'] in ['coding','sql','debugging']:
        for t in c['tests']:
            r=run(c,p,t.get('input'),t.get('dataset'))
            actual=r.get('rows') if c['type']=='sql' else r.get('value')
            passed=r['status']=='ok' and equivalent(actual,t['expected'])
            results.append({'label':t['label'],'visibility':t['visibility'],'passed':passed,'status':'passed' if passed else r['status'] if r['status']!='ok' else 'wrong_answer','competencies':t['competencies'],'input':t.get('input'),'expected':t['expected'],'actual':actual,'message':r.get('message'),'wall_ms':r.get('wall_ms')})
        comp={name:sum(t['passed'] for t in results if name in t['competencies'])/sum(name in t['competencies'] for t in results) for name in c['competencies']}
        ratio=sum(t['passed'] for t in results)/len(results)
        criteria=[{'label':name.replace('_',' ').title(),'ratio':value,'weight':1/len(comp)} for name,value in comp.items()]
    elif c['type']=='scenario':
        answers=p.get('answers',{})
        scores=[float(answers.get(q['id'])==c['answers'][q['id']]) for q in c['questions']]
        deterministic=sum(scores)/len(scores)
        assisted=None
        if ai_enabled and c.get('explanation_rubric') and p.get('explanation','').strip():
            try:assisted=grade_explanation(p['explanation'],c['explanation_rubric'])
            except Exception:assisted=None
        if assisted:
            criteria=[{'label':q['prompt'],'ratio':score,'weight':.8/len(scores)} for q,score in zip(c['questions'],scores)]
            criteria.append({'label':'Written explanation (AI-assisted, capped at 20%)','ratio':assisted['score'],'weight':.2,'status':'evaluated','quotes':assisted['quotes']})
            ratio=deterministic*.8+assisted['score']*.2
        else:
            criteria=[{'label':q['prompt'],'ratio':score,'weight':1/len(scores)} for q,score in zip(c['questions'],scores)]
            if c.get('explanation_rubric') and ai_opted_in:
                reason='not_evaluated_no_explanation' if not p.get('explanation','').strip() else 'not_evaluated_ai_unavailable'
                criteria.append({'label':'Written explanation (optional AI feedback)','ratio':None,'weight':0,'status':reason})
            ratio=deterministic
        comp={x:ratio for x in c['competencies']}
    elif c['type']=='trust':
        decisions=p.get('decisions',{});categories=p.get('categories',{})
        truth=c['suggestions'];n=len(truth)
        acc=sum(decisions.get(s['id'])==('accept' if s['acceptable'] else 'reject') for s in truth)/n
        flawed=[s for s in truth if not s['acceptable']]
        defects=sum(categories.get(s['id'])==s['category'] and decisions.get(s['id'])=='reject' for s in flawed)/len(flawed)
        ce=0;correct_test=0;fix=0;note='No executable counterexample was submitted.'
        try:inp=json.loads(p.get('counterexample',''))
        except (ValueError,TypeError):inp=None
        if isinstance(inp,list) and len(inp)<=10000 and all(isinstance(x,int) and not isinstance(x,bool) and abs(x)<=1000000 for x in inp):
            reference=code_run(c['language'],c['reference'],inp)
            if reference['status']!='ok':raise RunnerUnavailable('Validated reference could not execute.')
            target=next((s for s in flawed if s['id']==p.get('target')),flawed[0])
            actual=code_run(c['language'],target['code'],inp)
            ce=float(actual['status']!='ok' or not equivalent(actual.get('value'),reference['value']))
            try:expected=json.loads(p.get('expected',''))
            except (ValueError,TypeError):expected=None
            correct_test=float(equivalent(expected,reference['value']))*(1 if ce else .5)
            note='Your counterexample exposed a difference from the validated reference.' if ce else 'The selected suggestion agreed with the reference on this input.'
        if p.get('code','').strip():
            for t in c['tests']:
                r=code_run(c['language'],p['code'],t['input']);ok=r['status']=='ok' and equivalent(r.get('value'),t['expected'])
                results.append({**t,'passed':ok,'status':'passed' if ok else r['status'] if r['status']!='ok' else 'wrong_answer','actual':r.get('value')})
            fix=sum(x['passed'] for x in results)/len(results)
        criteria=[{'label':'Suggestion decisions','ratio':acc,'weight':.3},{'label':'Defect identification','ratio':defects,'weight':.2},{'label':'Executed counterexample','ratio':ce,'weight':.2},{'label':'Correct, discriminating test','ratio':correct_test,'weight':.15},{'label':'Fix passes hidden tests','ratio':fix,'weight':.15}]
        ratio=sum(x['ratio']*x['weight'] for x in criteria);comp={x:ratio for x in c['competencies']}
        return {'status':'completed','ratio':ratio,'competencies':comp,'criteria':criteria,'tests':results,'counterexample_valid':bool(ce),'note':note,'evaluator':'trust-1.0','ai_assisted':False}
    else:raise ValueError('Unsupported challenge type')
    ai_used=bool(c['type']=='scenario' and assisted)
    return {'status':'completed','ratio':ratio,'competencies':comp,'criteria':criteria,'tests':results,'evaluator':c['type']+'-1.0','ai_assisted':ai_used,'ai_points_share':.2 if ai_used else 0}

def visible_evaluation(ev,practice=False):
    if not ev:return None
    out={k:v for k,v in ev.items() if k!='tests'}
    out['tests']=[{k:v for k,v in t.items() if k in ['label','visibility','passed','status','wall_ms','competencies'] or (practice or t['visibility']=='sample') and k in ['input','expected','actual','message']} for t in ev.get('tests',[])]
    return out
