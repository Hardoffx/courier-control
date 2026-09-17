#!/usr/bin/env bash
set -Eeuo pipefail
APP_DIR=/opt/courier-control-staging
BRANCH=${STAGING_BRANCH:-feat/ui-quality-pipeline}
SERVICE=courier-control-staging.service

[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root" >&2; exit 1; }
[[ -d "$APP_DIR/.git" ]] || { echo "$APP_DIR is not installed" >&2; exit 1; }

runuser -u courierctl -- git -C "$APP_DIR" fetch origin "$BRANCH"
runuser -u courierctl -- git -C "$APP_DIR" reset --hard FETCH_HEAD
runuser -u courierctl -- "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
cd "$APP_DIR"
runuser -u courierctl -- .venv/bin/python manage.py check
runuser -u courierctl -- .venv/bin/python manage.py migrate --noinput
runuser -u courierctl -- .venv/bin/python manage.py collectstatic --noinput
install -m 0644 deploy/courier-control-staging.service /etc/systemd/system/$SERVICE
systemctl daemon-reload
systemctl restart "$SERVICE"

for _ in {1..15}; do
  curl -fsS http://127.0.0.1:8011/healthz/ && { echo; echo "Staging updated: $BRANCH"; exit 0; }
  sleep 1
done
journalctl -u "$SERVICE" -n 80 --no-pager
exit 1
