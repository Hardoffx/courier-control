# Web deployment troubleshooting

Use this order before making speculative infrastructure changes.

## Blank page / endless loading

1. Check application health locally.
2. Check nginx access/error logs while reproducing from the affected device.
3. Identify the last completed HTTP request and status code.
4. If a redirect completes but the next request never arrives, investigate browser state, Service Workers, PWA caches, extensions/content blockers, and the client network before changing backend code.
5. Test a second origin/device/network when possible to isolate the layer.

## Authentication redirects

A successful Django login commonly returns HTTP `302`. Follow the chain request by request. A completed `POST /login/ -> 302` proves the login response completed; it does not prove that the browser successfully performed the next navigation.

## Service Worker / PWA rule

Do not add a Service Worker merely to make a site installable-looking. It is persistent origin-scoped application state and needs its own lifecycle and rollback plan.

For Courier Control the expected state is:

- no Service Worker registration in rendered HTML;
- `/service-worker.js` is retirement-only;
- no `fetch` handler in the retirement worker;
- old Cache Storage entries are deleted;
- the worker unregisters itself;
- the endpoint is served with `no-store` / `no-cache`.

If this architecture changes, update the tests and `docs/INCIDENTS.md` in the same change.

## DNS / VPS migration reminder

Browser origin is based on scheme + hostname + port. Moving a hostname to a new IP/VPS does not create a new origin. Persistent browser state associated with that hostname can therefore survive the migration.

## Isolating the public network path

When Gunicorn and nginx are healthy locally but the public HTTPS origin stalls,
use `deploy/enable_cloudflare_quick_tunnel.sh` as a short-lived control test. It
creates a fresh `trycloudflare.com` HTTPS origin over an outbound tunnel and
rewrites the origin Host header to the configured control portal. This keeps
strict `DOMAIN_SPLIT_ENABLED=1` routing intact.

If the tunnel URL is fast while the normal domain still stalls, do not rewrite
the application. The remaining fault is on the public DNS/TCP/TLS path or in
origin-scoped browser state. Quick Tunnels have no uptime guarantee and are not
a production endpoint; replace the failing path with a managed tunnel or a
healthy VPS/network after the comparison.
