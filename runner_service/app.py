"""Private API for isolated candidate-code execution.

Run this service on a dedicated Linux host with a container runtime. Requests
are authenticated and replay-protected; this service has no application DB.
"""
import asyncio
import hashlib
import hmac
import json
import os
import re
import threading
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.app.execution import docker_code_run, RunnerUnavailable
from backend.app.config import OCI_RUNTIME

SECRET = os.environ.get('RUNNER_HMAC_SECRET', '')
if len(SECRET) < 32:
    raise RuntimeError('RUNNER_HMAC_SECRET must contain at least 32 characters.')

MAX_BODY = 256_000
NONCE_LOCK = threading.Lock()
USED_NONCES = {}
app = FastAPI(title='SkillTrial Isolated Runner', version='1.0.0', docs_url=None, redoc_url=None, openapi_url=None)


@app.get('/healthz')
def health():
    return {'status': 'ok'}


@app.get('/readyz')
def ready():
    import subprocess
    try:
        result = subprocess.run(['docker', 'info', '--format', '{{json .Runtimes}}'], capture_output=True, text=True, timeout=4)
        runtimes = json.loads(result.stdout) if result.returncode == 0 else {}
        if result.returncode != 0 or OCI_RUNTIME not in runtimes:
            return JSONResponse({'status': 'not_ready'}, status_code=503)
    except (OSError, subprocess.TimeoutExpired):
        return JSONResponse({'status': 'not_ready'}, status_code=503)
    return {'status': 'ready'}


async def bounded_body(request: Request):
    try:
        declared = int(request.headers.get('content-length', '0'))
    except ValueError:
        return None
    if declared > MAX_BODY:
        return None
    chunks = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_BODY:
            return None
        chunks.append(chunk)
    return b''.join(chunks)


def authenticate(request: Request, raw: bytes):
    timestamp = request.headers.get('X-SkillTrial-Timestamp', '')
    nonce = request.headers.get('X-SkillTrial-Nonce', '')
    signature = request.headers.get('X-SkillTrial-Signature', '')
    if not re.fullmatch(r'[0-9]{1,12}', timestamp) or not re.fullmatch(r'[0-9a-f]{32}', nonce) or not re.fullmatch(r'[0-9a-f]{64}', signature):
        return False
    if abs(int(time.time()) - int(timestamp)) > 60:
        return False
    signed = '\n'.join(['POST', '/v1/run', timestamp, nonce, hashlib.sha256(raw).hexdigest()]).encode('utf-8')
    expected = hmac.new(SECRET.encode('utf-8'), signed, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    current = time.time()
    with NONCE_LOCK:
        for old, expiry in list(USED_NONCES.items()):
            if expiry < current:
                USED_NONCES.pop(old, None)
        if nonce in USED_NONCES:
            return False
        USED_NONCES[nonce] = current + 120
    return True


@app.post('/v1/run')
async def run(request: Request):
    raw = await bounded_body(request)
    if raw is None:
        return JSONResponse({'error': 'request_too_large'}, status_code=413)
    if not authenticate(request, raw):
        return JSONResponse({'error': 'request_not_authorized'}, status_code=401)
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return JSONResponse({'error': 'invalid_json'}, status_code=400)
    if not isinstance(payload, dict) or set(payload) != {'language', 'code', 'input'}:
        return JSONResponse({'error': 'invalid_payload'}, status_code=422)
    language = payload['language']
    code = payload['code']
    if language not in ['python', 'javascript', 'java'] or not isinstance(code, str) or len(code.encode('utf-8')) > 200_000:
        return JSONResponse({'error': 'invalid_execution_request'}, status_code=422)
    try:
        result = await asyncio.to_thread(docker_code_run, language, code, payload['input'])
    except RunnerUnavailable:
        return JSONResponse({'error': 'runner_unavailable'}, status_code=503)
    return result
