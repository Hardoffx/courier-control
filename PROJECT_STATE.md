# Courier Control — Project State

Перед разработкой читать этот файл, ROADMAP.md, DESIGN_SPEC.md и PILOT_ACCEPTANCE.md; затем проверять main и CI. После крупного блока обновлять.

Последнее обновление: 2026-09-15. Repo: Hardoffx/courier-control. Branch: main.
Стадия: functional MVP complete; internal pilot hardening is nearly complete, remaining acceptance is mostly live/deployment data.

## Continuation
Дальше / Курьер Бот — продолжай: проверить state, roadmap, design spec, main и CI; автономно реализовать следующий крупный блок; исправить CI; обновить handoff. Не менять утвержденное визуальное направление.

## Source of truth
DESIGN_SPEC.md и design/v1/courier-control-v1-reference.png; design/v1/README.md фиксирует continuity rule. Основной сценарий list-first, карта вторична. Courier mobile-first. Dispatcher полноценно работает desktop/tablet/phone. Встроенная operational карта только Yandex Maps.

## Готово
- Operational Django MVP: Excel import, point directory, routes/templates/runs, courier/dispatcher workflows, GPS, problems, history, stats/CSV, demo seed.
- Design V1 применен к основным и вторичным courier/dispatcher экранам.
- Dispatcher List / Map / Split и critical operational controls: one-day route reassignment, problem visibility, courier filter, Today shortcut, phone/call, edit/history, bulk assignment.
- Daily route workspace, courier route screen и постоянный route-template editor адаптированы под узкие 375–430 px сценарии без desktop-only критичных действий.
- На телефоне route-template можно включать/отключать, редактировать время/комментарий, двигать ↑/↓ и удалять без горизонтальной таблицы.
- Excel preview contract восстановлен: реальные row/label/date/match, existing/in-file duplicate prediction и estimate будущих новых точек без записи в БД.
- Excel staging: private 0700/0600, expiring one-time user-bound token, configurable IMPORT_STAGING_DIR.
- XLSX guards: 5 MB source limit, ZIP member count и expanded-size limit.
- DeliveryPoint хранит реальные destination coordinates отдельно от completion GPS.
- Yandex geocoder: batch command, retryable transient errors, explicit no-result failed, forced transient failure сохраняет ранее подтвержденные coordinates, address edit сбрасывает stale coordinates в pending.
- Embedded Yandex map теперь реально secondary/lazy: внешний JS API не загружается при первоначальном list-only сценарии, dispatcher запускает карту при Map/Split, courier — при переходе/прокрутке к карте; один loader promise на страницу.
- YANDEX_MAPS_LANG теперь используется frontend-компонентом.
- Marker → delivery scroll/focus и delivery → marker visual focus работают без подмены destination coordinates.
- PWA service worker больше не кеширует login или authenticated operational HTML; runtime cache ограничен same-origin /static/, старый courier-shell cache удаляется при activate.
- design/v1/README.md и DESIGN_SPEC.md явно закрепляют официальный PNG reference и continuity rule.
- PILOT_ACCEPTANCE.md — единый gate для CI, real XLSX, devices, backup/restore, roles, maps и запуска.
- Аудит старого tests.py replacement выполнен: commit compare показал только точечные +13/-2 изменения, массового удаления тестов не было.

## Tests / CI
- CI #174 green после import/geocoding quality gate.
- CI #178 green для lazy Yandex UI contract.
- CI #179 green после courier narrow-phone polish.
- CI #180 green после mobile route-template editor.
- CI #181 green для responsive operational render contracts.
- CI #183 green после PWA dynamic-cache safety tests.
- После этого обновлены только state/roadmap docs; проверить свежий docs CI первым действием следующего продолжения.

## Осталось до pilot acceptance
1. Live visual/device QA на реальных 375/390/430 px телефонах, tablet, laptop/wide desktop; code-level responsive hardening уже выполнен.
2. Реальный VPS/domain/HTTPS и backup/restore drill по PILOT_ACCEPTANCE.md.
3. Реальные Yandex JS/Geocoder credentials с domain/referrer restrictions, массовое геокодирование и ручная проверка минимум 10 реальных адресов.
4. Первый настоящий management XLSX end-to-end; theme/indexed fills добавлять только если этот файл реально использует их и текущего parser недостаточно.
5. Реальные pilot accounts и один тестовый рабочий день с фиксацией feedback/issues.
6. Перед существенной concurrency/full production — PostgreSQL и production monitoring/backup hardening.

## Архитектурные ограничения
SQLite остаётся намеренным single-server pilot выбором; PostgreSQL нужен перед серьезной concurrency/production стадией. Цвет Excel строки — только representation и никогда не определяет CMD/INVITRO/статус/бизнес-логику. Карта никогда не использует completion GPS как destination coordinates.
