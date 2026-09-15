# Courier Control — Roadmap

Roadmap отражает порядок разработки, а не обещанные календарные сроки.

## Phase 0 — Foundation
- [x] Django project structure / custom User / Delivery / DeliveryEvent / DeliveryPoint / migrations / PostgreSQL config / CI

## Phase 1 — Daily operational loop
- [x] Dispatcher dashboard, create/edit, single+bulk assignment, search/filter
- [x] Courier Today, done/problem, optional GPS, phone, reorder
- [x] Audit events, independent row colors, core workflow tests

## Phase 2 — Familiar Excel workflow + reference directory
- [x] XLSX upload foundation + column aliases
- [x] Initial row-fill preservation
- [x] Point classification fallback
- [x] DeliveryPoint management UI
- [x] Reliable conservative matching: code/address/name
- [x] Canonical address/phone/type reuse from directory
- [x] Manual corrections are reused by later matching/imports
- [x] Header detection scans first 20 rows instead of requiring row 1
- [ ] Handle theme/indexed fills where practical
- [ ] Import preview before final commit
- [x] Duplicate detection / safe repeated import
- [x] Legitimate repeat visits supported when order/time differs
- [x] Import result summary: created/skipped/warnings/matched/new points

## Phase 2.5 — Persistent courier route memory
- [x] Route independent from courier + default courier
- [x] RouteTemplate weekday/weekend/custom model
- [x] RouteTemplateItem canonical DeliveryPoint
- [x] Order/enabled/time/comment per template item
- [x] Weekday/weekend separation
- [x] Dispatcher template editor
- [x] Enable/disable concrete template points
- [ ] Fast drag-and-drop
- [x] Up/down fallback
- [x] Generate selected day's Delivery rows from template
- [x] Safe re-generation without duplicating completed work
- [x] Actual RouteRun courier can differ from default courier
- [x] Add an extra canonical point directly to one generated day without changing template
- [ ] Learn/update a template from imported/corrected real route
- [x] Core route generation tests

## Phase 3 — Courier and dispatcher usability
- [ ] Courier management UI: create/deactivate/edit/name/phone/login/reset password
- [x] Dispatcher date navigation
- [ ] Copy previous day's route as a starting point
- [ ] Bulk route/order operations
- [ ] Drag/drop route/day ordering
- [ ] Better mobile courier cards + clear next stop
- [ ] Problem reason presets + free comment
- [ ] Dispatcher completion time/GPS/problem details
- [ ] Event/history view per delivery
- [ ] Responsive polish

## Phase 4 — Quality gate
- [x] Role permissions / single assignment / cross-courier protection
- [x] Completion without GPS / reorder / point classification
- [x] Point matching tests
- [x] Excel representative workbook tests including preamble/header detection
- [x] Duplicate/re-import and legitimate repeat-visit tests
- [x] Route template generation/safe refresh tests
- [x] Daily RouteRun extra-point test
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
