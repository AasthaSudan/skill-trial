from io import BytesIO
from html import escape
from datetime import datetime,timezone
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether

def pdf(snapshot,fingerprint):
    output=BytesIO();doc=SimpleDocTemplate(output,pagesize=(595,842),rightMargin=44,leftMargin=44,topMargin=42,bottomMargin=45,title='SkillTrial Verification Report',author='SkillTrial')
    styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='SmallProof',fontSize=8,leading=12,textColor=colors.HexColor('#475569')))
    body=[]
    def p(text,style='BodyText'):return Paragraph(escape(str(text)),styles[style])
    def add(text,style='BodyText'):body.extend([p(text,style),Spacer(1,10)])
    result=snapshot['result']
    add('SkillTrial', 'Title');add('SKILL VERIFICATION REPORT','SmallProof')
    add(snapshot['candidate'],'Heading1');add(snapshot['skill_name']+' · '+snapshot['level'].title(),'Heading2')
    add(result['status'].replace('_',' ').title(),'Heading2')
    add(f"Reference: {snapshot['ref']} | Assessed: {datetime.fromtimestamp(snapshot['date'],timezone.utc).strftime('%d %b %Y, %H:%M UTC')}",'SmallProof')
    add(f"Claimed: {snapshot['claim'].get('level') or 'Not stated'} | Demonstrated: {result.get('demonstrated_level') or 'Not established'}")
    add('Why this outcome','Heading2')
    for reason in result['reasons']:add(reason)
    add('Competency evidence','Heading2')
    rows=[[p('Competency'),p('Evidence'),p('Score')]]
    for c in result['competencies']:rows.append([p(c['name'].replace('_',' ').title()),p(c['status'].replace('_',' ')),p('Not assessed' if c['score'] is None else f"{c['score']:.0%}")])
    table=Table(rows,colWidths=[170,240,95],hAlign='LEFT');table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eef0f7')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#d8deeb'))]));body.extend([table,Spacer(1,18)])
    add('Assessment tasks','Heading2')
    for c in snapshot['challenges']:
        ev=c.get('evaluation');score=f"{ev['ratio']:.0%}" if ev and ev.get('ratio') is not None else 'Not evaluated'
        body.extend([KeepTogether([p(c['title'],'Heading3'),p(f"{c['type'].title()} | {c['difficulty'].title()} | {score} | {c['status'].replace('_',' ')}"),Spacer(1,8)])])
        if ev:
            for criterion in ev.get('criteria',[]):
                ratio=criterion.get('ratio')
                status=criterion.get('status')
                note={'not_evaluated_ai_unavailable':'AI feedback unavailable; deterministic score used','not_evaluated_no_explanation':'No written explanation was submitted'}.get(status,'Not evaluated')
                add(f"{criterion['label']}: {ratio:.0%}" if ratio is not None else f"{criterion['label']}: {note}",'SmallProof')
    add('Assessment limitations','Heading2')
    for limitation in snapshot['limitations']:add(limitation)
    add('Snapshot fingerprint (SHA-256)','Heading3');add(fingerprint,'SmallProof')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#64748b'));canvas.drawString(44,27,snapshot['ref']);canvas.drawRightString(551,27,f'Page {doc.page}')
    doc.build(body,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
