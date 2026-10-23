import io
import json
import os
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest
from app import llm

class Reply:
    def __init__(self,payload):self.payload=payload
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,n):return self.payload[:n]

@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(llm,'LLM_READY',True)
    monkeypatch.setattr(llm,'LLM_API_KEY','fake-unit-test-key')
    monkeypatch.setattr(llm,'LLM_API_BASE_URL','https://provider.example.test')
    monkeypatch.setattr(llm,'LLM_MODEL','models/gemini-test')
    monkeypatch.setattr(llm,'LLM_PROVIDER','gemini')

def fake_response(monkeypatch,payload,capture=None):
    raw=payload if isinstance(payload,bytes) else json.dumps(payload).encode()
    def open_request(request,timeout):
        if capture is not None:capture.append((request,timeout))
        return Reply(raw)
    monkeypatch.setattr(llm.urllib.request,'urlopen',open_request)

def gemini_answer(text,**candidate):
    return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':text}]},**candidate}]}

def test_gemini_native_request_and_json_response(configured,monkeypatch):
    captured=[];fake_response(monkeypatch,gemini_answer('{"score":0.8}'),captured)
    assert llm._json_response('System instructions','Synthetic prompt',300)=={'score':0.8}
    request,timeout=captured[0];body=json.loads(request.data)
    assert request.full_url=='https://provider.example.test/v1beta/models/gemini-test:generateContent'
    assert request.get_header('X-goog-api-key')=='fake-unit-test-key'
    assert 'fake-unit-test-key' not in request.full_url
    assert body['systemInstruction']['parts'][0]['text']=='System instructions'
    assert body['contents'][0]['parts'][0]['text']=='Synthetic prompt'
    assert body['generationConfig']=={'maxOutputTokens':300,'responseMimeType':'application/json'}
    assert timeout==12

def test_anthropic_remains_supported(configured,monkeypatch):
    monkeypatch.setattr(llm,'LLM_PROVIDER','anthropic');monkeypatch.setattr(llm,'LLM_MODEL','claude-test')
    captured=[];fake_response(monkeypatch,{'content':[{'type':'text','text':'{"ok":true}'}]},captured)
    assert llm._json_response('System','Prompt')=={'ok':True}
    request,_=captured[0];assert request.full_url.endswith('/v1/messages')
    assert request.get_header('X-api-key')=='fake-unit-test-key'
    assert json.loads(request.data)['model']=='claude-test'
    assert 'temperature' not in json.loads(request.data)

def test_gemini_ignores_thought_parts(configured,monkeypatch):
    fake_response(monkeypatch,gemini_answer('',content={'parts':[{'thought':True,'text':'{"score":1}'},{'text':'{"score":0.25}'}]}))
    assert llm._json_response('System','Prompt')=={'score':0.25}

@pytest.mark.parametrize('payload',[
    {'promptFeedback':{'blockReason':'SAFETY'}},
    gemini_answer('{"ok":true}',finishReason='MAX_TOKENS'),
    gemini_answer('{"ok":true}',finishReason='SAFETY'),
    gemini_answer('not JSON'),
    gemini_answer('[]'),
    {'candidates':[None]},
    {'candidates':[{'finishReason':'STOP','content':{'parts':'invalid'}}]},
    b'x'*256001,
])
def test_blocked_incomplete_or_malformed_answers_are_unavailable(configured,monkeypatch,payload):
    fake_response(monkeypatch,payload)
    with pytest.raises(llm.LLMUnavailable):llm._json_response('System','Prompt')

@pytest.mark.parametrize('error',[
    urllib.error.HTTPError('https://provider.example.test',429,'quota exceeded',{},io.BytesIO(b'secret provider body')),
    urllib.error.HTTPError('https://provider.example.test',401,'invalid key',{},io.BytesIO(b'secret provider body')),
    TimeoutError('provider timeout'),
])
def test_provider_failures_do_not_leak_secrets(configured,monkeypatch,error):
    def fail(*args,**kwargs):raise error
    monkeypatch.setattr(llm.urllib.request,'urlopen',fail)
    with pytest.raises(llm.LLMUnavailable) as caught:llm._json_response('System','Prompt')
    assert 'secret' not in str(caught.value) and 'fake-unit-test-key' not in str(caught.value)

def test_explanation_falls_back_when_gemini_is_unavailable(configured,monkeypatch):
    from app.evaluation import evaluate
    monkeypatch.setattr(llm.urllib.request,'urlopen',lambda *a,**k:(_ for _ in ()).throw(TimeoutError()))
    content={'type':'scenario','questions':[{'id':'q1','prompt':'Choose the boundary'}],'answers':{'q1':'a'},'competencies':['service_boundaries'],'explanation_rubric':['Names the boundary']}
    result=evaluate(content,{'answers':{'q1':'a'},'explanation':'Keep validation at the request boundary.'},ai_enabled=True,ai_opted_in=True)
    assert result['ratio']==1 and result['ai_assisted'] is False
    assert result['criteria'][-1]['status']=='not_evaluated_ai_unavailable'

def test_gemini_resume_suggestions_require_real_evidence_and_redaction(configured,monkeypatch):
    key='AIza'+'X'*35;captured=[]
    fake_response(monkeypatch,gemini_answer(json.dumps({'claims':[{'skill':'sql','level':'intermediate','evidence':'Intermediate SQL reporting queries'},{'skill':'java','level':'advanced','evidence':'Invented Java experience statement'}]})),captured)
    result=llm.extract_claims('QA Person qa@example.test '+key+'\nIntermediate SQL reporting queries',['QA Person'])
    assert [x['skill'] for x in result]==['sql']
    prompt=json.loads(captured[0][0].data)['contents'][0]['parts'][0]['text']
    assert 'qa@example.test' not in prompt and key not in prompt and 'QA Person' not in prompt

@pytest.mark.parametrize('provider,key,enabled,ready',[
    ('gemini','fake-test-key','true',True),
    ('gemini','','true',False),
    ('gemini','fake-test-key','false',False),
    ('unsupported','fake-test-key','true',False),
])
def test_provider_configuration_uses_explicit_readiness(provider,key,enabled,ready):
    env={**os.environ,'LLM_PROVIDER':provider,'GEMINI_API_KEY':key,'LLM_API_KEY':'','LLM_MODEL':'','LLM_API_BASE_URL':'','LLM_ENABLED':enabled,'PYTHONDONTWRITEBYTECODE':'1'}
    code="from app.config import LLM_READY,LLM_API_BASE_URL,LLM_MODEL; import json; print(json.dumps([LLM_READY,LLM_API_BASE_URL,LLM_MODEL]))"
    result=json.loads(subprocess.check_output([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],env=env))
    assert result[0] is ready
    if provider=='gemini':assert result[1:]==['https://generativelanguage.googleapis.com','gemini-3.5-flash-lite']
