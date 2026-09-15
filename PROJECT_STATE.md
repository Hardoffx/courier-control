# Courier Control — Project State

Перед разработкой читать этот файл, ROADMAP.md и DESIGN_SPEC.md; затем проверять main и CI. После крупного блока обновлять.

Последнее обновление: 2026-09-15. Repo: Hardoffx/courier-control. Branch: main.
Стадия: functional demo MVP complete; Design V1 nearing pilot acceptance.

## Continuation
Дальше / Курьер Бот — продолжай: проверить state, roadmap, design spec, main и CI; автономно реализовать следующий крупный блок; исправить CI; обновить handoff. Не менять утвержденное визуальное направление.

## Source of truth
DESIGN_SPEC.md и design/v1/courier-control-v1-reference.png. Основной сценарий list-first, карта вторична. Courier mobile-first. Dispatcher полноценно работает desktop/tablet/phone. Встроенная operational карта только Yandex Maps.

## Готово
- Operational Django MVP: Excel import, point directory, routes/templates/runs, courier/dispatcher workflows, GPS, problems, history, stats/CSV, demo seed.
- Design V1 применен к основным и вторичным courier/dispatcher экранам.
- Dispatcher поддерживает List / Map / Split.
- DeliveryPoint хранит реальные координаты и состояние геокодирования.
- Yandex geocoder и batch command готовы.
- Общий Yandex JS API map component подключен к courier и dispatcher; используются только реальные сохраненные координаты.
- Маркеры учитывают статус, клик по маркеру фокусирует соответствующую доставку.
- Dashboard KPI и bulk-selection исправлены.
- Excel staging хранит временные файлы с private permissions и one-time signed token.
- XLSX validation ограничивает исходный файл 5 MB, число ZIP entries и суммарный размер после распаковки для защиты от archive expansion.

## CI
CI 144 и 145 прошли после dispatcher Yandex map и roadmap. CI 146 прошел после hardening staging storage. Текущий XLSX archive guard commit должен быть проверен следующим continuation и исправлен первым при регрессии.

## Осталось до pilot acceptance
1. Проверить последний CI.
2. Финальная visual/device QA на 375/390/430, tablet, laptop, wide desktop и точечная UX-полировка.
3. Добавить/расширить тесты hardening импорта, включая expiry/one-time/archive limits.
4. Подготовить pilot acceptance/deploy checklist.
5. Реальный VPS/domain/HTTPS, Yandex API credentials с domain/referrer restrictions и первый настоящий management XLSX — внешние acceptance dependencies.

## Архитектурные ограничения
SQLite остается намеренным выбором для single-server pilot; PostgreSQL нужен перед серьезной concurrency/production стадией. Цвет Excel строки остается только представлением и никогда не определяет CMD/INVITRO/статус/бизнес-логику.
