#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR=/opt/courier-control
APP_USER=courierctl
APP_GROUP=courierctl
APP_SERVICE=courier-control.service
TUNNEL_SERVICE=courier-control-tunnel.service
URL_FILE="$APP_DIR/data/quick-tunnel-url.txt"

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/enable_cloudflare_quick_tunnel.sh" >&2
  exit 1
fi
[[ -d "$APP_DIR/.git" ]] || { echo "Courier Control is not installed at $APP_DIR" >&2; exit 1; }
[[ -f "$APP_DIR/.env" ]] || { echo "Missing $APP_DIR/.env" >&2; exit 1; }

log(){ printf '\n==> %s\n' "$*"; }
fail(){ echo "ERROR: $*" >&2; exit 1; }

BOT_BEFORE="$(systemctl is-active courier-route-bot.service 2>/dev/null || true)"

log "Installing cloudflared from Cloudflare package repository"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gpg
mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
cat > /etc/apt/sources.list.d/cloudflared.list <<'EOF'
deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main
EOF
apt-get update
apt-get install -y cloudflared

log "Allowing the temporary trycloudflare.com HTTPS hostname in Django"
python3 - "$APP_DIR/.env" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1])
lines=path.read_text().splitlines()
parsed={}
order=[]
for line in lines:
    if '=' in line and not line.lstrip().startswith('#'):
        key,value=line.split('=',1)
        parsed[key]=value
        order.append(key)

def add_csv(key, value):
    current=[x.strip() for x in parsed.get(key,'').split(',') if x.strip()]
    if value not in current:
        current.append(value)
    parsed[key]=','.join(current)

add_csv('DJANGO_ALLOWED_HOSTS','.trycloudflare.com')
add_csv('DJANGO_CSRF_TRUSTED_ORIGINS','https://*.trycloudflare.com')

seen=set(); out=[]
for line in lines:
    if '=' in line and not line.lstrip().startswith('#'):
        key=line.split('=',1)[0]
        if key in ('DJANGO_ALLOWED_HOSTS','DJANGO_CSRF_TRUSTED_ORIGINS'):
            if key not in seen:
                out.append(f'{key}={parsed[key]}'); seen.add(key)
            continue
    out.append(line)
for key in ('DJANGO_ALLOWED_HOSTS','DJANGO_CSRF_TRUSTED_ORIGINS'):
    if key not in seen:
        out.append(f'{key}={parsed[key]}')
path.write_text('\n'.join(out)+'\n')
PY
chown "$APP_USER:$APP_GROUP" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"
systemctl restart "$APP_SERVICE"

log "Installing persistent Quick Tunnel service"
cat > "/etc/systemd/system/$TUNNEL_SERVICE" <<EOF
[Unit]
Description=Courier Control Cloudflare Quick Tunnel
Wants=network-online.target
After=network-online.target $APP_SERVICE

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
Environment=HOME=$APP_DIR
ExecStart=/usr/bin/cloudflared tunnel --url http://127.0.0.1:8010
Restart=always
RestartSec=5
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable "$TUNNEL_SERVICE" >/dev/null
systemctl restart "$TUNNEL_SERVICE"

log "Waiting for Cloudflare public HTTPS URL"
URL=""
for _ in {1..60}; do
  URL="$(journalctl -u "$TUNNEL_SERVICE" -n 250 --no-pager 2>/dev/null | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -n 1 || true)"
  if [[ -n "$URL" ]]; then
    if curl -fsS --max-time 8 "$URL/healthz/" >/tmp/courier-control-cloudflare-health.json 2>/dev/null; then
      break
    fi
  fi
  sleep 1
  URL=""
done

if [[ -z "$URL" ]]; then
  journalctl -u "$TUNNEL_SERVICE" -n 120 --no-pager || true
  fail "Cloudflare Quick Tunnel did not become healthy. Check outbound connectivity to Cloudflare and rerun this script."
fi

printf '%s\n' "$URL" > "$URL_FILE"
chown "$APP_USER:$APP_GROUP" "$URL_FILE"
chmod 644 "$URL_FILE"

cat > /usr/local/bin/courier-control-url <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
URL="$(journalctl -u courier-control-tunnel.service -n 250 --no-pager 2>/dev/null | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -n 1 || true)"
if [[ -z "$URL" ]]; then
  echo "Quick Tunnel URL not found. Check: systemctl status courier-control-tunnel.service" >&2
  exit 1
fi
echo "$URL"
EOF
chmod 755 /usr/local/bin/courier-control-url

BOT_AFTER="$(systemctl is-active courier-route-bot.service 2>/dev/null || true)"
if [[ -n "$BOT_BEFORE" && "$BOT_BEFORE" != "$BOT_AFTER" ]]; then
  echo "WARNING: courier-route-bot.service state changed: $BOT_BEFORE -> $BOT_AFTER" >&2
else
  echo "Existing courier bot service was not modified."
fi

printf '\nCloudflare Quick Tunnel is ready.\n'
printf 'Web:    %s/\n' "$URL"
printf 'Health: %s/healthz/\n' "$URL"
printf 'Tunnel service: %s\n' "$(systemctl is-active "$TUNNEL_SERVICE" 2>/dev/null || true)"
printf 'App service:    %s\n' "$(systemctl is-active "$APP_SERVICE" 2>/dev/null || true)"
printf '\nCurrent URL later: courier-control-url\n'
printf 'Note: Quick Tunnel is for pilot/testing. Its random trycloudflare.com URL can change when cloudflared restarts.\n'
