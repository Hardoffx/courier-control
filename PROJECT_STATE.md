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
- Dispatcher dashboard содержит critical operational controls: one-day route reassignment, problem visibility, selected courier filter, Today shortcut, phone/call, edit/history и bulk assignment.
- Daily route workspace адаптирован для узких телефонов: add-point form складывается в одну колонку, touch actions не переполняют 375–390 px.
- Excel preview contract восстановлен: таблица предпросмотра получает реальные row/label/date/match данные, показывает существующие и внутрисистемные дубликаты и оценивает будущие новые постоянные точки без записи в БД.
- Import preview screen имеет render-test и мобильную confirmation раскладку.
- Excel staging хранит временные файлы с private permissions и one-time signed token; staging path теперь можно задать через IMPORT_STAGING_DIR environment.
- deploy/.env.example содержит SQLite, staging и Yandex pilot variables.
- XLSX validation ограничивает исходный файл 5 MB, число ZIP entries и суммарный размер после распаковки.
- DeliveryPoint хранит реальные destination coordinates и состояние геокодирования; completion GPS остаётся отдельным.
- Yandex geocoder и batch command готовы; transient transport/payload failures остаются retryable, no-result фиксируется как failed.
- Изменение адреса постоянной точки автоматически очищает старые destination coordinates и возвращает её в pending geocoding.
- Forced transient geocoding не уничтожает ранее подтверждённые координаты.
- Общий Yandex JS API map component подключен к courier и dispatcher; используются только реальные сохраненные координаты.
- Hardening/QA tests покрывают import expiry/one-time/archive expansion, preview contract, geocoder success/transient/no-result, address invalidation и map coordinate order.
- Добавлен PILOT_ACCEPTANCE.md с единым acceptance gate для приложения, карт, реального Excel, устройств, backup/restore и ролей.

## CI
CI #169 успешно прошёл на commit 1ffeb1e после import-preview и geocoding correctness блока. После него добавлена env-конфигурация private staging и отдельный permission test; свежий CI этого хвоста нужно проверить первым действием следующего продолжения.

## Осталось до pilot acceptance
1. Завершить visual/device QA остальных экранов на 375/390/430, tablet, laptop, wide desktop и исправить найденные UX-проблемы.
2. Довести embedded Yandex map до финального secondary/lazy поведения и live-check с реальным ключом/доменом.
3. Реальный VPS/domain/HTTPS и проверка backup/restore по PILOT_ACCEPTANCE.md.
4. Yandex API credentials с domain/referrer restrictions, массовое геокодирование и выборочная проверка реальных адресов.
5. Первый настоящий management XLSX и end-to-end проверка импорта; theme/indexed fill поддерживать только если реально требуется этим файлом.
6. Реальные pilot accounts и один тестовый рабочий день с фиксацией feedback.

## Архитектурные ограничения
SQLite остается намеренным выбором для single-server pilot; PostgreSQL нужен перед серьезной concurrency/production стадией. Цвет Excel строки остается только представлением и никогда не определяет CMD/INVITRO/статус/бизнес-логику.
