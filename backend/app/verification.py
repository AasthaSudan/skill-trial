"""Pure evidence decision. This module never imports the reward system."""
def decide(items,policy,level):
    evaluable=[i for i in items if i.get('evaluation') and i['evaluation']['status']=='completed']
    comps=[]
    for name in policy['required']:
        rows=[i['evaluation']['competencies'][name] for i in evaluable if name in i['evaluation'].get('competencies',{})]
        score=sum(rows)/len(rows) if rows else None
        comps.append({'name':name,'status':'not_assessed' if score is None else 'demonstrated' if score>=policy['competency_pass'] else 'not_demonstrated','score':score,'items':len(rows)})
    coverage=sum(c['score'] is not None for c in comps)/max(1,len(comps))
    overall=sum(i['evaluation']['ratio'] for i in evaluable)/len(evaluable) if evaluable else None
    reasons=[]
    if len(evaluable)<policy['min_items']:reasons.append(f"Only {len(evaluable)} of the required {policy['min_items']} tasks could be evaluated.")
    if coverage<policy['coverage']:reasons.append('Too few required competencies were assessed for a reliable decision.')
    demonstrated=[c for c in comps if c['status']=='demonstrated']
    rank={'beginner':0,'intermediate':1,'advanced':2}
    at_level=sum(i['evaluation']['ratio']>=policy['item_pass'] and rank[i['level']]>=rank[level] for i in evaluable)
    trust_ok=not policy.get('trust_required') or any(i['type']=='trust' and i['evaluation']['ratio']>=policy['item_pass'] for i in evaluable)
    if reasons:status='insufficient_evidence'
    elif len(demonstrated)==len(comps) and overall>=policy['overall'] and at_level>=policy['at_level'] and trust_ok:
        status='verified';reasons=[f'All required competencies were demonstrated at the assessed {level} level.']
    else:
        status='partially_verified' if demonstrated else 'not_verified'
        reasons=[f"{c['name'].replace('_',' ').capitalize()} {'was not assessed' if c['score'] is None else 'did not meet the competency threshold'} ." for c in comps if c['status']!='demonstrated']
        if overall<policy['overall']:reasons.append(f"Overall performance was {overall:.0%}; {policy['overall']:.0%} is required.")
        if at_level<policy['at_level']:reasons.append(f"{at_level} tasks at the target difficulty passed; {policy['at_level']} are required.")
    skipped=sum(i.get('status')=='not_attempted' for i in items)
    infra=sum(i.get('status')=='infra_error' for i in items)
    if skipped:reasons.append(f'{skipped} tasks were not attempted and were excluded from scoring.')
    if infra:reasons.append(f'{infra} tasks could not be evaluated due to a platform issue. A free retake is available.')
    return {'status':status,'demonstrated_level':level if status=='verified' else None,'overall':overall,'coverage':coverage,'competencies':comps,'reasons':reasons,'infra_incident':bool(infra),'evaluable':len(evaluable)}
