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
- [ ] Theme/indexed fills where practical
- [ ] Import preview before final commit

## Phase 2.5 — Persistent courier route memory
- [x] Route independent from courier + default courier
- [x] Weekday/weekend/custom templates + canonical points + order/enabled/time/comment
- [x] Dispatcher template editor + enable/disable
- [x] Drag-and-drop ordering + up/down fallback
- [x] Generate day safely + actual courier override + completed-work preservation
- [x] Add one-off canonical point to generated day
- [ ] Learn/update template from imported/corrected real route

## Phase 3 — Courier and dispatcher usability
- [x] Courier management UI: create/edit/deactivate/name/phone/login/password change
- [x] Explicit reserve courier marker («затычка») while retaining normal courier permissions
- [x] Dispatcher date navigation
- [x] Batch/drag ordering for template and generated day
- [x] Dispatcher generated-day completion time/GPS/problem/last-event visibility
- [ ] Copy previous day's route as a starting point
- [ ] Better mobile courier cards + clear next stop
- [ ] Problem reason presets + free comment
- [ ] Full event/history view per delivery
- [ ] Responsive polish

## Phase 4 — Quality gate
- [x] Role/cross-courier/single assignment/completion/reorder/classification baseline
- [x] Point matching + Excel header/duplicate/repeat tests
- [x] Route generation/safe refresh/day extra-point tests
- [x] Courier create/deactivate/reserve tests
- [x] Batch template/day reorder tests
- [ ] Bulk assignment test
- [ ] Completion with GPS test
- [ ] CI green on latest main after each major block
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
