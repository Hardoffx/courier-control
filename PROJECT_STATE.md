# Courier Control — Project State

Перед разработкой читать этот файл, ROADMAP.md, DESIGN_SPEC.md и PILOT_ACCEPTANCE.md; затем проверять main и CI. После крупного блока обновлять.

Последнее обновление: 2026-09-15. Repo: Hardoffx/courier-control. Branch: main.
Стадия: functional demo MVP complete; Design V1 at pilot acceptance gate.

## Continuation
Дальше / Курьер Бот — продолжай: проверить state, roadmap, design spec, main и CI; автономно реализовать следующий крупный блок; исправить CI; обновить handoff. Не менять утвержденное визуальное направление.

## Source of truth
DESIGN_SPEC.md и design/v1/courier-control-v1-reference.png; design/v1/README.md фиксирует continuity rule. Основной сценарий list-first, карта вторична. Courier mobile-first. Dispatcher полноценно работает desktop/tablet/phone. Встроенная operational карта только Yandex Maps.

## Готово
- Operational Django MVP: Excel import, point directory, routes/templates/runs, courier/dispatcher workflows, GPS, problems, history, stats/CSV, demo seed.
- Design V1 применен к основным и вторичным courier/dispatcher экранам.
- Dispatcher поддерживает List / Map / Split.
- Dispatcher dashboard после map-интеграции снова содержит критичные operational controls: one-day route reassignment, problem visibility, selected courier filter, Today shortcut, phone/call, edit/history и bulk assignment.
- Daily route workspace адаптирован для узких телефонов: add-point form складывается в одну колонку, touch actions не переполняют 375–390 px.
- DeliveryPoint хранит реальные координаты и состояние геокодирования.
- Yandex geocoder и batch command готовы.
- Общий Yandex JS API map component подключен к courier и dispatcher; используются только реальные сохраненные координаты.
- Маркеры учитывают статус, клик по маркеру фокусирует соответствующую доставку.
- Excel staging хранит временные файлы с private permissions и one-time signed token.
- XLSX validation ограничивает исходный файл 5 MB, число ZIP entries и суммарный размер после распаковки.
- Hardening tests покрывают expiry/one-time staging и archive expansion guard.
- Исправлены регрессии point matching и audit event в XLSX import.
- Добавлен PILOT_ACCEPTANCE.md с единым acceptance gate для приложения, карт, реального Excel, устройств, backup/restore и ролей.

## CI
CI #157 успешно прошёл на commit 64b1da9. После него начат следующий UX-polish block; его свежий CI необходимо проверять первым действием следующего продолжения.

## Осталось до pilot acceptance
1. Завершить visual/device QA остальных экранов на 375/390/430, tablet, laptop, wide desktop и исправить найденные UX-проблемы.
2. Реальный VPS/domain/HTTPS и проверка backup/restore по PILOT_ACCEPTANCE.md.
3. Yandex API credentials с domain/referrer restrictions, геокодирование и выборочная проверка реальных адресов.
4. Первый настоящий management XLSX и end-to-end проверка импорта.
5. Реальные pilot accounts и один тестовый рабочий день с фиксацией feedback.

## Архитектурные ограничения
SQLite остается намеренным выбором для single-server pilot; PostgreSQL нужен перед серьезной concurrency/production стадией. Цвет Excel строки остается только представлением и никогда не определяет CMD/INVITRO/статус/бизнес-логику.
