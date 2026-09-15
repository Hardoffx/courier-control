#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR=/opt/courier-control
APP_USER=courierctl
APP_GROUP=courierctl
SERVICE=courier-control.service
NGINX_SITE=/etc/nginx/sites-available/courier-control-pilot
ACME_ROOT=/var/www/courier-control-acme

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/enable_https_sslip.sh" >&2
  exit 1
fi
[[ -d "$APP_DIR/.git" ]] || { echo "Courier Control is not installed at $APP_DIR" >&2; exit 1; }
[[ -f "$NGINX_SITE" ]] || { echo "Courier Control nginx site is missing: $NGINX_SITE" >&2; exit 1; }

log(){ printf '\n==> %s\n' "$*"; }
fail(){ echo "ERROR: $*" >&2; exit 1; }

PUBLIC_IP="${COURIER_CONTROL_IP:-$(curl -4 -fsS --max-time 8 https://api.ipify.org 2>/dev/null || true)}"
[[ "$PUBLIC_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || fail "Could not determine public IPv4 address. Set COURIER_CONTROL_IP and run again."
HOST="${COURIER_CONTROL_DOMAIN:-${PUBLIC_IP//./-}.sslip.io}"

BOT_BEFORE="$(systemctl is-active courier-route-bot.service 2>/dev/null || true)"
BACKUP="$(mktemp /tmp/courier-control-nginx.XXXXXX)"
cp "$NGINX_SITE" "$BACKUP"
FINALIZED=0
cleanup(){
  rc=$?
  if [[ $rc -ne 0 && $FINALIZED -eq 0 ]]; then
    echo "HTTPS setup failed; restoring previous Courier Control nginx site." >&2
    cp "$BACKUP" "$NGINX_SITE" || true
    nginx -t >/dev/null 2>&1 && systemctl reload nginx || true
  fi
  rm -f "$BACKUP"
  exit $rc
}
trap cleanup EXIT

log "Checking temporary hostname $HOST"
for _ in {1..12}; do
  if getent ahostsv4 "$HOST" 2>/dev/null | awk '{print $1}' | grep -Fxq "$PUBLIC_IP"; then break; fi
  sleep 2
done
getent ahostsv4 "$HOST" 2>/dev/null | awk '{print $1}' | grep -Fxq "$PUBLIC_IP" || fail "$HOST does not resolve to $PUBLIC_IP"

log "Installing Certbot"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y certbot
mkdir -p "$ACME_ROOT/.well-known/acme-challenge"
chmod 755 "$ACME_ROOT" "$ACME_ROOT/.well-known" "$ACME_ROOT/.well-known/acme-challenge"

log "Opening ACME challenge only on port 80"
cat > "$NGINX_SITE" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $HOST;

    location ^~ /.well-known/acme-challenge/ {
        root $ACME_ROOT;
        default_type text/plain;
        try_files \$uri =404;
    }

    location / { return 404; }
}

server {
    listen 8088 default_server;
    listen [::]:8088 default_server;
    server_name _;
    client_max_body_size 6m;

    location /static/ {
        alias $APP_DIR/staticfiles/;
        expires 1h;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 5s;
        proxy_read_timeout 65s;
    }
}
EOF
nginx -t
systemctl reload nginx

if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q '^Status: active'; then
  ufw allow 80/tcp >/dev/null
  ufw allow 443/tcp >/dev/null
fi

TEST_TOKEN="courier-control-$(date +%s)"
echo "$TEST_TOKEN" > "$ACME_ROOT/.well-known/acme-challenge/cc-test"
curl -fsS -H "Host: $HOST" http://127.0.0.1/.well-known/acme-challenge/cc-test | grep -Fq "$TEST_TOKEN" || fail "Local ACME webroot check failed"
rm -f "$ACME_ROOT/.well-known/acme-challenge/cc-test"

log "Requesting trusted TLS certificate for $HOST"
certbot certonly \
  --non-interactive \
  --agree-tos \
  --register-unsafely-without-email \
  --webroot \
  --webroot-path "$ACME_ROOT" \
  -d "$HOST"

CERT_DIR="/etc/letsencrypt/live/$HOST"
[[ -s "$CERT_DIR/fullchain.pem" && -s "$CERT_DIR/privkey.pem" ]] || fail "Certificate files were not created"

log "Switching Courier Control to HTTPS"
cat > "$NGINX_SITE" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $HOST;

    location ^~ /.well-known/acme-challenge/ {
        root $ACME_ROOT;
        default_type text/plain;
        try_files \$uri =404;
    }

    location / { return 301 https://$HOST\$request_uri; }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name $HOST;
    client_max_body_size 6m;

    ssl_certificate $CERT_DIR/fullchain.pem;
    ssl_certificate_key $CERT_DIR/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location /static/ {
        alias $APP_DIR/staticfiles/;
        expires 1h;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_connect_timeout 5s;
        proxy_read_timeout 65s;
    }
}
EOF
nginx -t
systemctl reload nginx

log "Updating Django trusted host/origin"
python3 - "$APP_DIR/.env" "$HOST" "$PUBLIC_IP" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1]); host=sys.argv[2]; ip=sys.argv[3]
updates={
    'DJANGO_ALLOWED_HOSTS': f'{host},{ip},127.0.0.1,localhost',
    'DJANGO_CSRF_TRUSTED_ORIGINS': f'https://{host}',
}
lines=path.read_text().splitlines()
seen=set(); out=[]
for line in lines:
    key=line.split('=',1)[0] if '=' in line else None
    if key in updates:
        out.append(f'{key}={updates[key]}'); seen.add(key)
    else:
        out.append(line)
for key,value in updates.items():
    if key not in seen: out.append(f'{key}={value}')
path.write_text('\n'.join(out)+'\n')
PY
chown "$APP_USER:$APP_GROUP" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"
systemctl restart "$SERVICE"

log "Enabling automatic certificate renewal reload"
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'EOF'
#!/usr/bin/env bash
set -e
nginx -t
systemctl reload nginx
EOF
chmod 755 /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
systemctl enable --now certbot.timer >/dev/null 2>&1 || true

log "HTTPS smoke check"
for _ in {1..15}; do
  if curl -fsS "https://$HOST/healthz/" >/tmp/courier-control-https-health.json 2>/dev/null; then break; fi
  sleep 1
done
curl -fsS "https://$HOST/healthz/" || fail "HTTPS health check failed"

if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q '^Status: active'; then
  ufw delete allow 8088/tcp >/dev/null 2>&1 || true
fi

BOT_AFTER="$(systemctl is-active courier-route-bot.service 2>/dev/null || true)"
if [[ -n "$BOT_BEFORE" && "$BOT_BEFORE" != "$BOT_AFTER" ]]; then
  echo "WARNING: courier-route-bot.service state changed: $BOT_BEFORE -> $BOT_AFTER" >&2
else
  echo "Existing courier bot service was not modified."
fi

FINALIZED=1

echo
echo "Courier Control HTTPS is ready."
echo "Web: https://$HOST/"
echo "Health: https://$HOST/healthz/"
echo "Certificate renewal timer: $(systemctl is-active certbot.timer 2>/dev/null || true)"
echo
echo "This sslip.io hostname is suitable for the pilot. A permanent owned domain can replace it later without changing the application architecture."
