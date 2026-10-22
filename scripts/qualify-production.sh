#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.production}"
COMPOSE_FILE="$ROOT_DIR/deploy/production.compose.yml"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Production environment file not found: $ENV_FILE" >&2
  exit 2
fi
if grep -Eq 'REPLACE_WITH|example\.com' "$ENV_FILE"; then
  echo "Replace the example domain and placeholder credentials before qualification." >&2
  exit 2
fi

read_env() {
  local key="$1"
  awk -F= -v key="$key" '$1 == key {sub(/^[^=]*=/, ""); print; exit}' "$ENV_FILE"
}

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

APP_URL="$(read_env APP_URL)"
if [[ -z "$APP_URL" ]]; then
  echo "APP_URL is required in $ENV_FILE" >&2
  exit 2
fi
if [[ "$APP_URL" != https://* ]]; then
  echo "APP_URL must use HTTPS for production qualification." >&2
  exit 2
fi

compose config --quiet
echo "PASS production Compose configuration"

compose exec -T db sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null
echo "PASS PostgreSQL readiness"

compose exec -T api python - <<'PY'
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from backend.app.config import ROOT
from backend.app.db import engine

config = Config(str(ROOT / "backend" / "alembic.ini"))
expected = set(ScriptDirectory.from_config(config).get_heads())
with engine.connect() as connection:
    applied = set(MigrationContext.configure(connection).get_current_heads())
if not expected or applied != expected:
    raise SystemExit(f"Database revisions {sorted(applied)} do not match source heads {sorted(expected)}")
print("PASS API migration state: " + ",".join(sorted(applied)))
PY

curl --fail --silent --show-error --max-time 12 "$APP_URL/healthz" >/dev/null
echo "PASS public HTTPS health endpoint"

compose exec -T api python - <<'PY'
import hashlib
import hmac
import json
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from backend.app.config import RUNNER_HMAC_SECRET, RUNNER_URL
from backend.app.execution import remote_code_run

cases = {
    "python": ("def solve(nums):\n    return sum(nums)\n", [2, 3]),
    "javascript": ("function solve(nums) { return nums.reduce((a, b) => a + b, 0); }", [2, 3]),
    "java": ("class Solution { public static Object solve(int[] nums) { return nums[0] + nums[1]; } }", [2, 3]),
}
for language, (code, values) in cases.items():
    result = remote_code_run(language, code, values)
    if result.get("status") != "ok" or result.get("value") != 5:
        raise SystemExit(f"Remote runner qualification failed for {language}: {result.get('status')}")
    print(f"PASS authenticated isolated runner: {language}")

if not RUNNER_URL or len(RUNNER_HMAC_SECRET) < 32:
    raise SystemExit("Remote runner qualification requires the configured private URL and HMAC secret")

path = "/v1/run"
body = json.dumps(
    {"language": "python", "code": "def solve(nums):\n    return sum(nums)\n", "input": [2, 3]},
    separators=(",", ":"),
).encode("utf-8")

def signature(timestamp, nonce):
    signed = "\n".join(
        ["POST", path, timestamp, nonce, hashlib.sha256(body).hexdigest()]
    ).encode("utf-8")
    return hmac.new(RUNNER_HMAC_SECRET.encode("utf-8"), signed, hashlib.sha256).hexdigest()

def send(timestamp, nonce, signed_value):
    request = Request(
        RUNNER_URL + path,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-SkillTrial-Timestamp": timestamp,
            "X-SkillTrial-Nonce": nonce,
            "X-SkillTrial-Signature": signed_value,
        },
    )
    try:
        with urlopen(request, timeout=25) as response:
            return response.status, response.read(256000)
    except HTTPError as error:
        return error.code, error.read(65536)

now = str(int(time.time()))
fresh_nonce = uuid4().hex
valid_signature = signature(now, fresh_nonce)
invalid_signature = ("0" if valid_signature[0] != "0" else "1") + valid_signature[1:]
if send(now, fresh_nonce, invalid_signature)[0] != 401:
    raise SystemExit("Runner accepted a request with an invalid HMAC signature")
print("PASS runner rejects invalid HMAC signatures")

stale = str(int(time.time()) - 120)
stale_nonce = uuid4().hex
if send(stale, stale_nonce, signature(stale, stale_nonce))[0] != 401:
    raise SystemExit("Runner accepted a stale signed request")
print("PASS runner rejects expired timestamps")

replay_timestamp = str(int(time.time()))
replay_nonce = uuid4().hex
replay_signature = signature(replay_timestamp, replay_nonce)
status, response_body = send(replay_timestamp, replay_nonce, replay_signature)
if status != 200:
    raise SystemExit(f"Runner rejected a fresh signed request: HTTP {status}")
result = json.loads(response_body)
if result.get("status") != "ok" or result.get("value") != 5:
    raise SystemExit("Runner returned the wrong result during replay qualification")
if send(replay_timestamp, replay_nonce, replay_signature)[0] != 401:
    raise SystemExit("Runner accepted a replayed nonce")
print("PASS runner rejects replayed nonces")
PY

echo "PASS automated production qualification checks"
echo "Complete the remaining manual, provider, restore, security, accessibility, and load checks in docs/PRODUCTION_DEPLOYMENT.md."
