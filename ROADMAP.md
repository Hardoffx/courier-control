# Courier Control — Roadmap

Roadmap отражает порядок разработки, а не обещанные календарные сроки.

## Phase 0 — Foundation
- [x] Django project structure / custom User / Delivery / DeliveryEvent / DeliveryPoint / migrations / PostgreSQL config / CI

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
- [x] Explicitly learn/update one selected template from corrected actual RouteRun without changing other variants

## Phase 3 — Courier and dispatcher usability
- [x] Courier management UI + reserve marker
- [x] Dispatcher date navigation + drag/batch ordering
- [x] Dispatcher completion/GPS/problem visibility
- [x] Copy previous route composition/order into prepared day, preserving today's courier and protecting completed work
- [x] Mobile action-first courier screen with explicit next stop
- [x] Problem reason presets + free comment
- [x] Full event/history view per delivery for dispatcher
- [ ] Further responsive/PWA polish

## Phase 4 — Quality gate
- [x] Role/cross-courier/single assignment/completion/reorder/classification baseline
- [x] Point matching + Excel header/duplicate/repeat/preview-no-write tests
- [x] Route generation/safe refresh/day extra-point tests
- [x] Courier create/deactivate/reserve tests
- [x] Batch template/day reorder tests
- [x] Bulk assignment test
- [x] Completion with GPS test
- [x] Problem preset/history permissions tests
- [x] Route learning isolation/wrong-route safety tests
- [ ] Further refactor dense views
- [ ] Security review auth/forms/uploads

## Phase 5 — Deployable pilot
- [ ] PostgreSQL / Gunicorn / reverse proxy / HTTPS/domain / env+secrets
- [ ] Static files / dispatcher+pilot courier accounts
- [ ] Backup / error logging / health check
- [ ] PWA/home-screen polish
- [ ] First real Excel end-to-end + pilot feedback fixes

## Phase 6 — Management pitch MVP
- [ ] Daily/weekly courier statistics
- [ ] Completion/problem performance
- [ ] Export/report
- [ ] Demo scenario + clean demo environment

## Later / not blocking MVP
OCR in web product; automatic route optimization; continuous tracking; advanced maps/geocoding; Telegram integration; notifications; customer portal; SaaS multi-tenancy; native apps.
