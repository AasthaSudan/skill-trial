import os
from pathlib import Path
import tempfile

TEST_DATA=Path(tempfile.mkdtemp(prefix='skilltrial-tests-'))
os.environ['SKILLTRIAL_DATA']=str(TEST_DATA)
os.environ['DATABASE_URL']='sqlite:///'+(TEST_DATA/'test.db').as_posix()

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base,engine
from app.service import LOCK
from app.security import RATES,RATE_LOCK

@pytest.fixture
def client():
    with RATE_LOCK:RATES.clear()
    with LOCK:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
    with TestClient(app) as c:yield c

DUMMY_TEST_PASSWORD = 'dummy_test_password_for_unit_tests_only'

def signup(client,name='Test Challenger',email='candidate@example.com',password=DUMMY_TEST_PASSWORD):
    r=client.post('/api/v1/auth/register',json={'name':name,'email':email,'password':password,'accept_privacy':True})
    assert r.status_code==202,r.text
    r=client.post('/api/v1/auth/login',json={'email':email,'password':password})
    assert r.status_code==200,r.text
    return r.json()

def headers(client,key=None):
    return {'X-CSRF-Token':client.cookies.get('st_csrf'),**({'Idempotency-Key':key} if key else {})}
