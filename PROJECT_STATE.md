# Courier Control — Project State

> Перед разработкой читать этот файл + `ROADMAP.md`, затем проверять актуальный `main` и CI. После крупного блока обновлять.

**Последнее обновление:** 2026-09-15 · **repo:** `Hardoffx/courier-control` · **branch:** `main`
**Стадия:** функциональный MVP, active development, ещё не production-ready.

## Архитектурные решения
Django; Excel-like dispatcher UI + mobile courier UI. Цвет строки только оформление. GPS optional. Excel основной вход. Route независим от courier: `default_courier` постоянный, `RouteRun.assigned_courier` фактический. Weekday/weekend независимы. Резервный курьер остаётся обычным courier по permissions, но имеет `is_reserve_courier` для диспетчерского UX.

## Реализовано
- Accounts, DeliveryPoint, Delivery/Event, Route/Template/Item/Run.
- Courier mobile operational loop.
- Dispatcher dashboard/date/filters/stats/assignment/RouteRun.
- Canonical point directory/matcher and robust Excel importer: preamble header detection, safe fingerprint re-import, repeat visits, result report.
- Persistent route memory: weekday/weekend templates, enable/disable, time/comment, safe day generation, substitute courier, one-off day point.
- **Courier management milestone:**
  - dispatcher nav `Курьеры`;
  - create/edit courier, name/phone/login;
  - set/change password;
  - activate/deactivate without deleting history;
  - explicit `Резерв / затычка` marker;
  - reserve couriers are surfaced first in route assignment selectors and can take any RouteRun without changing permanent owner.
- **Fast route editing milestone:**
  - permanent template rows support mouse drag/drop;
  - generated RouteRun unfinished rows support mouse drag/drop;
  - server-side batch reorder endpoints validate membership and renumber;
  - ↑/↓ remain non-JS fallback;
  - DONE rows are not draggable in generated day.
- **Dispatcher execution visibility:** RouteRun editor shows completion time, problem reason, GPS when available, and latest audit event/actor per delivery.
- Tests added for courier create/reserve/deactivation and template/day batch reorder.
- CI green through drag/drop template commit (`bac70cd...`); newest test commit (`25bba9c...`) was queued when this state was written.

## Технический долг / риски
1. Verify newest tests + migration in latest CI and fix until green.
2. Import preview and theme/indexed fills pending.
3. Need first real management XLSX validation.
4. Fuzzy matching intentionally absent; non-CMD unique constraint eventually revisit.
5. Drag/drop is desktop HTML5; mobile courier already has ↑/↓. Touch drag can be added later if useful.
6. Full event history/detail screen not yet implemented; RouteRun currently shows latest event.
7. Problem presets/mobile next-stop polish pending.
8. Copy previous day / learn template from real route pending.
9. `views.py`/route code still deserves service refactor/security review.
10. Deployment/pilot infrastructure pending.

## Следующий укрупнённый блок
1. Verify latest CI including migration/tests; repair to green.
2. Finish dispatcher/courier operational UX together: problem presets + clear next stop + full delivery event/history + copy previous day.
3. Import preview + improved Excel fills + learn/update template from real imported route where safe.
4. Add missing quality tests (bulk assignment, GPS completion, permissions/security upload cases).
5. Then take deployable pilot as one large block: production settings, PostgreSQL, Gunicorn, static, health/logging, Docker/reverse-proxy-friendly config, PWA shell; actual VPS/domain hookup only when external credentials/target are needed.

## Протокол «Дальше»
Read state+roadmap → inspect main/CI → take a **large cohesive unfinished block** (user explicitly wants fewer «Дальше») → implement autonomously → verify → commit → update state. Не задавать планировочных вопросов без внешней зависимости.
