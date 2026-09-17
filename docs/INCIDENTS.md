# Incident knowledge base

This file records production/deployment incidents that took significant time to diagnose. Keep the symptoms, evidence, false leads, root cause, recovery, and prevention so the same class of failure can be recognized quickly in future projects.

## INC-001 — iOS white screen / navigation stalls after login

**Date:** 2026-09-17  
**Affected origin:** `https://control.routecontrol.ru` (the same class can affect any origin that previously registered a Service Worker)  
**Status:** fixed and guarded against regression.

### Symptoms

- iPhone intermittently showed a blank page or endless navigation.
- Login could render normally and then hang after submitting credentials.
- Safari and Chrome on iOS could both reproduce the symptom.
- Moving the application to another VPS and IP did not eliminate it.
- Server-side health checks and direct curl requests were fast and successful.

### Decisive evidence

Nginx access logging showed a successful completed login request:

```text
POST /login/ HTTP/1.1 302
```

but during a failed navigation there was no subsequent browser `GET /` / dispatcher request. The application therefore completed authentication and returned the redirect; the next navigation was being lost before it reached nginx.

### Cause

Older releases registered `/service-worker.js` with root scope. Service Worker registrations and Cache Storage belong to the web origin, not the VPS IP. Consequently client-side PWA state can survive server migrations and application deployments as long as the origin remains the same.

The exact internal failure mode of the historical iOS registration was not captured, so do not claim that a particular old worker line was proven to intercept authenticated HTML. What was demonstrated experimentally is that retiring the Service Worker, clearing its caches, and preventing re-registration eliminated the failure.

### Permanent architecture decision

Courier Control does **not** use a Service Worker unless offline/PWA behavior becomes an explicit product requirement.

- `base.html` must not call `navigator.serviceWorker.register`.
- `/service-worker.js` remains a retirement endpoint for old clients.
- The retirement worker performs no `fetch` interception, clears Cache Storage, and unregisters itself.
- The retirement endpoint is never HTTP-cached.
- Regression tests enforce these properties.

### Fast diagnostic procedure for future sites

When a browser shows a blank page or stalls after authentication:

1. Verify `/healthz/` and the application locally from the server.
2. Tail nginx access logs while reproducing the issue.
3. If `POST /login/` completes with `302` but the expected next `GET` never reaches nginx, stop changing the database/backend and investigate the browser/client transition.
4. Check whether the origin has ever registered a Service Worker or used Cache Storage/PWA navigation.
5. Remember that changing DNS destination or VPS IP does not change the browser origin and therefore does not remove Service Worker state.
6. Retire/unregister the worker and clear application caches before investigating more invasive server changes.

### False leads encountered

DNS, certificate issuance, nginx proxying, Gunicorn, Django authentication, SQLite, user role configuration, VPS location/IP, and MTU/MSS were investigated. Some packet retransmissions were observed, but they did not establish MTU as the cause. Public DNS and the local server stack were verified healthy.

### If Service Worker support is reintroduced later

Treat it as a separate feature with explicit tests and rollout/rollback design. Never cache login, logout, authenticated operational HTML, or navigation responses by default. Version caches, delete obsolete caches on activation, provide a remotely deployable kill switch/retirement worker, and test upgrades on iOS Safari before production rollout.
