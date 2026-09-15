#!/usr/bin/env bash
set -Eeuo pipefail
APP_DIR=/opt/courier-control
APP_USER=courierctl
APP_GROUP=courierctl
SERVICE=courier-control.service

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run as root" >&2
  exit 1
fi
[[ -d "$APP_DIR/.git" ]] || { echo "$APP_DIR is not installed" >&2; exit 1; }
id "$APP_USER" >/dev/null 2>&1 || { echo "$APP_USER user is missing" >&2; exit 1; }

runuser -u "$APP_USER" -- git -C "$APP_DIR" fetch --depth 1 origin main
runuser -u "$APP_USER" -- git -C "$APP_DIR" reset --hard origin/main
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
runuser -u "$APP_USER" -- "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
cd "$APP_DIR"
runuser -u "$APP_USER" -- .venv/bin/python manage.py check
runuser -u "$APP_USER" -- .venv/bin/python manage.py migrate --noinput
runuser -u "$APP_USER" -- .venv/bin/python manage.py shell -c "from accounts.models import User; User.objects.filter(is_superuser=True).update(role=User.Role.DISPATCHER, is_reserve_courier=False)"
runuser -u "$APP_USER" -- .venv/bin/python manage.py collectstatic --noinput
install -m 0644 deploy/courier-control.service "/etc/systemd/system/$SERVICE"
systemctl daemon-reload
systemctl restart "$SERVICE"
nginx -t
systemctl reload nginx
for _ in {1..15}; do
  if curl -fsS http://127.0.0.1:8010/healthz/; then
    echo
    echo "Courier Control updated successfully."
    exit 0
  fi
  sleep 1
done
journalctl -u "$SERVICE" -n 80 --no-pager
exit 1
