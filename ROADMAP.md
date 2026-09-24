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
- [x] Header detection / duplicate-safe re-import / legitimate repeats
- [x] Import result + non-writing preview
- [x] Preview presentation contract, duplicate prediction and estimated new-point count
- [x] Upload/staging/archive hardening and tests
- [x] Configurable private staging directory via environment
- [ ] Theme/indexed fills where practical; validate need against real management XLSX

## Phase 2.5 — Persistent courier route memory
- [x] Route independent from courier + default courier
- [x] Weekday/weekend/custom templates
- [x] Template editor, drag/drop, safe daily generation, actual courier override
- [x] One-off daily point + explicit actual-route→template learning

## Phase 3 — Courier and dispatcher usability
- [x] Courier management + reserve marker
- [x] Date navigation, ordering, completion/GPS/problem visibility
- [x] Copy previous route
- [x] Mobile next-stop workflow + problem presets
- [x] Full delivery history
- [x] Initial PWA/iPhone shell
- [x] Narrow-phone courier controls and route-template editing hardening

## Phase 3.5 — Approved Design V1
- [x] Shared responsive shell + official visual reference/spec
- [x] Courier list-first route screen and secondary screens
- [x] Dispatcher desktop/mobile dashboard, statistics, import, points, routes, couriers, forms/history
- [x] Yandex Maps-only data contract and persisted point coordinates
- [x] Yandex geocoder service + batch management command
- [x] Retryable transient geocoding + address-change coordinate invalidation
- [x] Courier operational Yandex route map with real coordinates only
- [x] Dispatcher List / Map / Split using the same operational Yandex map component
- [x] Marker ↔ delivery visual focus and status-aware markers
- [x] Lazy/secondary embedded-map loading; configured map language; one API loader per page
- [x] Code-level responsive QA/hardening of critical 375–430 px courier/dispatcher route workflows
- [ ] Live visual/device QA at 375/390/430, tablet, laptop, wide desktop
- [ ] Real API key/domain-restriction acceptance on deployed host

## Phase 3.6 — Route-centric operations (approved 2026-09-18)
- [x] Today: global KPI cards include routes/deliveries/completed/problems
- [x] Today: dense RouteRun card board becomes primary operational surface
- [x] Route cards: courier, progress, remaining, problems, last completed, next stop, attention/completed state
- [x] RouteRun detail: route-specific KPI cards and operational “current state” summary
- [x] Preserve global delivery search/bulk operations as secondary surface
- [x] Add route-board sorting/filtering for scale (attention/progress/courier/name)
- [x] RouteRun events/history presentation
- [x] Staging demo dataset for realistic multi-route visual acceptance
- [ ] Later: route-selected map monitoring with numbered status markers and click details
- [ ] Later: cached coordinates on persistent points; no continuous courier GPS required

See docs/ROUTE_CENTRIC_OPERATIONS.md.

## Phase 3.7 — Courier workspace refinement
- [x] Real selected-point state; initial selection = first unfinished point
- [x] Tap route row to select/expand without forced scroll and without changing route order
- [x] Previous / Next point selection controls
- [x] Prominent assigned route context in courier header
- [x] Selected card includes LPU, phone, time, notes/problem context
- [x] Exact completion time visible where useful; completion GPS optional/non-blocking
- [x] Preserve Done from selected card and expanded unfinished rows
- [x] Preserve compact problem presets + optional comment
- [x] Long-route density QA at 375/390/430 px
- [x] Preserve neighbor-swap reorder invariant; drag handle is optional later enhancement

See docs/COURIER_WORKSPACE.md.

## Phase 4 — Quality gate
- [x] Core role/workflow/import/route tests
- [x] Health/PWA tests
- [x] Map data/geocoding foundation tests
- [x] Lazy map render/secondary behavior tests
- [x] Geocoder success/transient/no-result/address-invalidation tests
- [x] Import staging expiry/one-time/archive-expansion/private-permission tests
- [x] Import preview render/contract tests
- [x] PWA service worker avoids caching login/authenticated operational HTML
- [x] Responsive route-template render contract tests
- [x] Deployment shell syntax validation in CI
- [ ] Further refactor dense views
- [ ] Broader security review auth/forms/uploads

## Phase 5 — Deployable demo/pilot
- [x] SQLite demo decision; PostgreSQL postponed
- [x] Env hardening, Gunicorn/systemd, nginx, WhiteNoise, health/logging
- [x] SQLite online backup + restore docs
- [x] PWA shell with static-only runtime caching
- [x] Excel confirmation via expiring user-bound server-side staging token
- [x] Explicit PILOT_ACCEPTANCE.md gate/checklist
- [x] Pilot env example includes SQLite/staging/Yandex variables
- [x] One-command shared-VPS installer isolated from existing Courier Bot
- [x] Safe shared-VPS update command + dedicated courierctl/systemd/Gunicorn ports
- [x] Temporary pre-domain nginx listener and health smoke-check workflow
- [ ] Execute installer on actual VPS and confirm health
- [ ] Domain + HTTPS + restore drill
- [ ] Yandex credentials/domain restrictions + real coordinate acceptance
- [ ] Pilot accounts / first real management Excel / one real test day / feedback fixes

## Phase 6 — Management pitch MVP
- [x] Daily/weekly/custom-range courier statistics
- [x] Completion/problem performance + completion rate
- [x] UTF-8 CSV management report/export
- [x] Idempotent demo-data command / presentation scenario foundation

## Before full production
- [ ] PostgreSQL migration and production concurrency validation
- [ ] Hardened backup/restore and monitoring

## Later / not blocking MVP
OCR in web product; automatic route optimization; continuous tracking; Telegram integration; notifications; customer portal; SaaS multi-tenancy; native apps.
