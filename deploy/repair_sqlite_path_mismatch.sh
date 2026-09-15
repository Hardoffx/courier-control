#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR=/opt/courier-control
APP_USER=courierctl
APP_GROUP=courierctl
SERVICE=courier-control.service
ENV_FILE="$APP_DIR/.env"
LEGACY_DB="$APP_DIR/db.sqlite3"

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/repair_sqlite_path_mismatch.sh" >&2
  exit 1
fi
[[ -d "$APP_DIR/.git" ]] || { echo "Courier Control is not installed at $APP_DIR" >&2; exit 1; }
[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE" >&2; exit 1; }

TARGET_DB="$(python3 - "$ENV_FILE" <<'PY'
from pathlib import Path
import sys
for raw in Path(sys.argv[1]).read_text().splitlines():
    line=raw.strip()
    if line.startswith('SQLITE_PATH='):
        print(line.split('=',1)[1].strip().strip('"\''))
        break
PY
)"
[[ -n "$TARGET_DB" ]] || { echo "SQLITE_PATH is missing from $ENV_FILE" >&2; exit 1; }
case "$TARGET_DB" in
  "$APP_DIR"/*) ;;
  *) echo "Refusing unexpected SQLITE_PATH outside $APP_DIR: $TARGET_DB" >&2; exit 1 ;;
esac
mkdir -p "$(dirname "$TARGET_DB")"

has_table(){
  python3 - "$1" "$2" <<'PY'
from pathlib import Path
import sqlite3, sys
path=Path(sys.argv[1]); table=sys.argv[2]
if not path.exists():
    raise SystemExit(1)
try:
    con=sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    row=con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    con.close()
except sqlite3.Error:
    raise SystemExit(1)
raise SystemExit(0 if row else 1)
PY
}

TARGET_READY=0
LEGACY_READY=0
has_table "$TARGET_DB" accounts_user && TARGET_READY=1 || true
has_table "$LEGACY_DB" accounts_user && LEGACY_READY=1 || true

echo "Configured DB: $TARGET_DB"
echo "Configured DB has application schema: $TARGET_READY"
echo "Legacy DB: $LEGACY_DB"
echo "Legacy DB has application schema: $LEGACY_READY"

if [[ $TARGET_READY -eq 0 && $LEGACY_READY -eq 1 ]]; then
  echo
  echo "Detected the deployment mismatch: migrations/accounts were created in the legacy DB while Gunicorn used SQLITE_PATH."
  echo "Preserving the legacy database into the configured data path."
  systemctl stop "$SERVICE"
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  if [[ -e "$TARGET_DB" ]]; then
    cp -a "$TARGET_DB" "$TARGET_DB.pre-repair-$stamp"
  fi
  python3 - "$LEGACY_DB" "$TARGET_DB" <<'PY'
import sqlite3, sys
src=sqlite3.connect(sys.argv[1])
dst=sqlite3.connect(sys.argv[2])
with dst:
    src.backup(dst)
src.close(); dst.close()
PY
  chown "$APP_USER:$APP_GROUP" "$TARGET_DB"
  chmod 600 "$TARGET_DB"
fi

# main now loads .env for direct manage.py commands; fetch it before running migrations.
runuser -u "$APP_USER" -- git -C "$APP_DIR" fetch --depth 1 origin main
runuser -u "$APP_USER" -- git -C "$APP_DIR" reset --hard origin/main
cd "$APP_DIR"
runuser -u "$APP_USER" -- .venv/bin/python manage.py check
runuser -u "$APP_USER" -- .venv/bin/python manage.py migrate --noinput
runuser -u "$APP_USER" -- .venv/bin/python manage.py collectstatic --noinput
chown "$APP_USER:$APP_GROUP" "$TARGET_DB"
chmod 600 "$TARGET_DB"
systemctl restart "$SERVICE"

for _ in {1..20}; do
  if curl -fsS http://127.0.0.1:8010/healthz/ >/tmp/courier-control-repair-health.json 2>/dev/null; then
    break
  fi
  sleep 1
done
cat /tmp/courier-control-repair-health.json 2>/dev/null || true
echo
curl -fsS http://127.0.0.1:8010/healthz/ >/dev/null || {
  journalctl -u "$SERVICE" -n 100 --no-pager
  echo "Repair did not reach a healthy application state." >&2
  exit 1
}

if has_table "$TARGET_DB" accounts_user; then
  USERS="$(python3 - "$TARGET_DB" <<'PY'
import sqlite3, sys
con=sqlite3.connect(sys.argv[1])
print(con.execute('SELECT COUNT(*) FROM accounts_user').fetchone()[0])
con.close()
PY
)"
else
  USERS=0
fi

echo "SQLite deployment repair complete."
echo "Configured DB: $TARGET_DB"
echo "Users preserved in configured DB: $USERS"
echo "App service: $(systemctl is-active "$SERVICE" 2>/dev/null || true)"
echo "Tunnel service: $(systemctl is-active courier-control-tunnel.service 2>/dev/null || true)"
echo "Courier bot: $(systemctl is-active courier-route-bot.service 2>/dev/null || true)"
