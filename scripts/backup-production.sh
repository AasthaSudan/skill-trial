#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.production}"
COMPOSE_FILE="$ROOT_DIR/deploy/production.compose.yml"
DEST="${1:-$ROOT_DIR/backups/$(date -u +%Y%m%dT%H%M%SZ)}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Production environment file not found: $ENV_FILE" >&2
  exit 2
fi
if [[ -z "${AGE_RECIPIENT:-}" ]]; then
  echo "Set AGE_RECIPIENT to the backup owner's age public key." >&2
  exit 2
fi
command -v age >/dev/null || { echo "Install the age CLI before creating an encrypted backup." >&2; exit 2; }
if [[ -e "$DEST" ]]; then
  echo "Backup destination already exists: $DEST" >&2
  exit 2
fi
mkdir -p "$DEST"
chmod 700 "$DEST"
trap 'rm -f -- "$DEST/database.dump.age" "$DEST/application-data.tar.gz.age" "$DEST/SHA256SUMS"' ERR
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db \
  sh -lc 'pg_dump --format=custom --no-owner --username="$POSTGRES_USER" "$POSTGRES_DB"' \
  | age --recipient "$AGE_RECIPIENT" > "$DEST/database.dump.age"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T api \
  tar -C /srv/skilltrial/var -czf - . | age --recipient "$AGE_RECIPIENT" > "$DEST/application-data.tar.gz.age"
chmod 600 "$DEST/database.dump.age" "$DEST/application-data.tar.gz.age"
sha256sum "$DEST/database.dump.age" "$DEST/application-data.tar.gz.age" > "$DEST/SHA256SUMS"
chmod 600 "$DEST/SHA256SUMS"
echo "Created encrypted backup set at $DEST"
