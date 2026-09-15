# Courier Control — Project State

> Постоянная точка передачи контекста. Перед разработкой прочитать этот файл и `ROADMAP.md`, затем проверить актуальный `main` и CI. После каждого крупного блока обновлять.

**Последнее обновление:** 2026-09-15
**Репозиторий:** `Hardoffx/courier-control` · **ветка:** `main`
**Стадия:** функциональный MVP, active development, ещё не production-ready.

## Ключевые решения
Django; Excel-подобный dispatcher UI + mobile courier UI. Цвет строки только оформление. GPS optional. Excel основной вход. Route независим от courier; default courier — постоянный, RouteRun assigned courier — фактический на дату. Weekday/weekend templates независимы.

## Реализовано
- Accounts, DeliveryPoint, Delivery/Event, Route/Template/Item/Run + migrations/tests.
- Courier workflow: Today, maps/call/done/problem/phone/GPS/reorder.
- Dispatcher dashboard by date, filters/stats, RouteRun cards/progress/reassign, daily editor.
- Point directory + canonical matcher: CMD code first, then normalized address/name; canonical address/phone reuse.
- Excel importer service + result report.
- **Excel robustness milestone:** header row automatically selected from first 20 rows, so title/preamble rows above the actual table are supported.
- **Duplicate logic refined:** duplicate fingerprint uses date + canonical point + source label + time window + route order. Re-upload of the same row is skipped, while two legitimate visits to the same lab in different positions/time slots are allowed.
- **Daily exception workflow:** dispatcher can open a RouteRun and add any active canonical point directly to that concrete day with optional time window. It inherits canonical address/phone and actual courier, is appended to route order, creates audit event, and does NOT modify permanent template.
- Tests cover matcher, canonical import, re-import, header below preamble, repeat visits, route generation/re-generation and daily extra point.
- CI was green on previous main (`a7e883e...`). New block CI is running automatically; verify latest head before next work.

## Технический долг / риски
1. Import preview before commit still missing.
2. Theme/indexed Excel fills incomplete.
3. Duplicate fingerprint should be validated against first real management workbook; it intentionally allows same point twice if time/order differs.
4. Fuzzy point matching intentionally absent to avoid false merges.
5. Unique `(code,address)` non-CMD should eventually be revisited.
6. Drag/drop + batch reorder missing.
7. Courier management UI/reserve marker missing.
8. RouteRun status sync and richer completion/problem visibility missing.
9. `views.py`/`route_views.py` still dense and need further service refactor before production.
10. Deployment/pilot infrastructure pending.

## Следующий крупный блок
1. Verify latest CI green; fix if needed.
2. Courier management UI: create/edit/deactivate, phone/login, password reset/change, reserve marker without changing courier role semantics.
3. Drag/drop + batch reorder for template and RouteRun, retaining up/down fallback.
4. Completion/problem detail/history visibility for dispatcher.
5. Then import preview/theme fills and first real Excel validation.
6. Start deployable pilot block: PostgreSQL/Gunicorn/HTTPS/env/health/logging/PWA.

## Протокол «Дальше»
Read `PROJECT_STATE.md` + `ROADMAP.md` → inspect current main/CI → take next large unfinished block → implement autonomously → verify → commit → update state. Не задавать планировочные вопросы без реальной внешней зависимости.
