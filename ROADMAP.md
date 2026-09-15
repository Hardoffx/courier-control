# Courier Control — Roadmap

Roadmap отражает порядок разработки, а не обещанные календарные сроки. Отмечать выполненные пункты по мере фактической проверки.

## Phase 0 — Foundation

- [x] Django project structure
- [x] Custom User: dispatcher/courier
- [x] Delivery / DeliveryEvent
- [x] DeliveryPoint directory model
- [x] Initial migrations
- [x] Environment-based PostgreSQL configuration
- [x] Basic CI workflow

## Phase 1 — Daily operational loop

Цель: диспетчер может сформировать день, курьер выполнить маршрут, диспетчер увидеть результат.

- [x] Dispatcher daily dashboard
- [x] Create/edit delivery
- [x] Assign courier
- [x] Bulk courier assignment
- [x] Courier mobile Today screen
- [x] Done/problem actions
- [x] Completion timestamp + optional GPS
- [x] Add phone from courier screen
- [x] Reorder remaining route
- [x] Audit events
- [x] Search/filter dispatcher table
- [x] Independent row colors
- [ ] Validate complete loop with automated integration tests

## Phase 2 — Familiar Excel workflow + reference directory

Цель: руководство не меняет привычный способ подготовки маршрута, но данные превращаются в живую систему.

- [x] XLSX upload foundation
- [x] Column aliases
- [x] Initial row-fill preservation
- [x] Initial point classification fallback
- [ ] Dedicated DeliveryPoint management UI outside Django Admin
- [ ] Reliable matching: existing point by code/address/name
- [ ] Auto-fill canonical address/phone/type from directory
- [ ] Explicit correction of incorrectly classified points
- [ ] Learn/reuse corrected mappings on future imports
- [ ] Better Excel header detection for real management files
- [ ] Handle theme/indexed fills where practical
- [ ] Import preview before final commit
- [ ] Duplicate detection / safe repeated import
- [ ] Import result summary: created/skipped/warnings/unmatched

## Phase 3 — Courier and dispatcher usability

- [ ] Courier management UI: create/deactivate/edit/name/phone/login/reset password
- [ ] Dispatcher date navigation: today/tomorrow/previous day
- [ ] Copy previous day's route as a starting point
- [ ] Bulk route/order operations
- [ ] Better mobile courier cards: source/type/time emphasis
- [ ] Clear next-stop visual state
- [ ] Problem reason presets + free comment
- [ ] Dispatcher can see completion time/GPS/problem details
- [ ] Event/history view per delivery
- [ ] Responsive polish for tablet/desktop dispatcher workflow

## Phase 4 — Quality gate

- [ ] Tests: role permissions
- [ ] Tests: assignment and bulk assignment
- [ ] Tests: courier cannot edit another courier's delivery
- [ ] Tests: completion with/without GPS
- [ ] Tests: route reorder and stable numbering
- [ ] Tests: point classification/matching
- [ ] Tests: Excel import representative fixture
- [ ] Tests: duplicate/re-import behavior
- [ ] CI green on `main`
- [ ] Refactor dense views into services/helpers without changing behavior
- [ ] Security review of auth/forms/uploads

## Phase 5 — Deployable pilot

Цель: дать Ивану и 1–2 курьерам реально поработать несколько дней.

- [ ] Production PostgreSQL
- [ ] Gunicorn + reverse proxy
- [ ] HTTPS/domain
- [ ] Production env/secrets
- [ ] Static files verified
- [ ] Create dispatcher account
- [ ] Create pilot courier accounts
- [ ] Backup strategy
- [ ] Error logging
- [ ] Health check
- [ ] Mobile/PWA metadata and home-screen install polish
- [ ] Run first real Excel file end-to-end
- [ ] Pilot feedback fixes

## Phase 6 — Management pitch MVP

- [ ] Daily/weekly courier statistics
- [ ] Completion/problem performance
- [ ] Export/report suitable for management
- [ ] Short product demo scenario
- [ ] Clean seeded/demo environment
- [ ] Explain value: familiar table + live status + audit + courier mobile workflow

## Later / explicitly not blocking MVP

- OCR from screenshots inside the web product
- automatic route optimization
- continuous courier tracking
- advanced maps/geocoding
- Telegram integration with the new backend
- notifications
- customer portal
- billing/SaaS multi-tenancy
- native mobile applications

These should not distract from getting the daily workflow into real use first.
