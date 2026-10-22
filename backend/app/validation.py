"""Execute references and Trust suggestions before allowing publication."""
from .catalog import validate
from .execution import code_run,sql_run,equivalent

def executable_validation(c):
    report=validate(c)
    if not report['ok']:return report
    checks=report['checks'][:]
    if c['type'] in ['sql','coding','debugging','trust']:
        reference=c['reference']
        for t in c['tests']:
            r=sql_run(t['dataset'],reference) if c['type']=='sql' else code_run(c['language'],reference,t['input'])
            actual=r.get('rows') if c['type']=='sql' else r.get('value')
            checks.append({'name':'Executed reference: '+t['label'],'passed':r['status']=='ok' and equivalent(actual,t['expected'])})
        if c['type']=='trust':
            for s in c['suggestions']:
                outcomes=[]
                for t in c['tests']:
                    r=code_run(c['language'],s['code'],t['input'])
                    outcomes.append(r['status']=='ok' and equivalent(r.get('value'),t['expected']))
                checks.append({'name':'Validated suggestion classification: '+s['id'],'passed':all(outcomes) if s['acceptable'] else not all(outcomes)})
    return {'ok':all(c['passed'] for c in checks),'checks':checks,'executed':True}
