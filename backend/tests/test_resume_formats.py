import io
import pytest
from docx import Document
from reportlab.pdfgen import canvas
from conftest import signup,headers

TEXT='QA Candidate\nTechnical skills\nIntermediate SQL\nProficient Python\nProjects\nBuilt customer reporting queries using joins, aggregation, missing values and repeatable test cases.\n'
def document_bytes(kind):
 if kind=='txt':return TEXT.encode()
 out=io.BytesIO()
 if kind=='docx':
  doc=Document()
  for line in TEXT.splitlines():doc.add_paragraph(line)
  doc.save(out)
 else:
  page=canvas.Canvas(out)
  for n,line in enumerate(TEXT.splitlines()):page.drawString(50,790-n*20,line)
  page.save()
 return out.getvalue()

@pytest.mark.parametrize('kind',['txt','pdf','docx'])
def test_real_resume_formats_parse_and_deduplicate(client,kind):
 signup(client)
 data=document_bytes(kind)
 r=client.post('/api/v1/resumes',files={'file':('resume.'+kind,data,'application/octet-stream')},headers=headers(client))
 assert r.status_code==201,r.text
 claims=client.get('/api/v1/me/skills').json()
 assert {x['skill'] for x in claims}=={'sql','python'}
 assert all(x['status']=='pending_review' and x['evidence'] for x in claims)
 repeated=client.post('/api/v1/resumes',files={'file':('resume.'+kind,data,'application/octet-stream')},headers=headers(client))
 assert repeated.json()['id']==r.json()['id']
 assert len(client.get('/api/v1/resumes').json())==1

@pytest.mark.parametrize('filename,data,code',[
 ('empty.txt',b'','FILE_EMPTY'),
 ('fake.pdf',b'not a PDF document','FILE_TYPE_UNSUPPORTED'),
 ('script.exe',b'not a resume','FILE_TYPE_UNSUPPORTED'),
 ('too-short.txt',b'SQL and Python','TEXT_TOO_SHORT'),
 ('oversized.txt',b'x'*(5*1024*1024+1),'FILE_TOO_LARGE'),
])
def test_invalid_uploads_are_actionable_and_do_not_create_claims(client,filename,data,code):
 signup(client)
 r=client.post('/api/v1/resumes',files={'file':(filename,data,'application/octet-stream')},headers=headers(client))
 assert r.status_code==422 and r.json()['error']['code']==code
 assert client.get('/api/v1/resumes').json()==[]
 assert client.get('/api/v1/me/skills').json()==[]
