# Courier Control — Project State

Перед разработкой читать этот файл, ROADMAP.md, DESIGN_SPEC.md и PILOT_ACCEPTANCE.md; затем проверять main и CI. После крупного блока обновлять.

Последнее обновление: 2026-09-18. Repo: Hardoffx/courier-control. Branch: main.
Стадия: functional MVP complete; internal pilot hardening complete enough for live deployment/acceptance.

## Continuation
Дальше / Курьер Бот — продолжай: проверить state, roadmap, design spec, main и CI; автономно реализовать следующий крупный блок; исправить CI; обновить handoff. Не менять утвержденное визуальное направление.

## Approved direction 2026-09-18
- RouteRun is now the primary dispatcher operational entity: route -> courier -> ordered deliveries -> events/problems.
- Today becomes a route board: global day KPIs + dense RouteRun cards; flat deliveries are secondary.
- Opening a RouteRun shows route-specific KPIs and full operational detail.
- Deferred monitoring map: select one route, status-colored numbered delivery markers, click for details; no continuous courier GPS. Provider may be Leaflet/OpenStreetMap for simplicity.
- Full dispatcher contract: `docs/ROUTE_CENTRIC_OPERATIONS.md`.
- Courier workspace contract: `docs/COURIER_WORKSPACE.md`: real selected point, row selection without forced scrolling, Previous/Next selection, explicit route context, exact completion time, optional non-blocking GPS, separate reorder semantics.

## Implemented 2026-09-19
- Dispatcher Today is route-centric with global KPIs, dense RouteRun cards, route/courier search, state filtering and sorting.
- RouteRun detail has route KPIs, current state, attention/problem panel, recent event timeline and existing reorder/template controls.
- Courier Today has real selected-point state, Previous/Next selection, explicit route context, notes/problems/phone, exact completion time on completed rows, optional GPS and separate reorder controls.
- Route rows no longer force page scrolling; selection is explicit and never changes route_order.
- Deferred map monitoring and staging demo-data acceptance remain future work.

## Source of truth
DESIGN_SPEC.md, docs/ROUTE_CENTRIC_OPERATIONS.md, docs/COURIER_WORKSPACE.md и design/v1/courier-control-v1-reference.png; design/v1/README.md фиксирует continuity rule. Основной сценарий list-first, карта вторична. Courier mobile-first. Dispatcher полноценно работает desktop/tablet/phone. Встроенная operational карта только Yandex Maps.

## Готово
- Operational Django MVP: Excel import, point directory, routes/templates/runs, courier/dispatcher workflows, GPS, problems, history, stats/CSV, demo seed.
- Design V1 применен к основным и вторичным courier/dispatcher экранам.
- Dispatcher List / Map / Split и critical operational controls: one-day route reassignment, problem visibility, courier filter, Today shortcut, phone/call, edit/history, bulk assignment.
- Daily route workspace, courier route screen и постоянный route-template editor адаптированы под узкие 375–430 px сценарии без desktop-only критичных действий.
- Excel preview contract, staging hardening и XLSX guards закрыты тестами.
- DeliveryPoint/geocoding/Yandex map correctness закрыты foundation + retry/address-invalidation tests.
- Embedded Yandex map secondary/lazy; YANDEX_MAPS_LANG используется; marker↔delivery visual focus работает.
- PWA не кеширует login/authenticated operational HTML; runtime cache ограничен same-origin /static/.
- PILOT_ACCEPTANCE.md — единый gate для CI, real XLSX, devices, backup/restore, roles, maps и запуска.
- Аудит старого tests.py replacement выполнен: массового удаления тестов не было.
- Shared-VPS deploy подготовлен для установки рядом с существующим Courier Bot: отдельный Linux user `courierctl`, `/opt/courier-control`, отдельный systemd service, Gunicorn `127.0.0.1:8010`, временный nginx listener `:8088`; bot service installer не изменяет.
- `deploy/install_shared_vps.sh` выполняет one-command install, private data/staging permissions, production secret, migrations/static, systemd/nginx и local health smoke-checks.
- `deploy/update_shared_vps.sh` выполняет безопасное обновление из canonical main без затрагивания `.env`/persistent data.
- CI теперь выполняет `bash -n deploy/*.sh`; исправлен старый manual-deploy bug с clone в заранее непустой `/opt/courier-control`.

## Tests / CI
- CI #174 green после import/geocoding quality gate.
- CI #178–#183 green для lazy map, responsive operational UI и PWA cache safety.
- CI #185 green на последнем pre-deploy handoff.
- Shared-VPS deploy scripts добавлены после этого; CI #193 уже прошёл shell syntax, Django check и migrations, полный test suite ещё выполнялся на момент handoff. Следующим действием проверить самый свежий CI.

## Осталось до pilot acceptance
1. Фактически выполнить shared-VPS installer и подтвердить local/public `/healthz/`, не используя реальные пароли по временному HTTP endpoint.
2. Привязать домен и включить HTTPS; после этого создать реальные pilot accounts.
3. Настроить реальные Yandex JS/Geocoder credentials с domain/referrer restrictions, массовое геокодирование и ручную проверку минимум 10 реальных адресов.
4. Первый настоящий management XLSX end-to-end; theme/indexed fills добавлять только если этот файл реально требует их.
5. Live visual/device QA на физических телефонах/tablet/desktop и один тестовый рабочий день с фиксацией feedback/issues.
6. Выполнить backup/restore drill по PILOT_ACCEPTANCE.md.
7. Перед существенной concurrency/full production — PostgreSQL и production monitoring/backup hardening.

## Архитектурные ограничения
SQLite остаётся намеренным single-server pilot выбором; PostgreSQL нужен перед серьезной concurrency/production стадией. Цвет Excel строки — только representation и никогда не определяет CMD/INVITRO/статус/бизнес-логику. Карта никогда не использует completion GPS как destination coordinates.
