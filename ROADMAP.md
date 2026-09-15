# Courier Control — Roadmap

Roadmap отражает порядок разработки, а не обещанные календарные сроки.

## Phase 0 — Foundation
- [x] Django project structure
- [x] Custom User: dispatcher/courier
- [x] Delivery / DeliveryEvent
- [x] DeliveryPoint directory model
- [x] Initial migrations
- [x] Environment-based PostgreSQL configuration
- [x] Basic CI workflow

## Phase 1 — Daily operational loop
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
- [x] Core automated workflow tests added

## Phase 2 — Familiar Excel workflow + reference directory
- [x] XLSX upload foundation
- [x] Column aliases
- [x] Initial row-fill preservation
- [x] Initial point classification fallback
- [x] Dedicated DeliveryPoint management UI outside Django Admin
- [ ] Reliable matching: existing point by code/address/name
- [ ] Auto-fill canonical address/phone/type from directory
- [x] Explicit manual correction of point type/address/phone in directory
- [ ] Learn/reuse corrected mappings on future imports
- [ ] Better Excel header detection for real management files
- [ ] Handle theme/indexed fills where practical
- [ ] Import preview before final commit
- [ ] Duplicate detection / safe repeated import
- [ ] Import result summary: created/skipped/warnings/unmatched

## Phase 2.5 — Persistent courier route memory
Цель: ежедневный маршрут не собирать с нуля. У каждого курьера есть полный потенциальный маршрут и отдельные варианты по режиму дня.

- [ ] RouteTemplate model owned by courier
- [ ] Template kinds: weekday / weekend / custom
- [ ] RouteTemplateItem references canonical DeliveryPoint
- [ ] Store default order, enabled-by-default and typical time window/overrides per template item
- [ ] Allow same point to have different order/time in weekday and weekend templates
- [ ] Dispatcher template editor showing the courier's full possible route
- [ ] One-click enable/disable points for a concrete day
- [ ] Fast reorder with drag-and-drop
- [ ] Up/down controls as non-JS/mobile fallback
- [ ] Generate a selected day's Delivery rows from template
- [ ] Re-generate/update day safely without duplicating completed work
- [ ] Learn/update a template from an imported or manually corrected real route
- [ ] Tests for weekday/weekend separation and daily generation

## Phase 3 — Courier and dispatcher usability
- [ ] Courier management UI: create/deactivate/edit/name/phone/login/reset password
- [ ] Dispatcher date navigation: today/tomorrow/previous day
- [ ] Copy previous day's route as a starting point
- [ ] Bulk route/order operations
- [ ] Better mobile courier cards: source/type/time emphasis
- [ ] Clear next-stop visual state
- [ ] Problem reason presets + free comment
- [ ] Dispatcher completion time/GPS/problem details
- [ ] Event/history view per delivery
- [ ] Responsive polish

## Phase 4 — Quality gate
- [x] Tests: role permission baseline
- [x] Tests: single assignment
- [x] Tests: courier cannot edit another courier's delivery
- [x] Tests: completion without GPS
- [x] Tests: route reorder and stable numbering
- [x] Tests: point classification baseline
- [ ] Tests: bulk assignment
- [ ] Tests: completion with GPS
- [ ] Tests: point matching
- [ ] Tests: Excel import representative fixture
- [ ] Tests: duplicate/re-import behavior
- [ ] Tests: route template generation and safe refresh
- [ ] CI green on latest `main`
- [ ] Refactor dense views into services/helpers
- [ ] Security review of auth/forms/uploads

## Phase 5 — Deployable pilot
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
- [ ] PWA/home-screen polish
- [ ] First real Excel end-to-end
- [ ] Pilot feedback fixes

## Phase 6 — Management pitch MVP
- [ ] Daily/weekly courier statistics
- [ ] Completion/problem performance
- [ ] Export/report
- [ ] Short demo scenario
- [ ] Clean demo environment

## Later / not blocking MVP
OCR in web product; automatic route optimization; continuous tracking; advanced maps/geocoding; Telegram integration; notifications; customer portal; SaaS multi-tenancy; native apps.
