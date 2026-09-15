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
- [x] Basic upload validation
- [ ] Theme/indexed fills where practical

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

## Phase 4 — Quality gate
- [x] Core role/workflow/import/route tests
- [x] Health/PWA tests
- [ ] Further refactor dense views
- [ ] Broader security review auth/forms/uploads

## Phase 5 — Deployable demo/pilot
- [x] SQLite demo decision; PostgreSQL postponed
- [x] Env hardening, Gunicorn/systemd, nginx, WhiteNoise, health/logging
- [x] SQLite online backup + restore docs
- [x] PWA shell
- [x] Excel confirmation via expiring user-bound server-side staging token
- [ ] Actual VPS/domain/HTTPS deployment
- [ ] Pilot accounts / first real management Excel / feedback fixes

## Phase 6 — Management pitch MVP
- [x] Daily/weekly/custom-range courier statistics
- [x] Completion/problem performance + completion rate
- [x] UTF-8 CSV management report/export
- [x] Idempotent demo-data command / presentation scenario foundation

## Before full production
- [ ] PostgreSQL migration and production concurrency validation
- [ ] Hardened backup/restore and monitoring

## Later / not blocking MVP
OCR in web product; automatic route optimization; continuous tracking; advanced maps/geocoding; Telegram integration; notifications; customer portal; SaaS multi-tenancy; native apps.
