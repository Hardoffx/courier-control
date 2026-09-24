#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${APP_DIR:-/opt/courier-control}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"

DB="$(APP_DIR="$APP_DIR" python3 - <<'PY'
from pathlib import Path
import os

app = Path(os.environ["APP_DIR"])
value = os.environ.get("SQLITE_PATH", "").strip()
env_path = app / ".env"
if not value and env_path.is_file():
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, candidate = line.split("=", 1)
        if key.strip() != "SQLITE_PATH":
            continue
        candidate = candidate.strip()
        if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in {'"', "'"}:
            candidate = candidate[1:-1]
        value = candidate
        break

db = Path(value) if value else app / "db.sqlite3"
if not db.is_absolute():
    db = app / db
print(db)
PY
)"

[[ -f "$DB" ]] || { echo "SQLite database not found: $DB" >&2; exit 1; }
mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/courier-$STAMP.sqlite3"
python3 - "$DB" "$OUT" <<'PY'
import sqlite3,sys
src=sqlite3.connect(sys.argv[1]); dst=sqlite3.connect(sys.argv[2])
with dst: src.backup(dst)
dst.close(); src.close()
PY
find "$BACKUP_DIR" -type f -name 'courier-*.sqlite3' -mtime +14 -delete
printf 'Database: %s\nBackup: %s\n' "$DB" "$OUT"
