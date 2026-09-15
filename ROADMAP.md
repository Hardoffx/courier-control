# Courier Control — Roadmap

Roadmap отражает порядок разработки, а не обещанные календарные сроки.

## Phase 0 — Foundation
- [x] Django project structure / custom User / Delivery / DeliveryEvent / DeliveryPoint / migrations / CI

## Phase 1 — Daily operational loop
- [x] Dispatcher dashboard, create/edit, single+bulk assignment, search/filter
- [x] Courier Today, done/problem, optional GPS, phone, reorder
- [x] Audit events, independent row colors, core workflow tests

## Phase 2 — Familiar Excel workflow + reference directory
- [x] XLSX upload + aliases + initial fill preservation
- [x] Point directory + conservative code/address/name matching
- [x] Canonical address/phone/type reuse + corrected mappings reuse
- [x] Header detection scans first 20 rows
- [x] Duplicate detection/safe re-import + legitimate repeat visits
- [x] Import result summary
- [x] Import preview before final commit; preview performs no DB writes
- [x] Basic upload validation (.xlsx, size, corrupt workbook)
- [ ] Theme/indexed fills where practical

## Phase 2.5 — Persistent courier route memory
- [x] Route independent from courier + default courier
- [x] Weekday/weekend/custom templates + canonical points + order/enabled/time/comment
- [x] Dispatcher template editor + enable/disable
- [x] Drag-and-drop ordering + up/down fallback
- [x] Generate day safely + actual courier override + completed-work preservation
- [x] Add one-off canonical point to generated day
- [x] Explicitly learn/update selected template from corrected actual RouteRun

## Phase 3 — Courier and dispatcher usability
- [x] Courier management UI + reserve marker
- [x] Dispatcher date navigation + drag/batch ordering
- [x] Dispatcher completion/GPS/problem visibility
- [x] Copy previous route composition/order into prepared day
- [x] Mobile action-first courier screen with explicit next stop
- [x] Problem reason presets + free comment
- [x] Full event/history view per delivery for dispatcher
- [x] Initial PWA/home-screen shell + iPhone safe-area/mobile input polish

## Phase 4 — Quality gate
- [x] Core role/workflow/import/route tests
- [x] Health/PWA endpoint tests
- [ ] Further refactor dense views
- [ ] Security review auth/forms/uploads

## Phase 5 — Deployable demo/pilot
- [x] Decision: SQLite for demo/pilot; PostgreSQL postponed until production scale
- [x] Production-style env settings while retaining persistent SQLite
- [x] Gunicorn systemd example + nginx reverse-proxy example
- [x] Static files / WhiteNoise
- [x] Health check + console logging
- [x] SQLite online backup script + restore documentation
- [x] PWA manifest/service-worker shell
- [ ] Replace Excel base64 confirmation with server-side temporary token/storage
- [ ] Actual VPS/domain/HTTPS deployment
- [ ] Dispatcher + pilot courier accounts
- [ ] First real Excel end-to-end + pilot feedback fixes

## Phase 6 — Management pitch MVP
- [ ] Daily/weekly courier statistics
- [ ] Completion/problem performance
- [ ] Export/report
- [ ] Demo scenario + clean demo environment

## Before full production
- [ ] PostgreSQL migration and production concurrency validation
- [ ] Hardened backup/restore and monitoring

## Later / not blocking MVP
OCR in web product; automatic route optimization; continuous tracking; advanced maps/geocoding; Telegram integration; notifications; customer portal; SaaS multi-tenancy; native apps.
