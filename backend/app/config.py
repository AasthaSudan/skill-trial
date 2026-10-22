import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if (ROOT/'.env').exists():
    for line in (ROOT/'.env').read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            name,value=line.split('=',1)
            os.environ.setdefault(name.strip(),value.strip().strip('"').strip("'"))
VAR = Path(os.environ.get('SKILLTRIAL_DATA', ROOT / 'var'))
VAR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.environ.get('DATABASE_URL', f'sqlite:///{(VAR / "skilltrial.db").as_posix()}')
if DATABASE_URL.startswith('postgres://'):DATABASE_URL='postgresql+psycopg://'+DATABASE_URL[len('postgres://'):]
elif DATABASE_URL.startswith('postgresql://'):DATABASE_URL='postgresql+psycopg://'+DATABASE_URL[len('postgresql://'):]
ENV = os.environ.get('SKILLTRIAL_ENV', 'development')
DEMO_CONTENT = ENV=='development' and os.environ.get('DEMO_CONTENT','true').lower()=='true'
COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'false').lower() == 'true'
RUNNER_MODE = os.environ.get('RUNNER_MODE', 'docker')
OCI_RUNTIME = os.environ.get('OCI_RUNTIME', 'runc')
RUN_BACKGROUND_WORKER = os.environ.get('RUN_BACKGROUND_WORKER', 'true' if ENV=='development' else 'false').lower()=='true'
LLM_ENABLED = os.environ.get('LLM_ENABLED', 'false').lower()=='true'
LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
LLM_MODEL = os.environ.get('LLM_MODEL', '')
LLM_API_BASE_URL = os.environ.get('LLM_API_BASE_URL', 'https://api.anthropic.com').rstrip('/')
LLM_READY = bool(LLM_ENABLED and LLM_API_KEY and LLM_MODEL)
RUNNER_URL = os.environ.get('RUNNER_URL', '').rstrip('/')
RUNNER_HMAC_SECRET = os.environ.get('RUNNER_HMAC_SECRET', '')
RUNNER_TIMEOUT = max(1,min(60,float(os.environ.get('RUNNER_TIMEOUT', '25'))))
RUNNER_READY = bool(RUNNER_URL and len(RUNNER_HMAC_SECRET)>=32)
RUNNER_WORKDIR = os.environ.get('RUNNER_WORKDIR', '')
COOLDOWN_H = float(os.environ.get('REASSESS_COOLDOWN_H', '24'))
GRACE = 5
