# Courier Control — Project State

> Постоянная точка передачи контекста. Перед разработкой прочитать этот файл и `ROADMAP.md`, затем проверить актуальный `main` и CI. После каждого крупного блока обновлять.

**Последнее обновление:** 2026-09-15
**Репозиторий:** `Hardoffx/courier-control`
**Ветка:** `main`
**Стадия:** функциональный MVP в активной разработке, ещё не production-ready.

## Цель и ключевые решения
Django-система для ежедневной курьерской работы. Excel-подобный интерфейс диспетчера + мобильный интерфейс курьера. Цвет строки — только оформление. GPS optional. Excel основной вход MVP. `courier-route-bot` отдельный проект.

### Маршруты и курьеры — разные сущности
Маршрут существует независимо от курьера. `Route.default_courier` — обычный исполнитель, но на конкретный день `RouteRun.assigned_courier` может быть любым активным курьером, включая резервного. Подмена на день не меняет шаблон и default courier. Будний/выходной — независимые варианты маршрута с разным составом, порядком и временем.

## Реализовано
- User dispatcher/courier, DeliveryPoint, Delivery, DeliveryEvent и migrations.
- Dashboard, поиск/фильтры, quick edit, массовое назначение.
- Мобильный маршрут: maps/call/done/problem/phone/GPS/reorder.
- Excel import foundation и UI справочника точек.
- CI + базовые workflow tests.
- Persistent route foundation: Route, RouteTemplate weekday/weekend/custom, RouteTemplateItem, RouteRun, Delivery.route_run, migration 0002.
- `generate_route_run()` безопасно создаёт/обновляет день, не дублирует и сохраняет DONE.
- `reassign_route_run()` меняет исполнителя незавершённых точек без изменения постоянного маршрута.
- Tests на weekday/weekend, default/substitute courier, safe regeneration/completed delivery.
- **Основной UI постоянных маршрутов:**
  - верхняя навигация «Сегодня / Маршруты / Точки / Импорт»;
  - список логических маршрутов с обычным курьером и вариантами;
  - создание/настройка Route; при первом создании автоматически создаются «Будни» и «Выходные»;
  - редактор выбранного шаблона: добавить точку из справочника, включить/выключить по умолчанию, изменить время/комментарий, удалить, поднять/опустить;
  - экран формирования конкретного дня прямо из шаблона: дата, фактический курьер, индивидуальные галочки точек;
  - выбор подменного курьера не меняет default courier;
  - POST endpoint смены курьера существующего RouteRun готов для подключения к dashboard.

## Технический долг / риски
1. Excel import: нужен matcher + canonical autofill + duplicate protection/report.
2. `infer_point_kind()` fallback `МО ...` слишком широкий.
3. Unique `(code,address)` non-CMD пересмотреть после matcher.
4. Quick edit Delivery не синхронизирует справочник.
5. Excel fill parser ограничен.
6. Route editor сейчас имеет up/down, drag/drop ещё не добавлен.
7. На dashboard нужно визуально группировать Delivery по RouteRun и подключить быструю смену курьера всего маршрута.
8. Нужен UI управления курьерами; резервный — метка, не ограничивающая роль.
9. Нужна date navigation и просмотр/редактирование уже сформированного RouteRun.
10. `deliveries/views.py` требует service refactor.
11. Deployment ещё впереди.

## Следующий крупный блок
1. Dashboard RouteRun: группировка сегодняшних точек по маршрутам, фактический курьер, быстрая подмена всего маршрута, статус/progress.
2. Date navigation и редактирование конкретного маршрута дня без изменения шаблона.
3. Улучшить template editor drag/drop + сохранить порядок одним запросом.
4. Затем point_matching + canonical Excel autofill + safe re-import/report.
5. Управление курьерами/резервной меткой.
6. Проверить latest CI до green и добавить UI tests.

## Протокол «Дальше»
Прочитать `PROJECT_STATE.md` + `ROADMAP.md` → проверить `main`/CI → взять следующий крупный блок → реализовать самостоятельно → проверить → commit → обновить state. Работать крупными блоками.
