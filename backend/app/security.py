import hashlib
import hmac
import os
import secrets
import threading
from collections import defaultdict, deque
from pathlib import Path
from argon2 import PasswordHasher
from cryptography.fernet import Fernet
from fastapi import HTTPException, Request
from sqlalchemy import select
from .config import VAR, ENV
from .db import now
from .models import AuthSession, Token, User, Audit

HASHER=PasswordHasher(time_cost=3,memory_cost=65536,parallelism=2)
DUMMY=HASHER.hash(secrets.token_urlsafe(20))
keyfile=VAR/'encryption.key'
if not keyfile.exists():
    try:
        with keyfile.open('xb') as f:f.write(Fernet.generate_key())
    except FileExistsError:pass
try:os.chmod(keyfile,0o600)
except OSError:pass
CRYPT=Fernet(keyfile.read_bytes())
RATES=defaultdict(deque)
RATE_LOCK=threading.Lock()

def fail(code,message,status=400,**details):
    raise HTTPException(status,{'code':code,'message':message,'details':details})

def rate(key,limit,seconds):
    with RATE_LOCK:
        q=RATES[key];t=now()
        while q and q[0]<t-seconds:q.popleft()
        if len(q)>=limit:fail('RATE_LIMIT','Too many requests. Please try again later.',429)
        q.append(t)

def hashed(value):return hashlib.sha256(value.encode()).hexdigest()

def password_ok(password,email):
    if len(password)<10 or len(password)>200 or password.lower() in {'password123','1234567890','qwerty12345'}:
        fail('PASSWORD_POLICY','Use a password of 10–200 characters that is not commonly used.',422)
    if len(email.split('@')[0])>=4 and email.split('@')[0].lower() in password.lower():
        fail('PASSWORD_POLICY','Your password must not contain your email name.',422)

def auth(db,request:Request,admin=False):
    token=request.cookies.get('st_session','')
    s=db.get(AuthSession,hashed(token)) if token else None
    u=db.get(User,s.user_id) if s else None
    if not s or not u or u.status not in ['active','pending_deletion'] or now()-s.seen>7200 or now()-s.created>604800:
        fail('AUTH_REQUIRED','Please sign in to continue.',401)
    if request.method not in ['GET','HEAD','OPTIONS']:
        if not hmac.compare_digest(request.headers.get('X-CSRF-Token',''),s.csrf):fail('CSRF_TOKEN_INVALID','Refresh your session and try again.',403)
    s.seen=now()
    if admin:
        if u.role!='admin':fail('PERMISSION_DENIED','Administrator access is required.',403)
        if isinstance(admin,str):
            permissions=u.profile.get('admin_permissions',['*']) if isinstance(u.profile,dict) else ['*']
            if '*' not in permissions and admin not in permissions:fail('PERMISSION_DENIED','This administrator role does not include that permission.',403)
    if u.status=='pending_deletion' and request.url.path not in ['/api/v1/me','/api/v1/me/cancel-deletion','/api/v1/auth/logout']:
        fail('ACCOUNT_PENDING_DELETION','Cancel account deletion in Settings before continuing.',409)
    return u

def owned(db,model,id,user):
    row=db.get(model,id)
    if not row or row.user_id!=user.id:fail('NOT_FOUND','We could not find that.',404)
    return row

def audit(db,user,action,target=''):
    db.add(Audit(actor=user.id if user else 'system',action=action,target=target))

def issue_token(db,u,kind):
    token=secrets.token_urlsafe(32)
    db.add(Token(token=hashed(token),user_id=u.id,kind=kind,expires=now()+(3600 if kind=='reset' else 86400)))
    return token
