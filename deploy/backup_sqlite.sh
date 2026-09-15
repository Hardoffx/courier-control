#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${APP_DIR:-/opt/courier-control}"
DB="${SQLITE_PATH:-$APP_DIR/db.sqlite3}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
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
printf 'Backup: %s\n' "$OUT"
