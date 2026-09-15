#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR=/opt/courier-control
APP_USER=courierctl
APP_GROUP=courierctl
REPO=https://github.com/Hardoffx/courier-control.git
PUBLIC_PORT=8088
GUNICORN_PORT=8010
SERVICE=courier-control.service
NGINX_SITE=courier-control-pilot

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/install_shared_vps.sh" >&2
  exit 1
fi

log(){ printf '\n==> %s\n' "$*"; }
fail(){ echo "ERROR: $*" >&2; exit 1; }

BOT_BEFORE="$(systemctl is-active courier-route-bot.service 2>/dev/null || true)"

if ss -ltnH 2>/dev/null | awk '{print $4}' | grep -Eq "(^|:)${PUBLIC_PORT}$"; then
  fail "TCP port ${PUBLIC_PORT} is already in use. Nothing was changed on that listener."
fi
if ss -ltnH 2>/dev/null | awk '{print $4}' | grep -Eq "(^|:)${GUNICORN_PORT}$"; then
  fail "TCP port ${GUNICORN_PORT} is already in use. Nothing was changed on that listener."
fi

log "Installing isolated pilot dependencies"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3-venv git nginx curl

if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi

log "Preparing application checkout"
if [[ -e "$APP_DIR" && ! -d "$APP_DIR/.git" ]]; then
  fail "$APP_DIR exists but is not a git checkout; refusing to overwrite it."
fi
if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone --depth 1 --branch main "$REPO" "$APP_DIR"
else
  git -C "$APP_DIR" fetch --depth 1 origin main
  git -C "$APP_DIR" reset --hard origin/main
fi

mkdir -p "$APP_DIR/data" "$APP_DIR/backups" "$APP_DIR/var/import-staging"
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
chmod 700 "$APP_DIR/data" "$APP_DIR/backups" "$APP_DIR/var/import-staging"

log "Creating Python environment"
if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
  runuser -u "$APP_USER" -- python3 -m venv "$APP_DIR/.venv"
fi
runuser -u "$APP_USER" -- "$APP_DIR/.venv/bin/pip" install --upgrade pip
runuser -u "$APP_USER" -- "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [[ ! -f "$APP_DIR/.env" ]]; then
  SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
  [[ -n "$SERVER_IP" ]] || SERVER_IP=127.0.0.1
  SECRET="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"
  cat > "$APP_DIR/.env" <<EOF
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=$SECRET
DJANGO_ALLOWED_HOSTS=$SERVER_IP,127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=
DJANGO_LOG_LEVEL=INFO
SQLITE_PATH=$APP_DIR/data/db.sqlite3
IMPORT_STAGING_DIR=$APP_DIR/var/import-staging
YANDEX_MAPS_JS_API_KEY=
YANDEX_GEOCODER_API_KEY=
YANDEX_MAPS_LANG=ru_RU
EOF
  chown "$APP_USER:$APP_GROUP" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
fi

log "Applying migrations and static files"
cd "$APP_DIR"
runuser -u "$APP_USER" -- .venv/bin/python manage.py check
runuser -u "$APP_USER" -- .venv/bin/python manage.py migrate --noinput
runuser -u "$APP_USER" -- .venv/bin/python manage.py collectstatic --noinput

log "Installing isolated systemd service"
install -m 0644 "$APP_DIR/deploy/courier-control.service" "/etc/systemd/system/$SERVICE"
systemctl daemon-reload
systemctl enable "$SERVICE" >/dev/null
systemctl restart "$SERVICE"

log "Installing temporary nginx listener on :${PUBLIC_PORT}"
install -m 0644 "$APP_DIR/deploy/nginx.shared-vps.conf.example" "/etc/nginx/sites-available/$NGINX_SITE"
ln -sfn "/etc/nginx/sites-available/$NGINX_SITE" "/etc/nginx/sites-enabled/$NGINX_SITE"
nginx -t
systemctl reload nginx

if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q '^Status: active'; then
  ufw allow "${PUBLIC_PORT}/tcp" >/dev/null
fi

log "Smoke checks"
for _ in {1..15}; do
  if curl -fsS "http://127.0.0.1:${GUNICORN_PORT}/healthz/" >/tmp/courier-control-health.json 2>/dev/null; then break; fi
  sleep 1
done
curl -fsS "http://127.0.0.1:${GUNICORN_PORT}/healthz/" || { journalctl -u "$SERVICE" -n 80 --no-pager; fail "Gunicorn health check failed"; }
curl -fsS "http://127.0.0.1:${PUBLIC_PORT}/healthz/" || fail "nginx health check failed"

BOT_AFTER="$(systemctl is-active courier-route-bot.service 2>/dev/null || true)"
if [[ -n "$BOT_BEFORE" && "$BOT_BEFORE" != "$BOT_AFTER" ]]; then
  echo "WARNING: courier-route-bot.service state changed: $BOT_BEFORE -> $BOT_AFTER" >&2
else
  echo "Existing courier bot service was not modified."
fi

SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo
echo "Courier Control pilot is running."
echo "Health: http://${SERVER_IP:-SERVER_IP}:${PUBLIC_PORT}/healthz/"
echo "Temporary web: http://${SERVER_IP:-SERVER_IP}:${PUBLIC_PORT}/"
echo
echo "Do not enter real courier/admin passwords over this temporary HTTP endpoint."
echo "Next stage: attach a domain, enable HTTPS, then create pilot accounts and configure Yandex keys."
