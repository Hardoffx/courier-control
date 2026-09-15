#!/usr/bin/env bash
set -u
HOST="${COURIER_CONTROL_DOMAIN:-78-17-187-5.sslip.io}"
IP="${COURIER_CONTROL_IP:-78.17.187.5}"
printf '\n=== Courier Control HTTPS diagnostics ===\n'
printf 'Host: %s\nIP:   %s\n' "$HOST" "$IP"
printf '\n--- DNS ---\n'
getent ahostsv4 "$HOST" 2>/dev/null | head -n 5 || true
printf '\n--- Listening TCP ports ---\n'
ss -ltnp 2>/dev/null | grep -E ':(80|443|8088|8010|57523)([[:space:]]|$)' || true
printf '\n--- nginx config test ---\n'
nginx -t 2>&1 || true
printf '\n--- UFW ---\n'
if command -v ufw >/dev/null 2>&1; then ufw status verbose 2>&1 || true; else echo 'ufw not installed'; fi
printf '\n--- nftables relevant lines ---\n'
if command -v nft >/dev/null 2>&1; then nft list ruleset 2>/dev/null | grep -E -C 2 'hook input|policy|dport (80|443|8088|57523)|tcp dport' | head -n 180 || true; else echo 'nft not installed'; fi
printf '\n--- iptables INPUT ---\n'
if command -v iptables >/dev/null 2>&1; then iptables -S INPUT 2>&1 | head -n 120 || true; else echo 'iptables not installed'; fi
printf '\n--- Local nginx checks ---\n'
printf '127.0.0.1:8088 health: '
curl -fsS --max-time 5 http://127.0.0.1:8088/healthz/ 2>&1 || true
printf '\n127.0.0.1:80 Host header: '
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' --max-time 5 -H "Host: $HOST" http://127.0.0.1/ 2>&1 || true
printf '\n--- Public-address checks from this VPS (hairpin may be unsupported) ---\n'
printf '%s:8088: ' "$IP"
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' --max-time 7 "http://$IP:8088/healthz/" 2>&1 || true
printf '%s:80: ' "$HOST"
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' --max-time 7 "http://$HOST/" 2>&1 || true
printf '\n--- Services ---\n'
printf 'courier-control: '; systemctl is-active courier-control.service 2>/dev/null || true
printf 'courier bot:     '; systemctl is-active courier-route-bot.service 2>/dev/null || true
printf '\n=== Interpretation ===\n'
printf '%s\n' 'If nginx listens on :80, the local Host-header check returns HTTP, and the local firewall allows 80/443, but Let’s Encrypt times out, the remaining blocker is normally the VPS/provider edge firewall/security group/NAT. Open inbound TCP 80 and 443 in the provider panel, then rerun enable_https_sslip.sh.'
