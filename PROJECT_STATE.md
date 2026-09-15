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
- **Persistent route foundation:**
  - `Route`: логический маршрут, default_courier, active, notes.
  - `RouteTemplate`: weekday/weekend/custom варианты.
  - `RouteTemplateItem`: canonical point, порядок, enabled_by_default, типичное time_window/comment.
  - `RouteRun`: конкретная дата + route/template + assigned_courier + status.
  - `Delivery.route_run`: связь фактической точки с маршрутом дня.
  - migration `0002_routes.py`.
  - technical Django Admin для Route/Template/items/Run.
- `route_services.generate_route_run()` создаёт/обновляет маршрут дня из шаблона, использует default courier, canonical point data, не дублирует точки при повторном запуске и не удаляет DONE.
- `route_services.reassign_route_run()` перекидывает незавершённые точки другому курьеру, не меняя Route.default_courier/template.
- Tests добавлены на независимость weekday/weekend, default courier generation, подменного курьера, безопасную повторную генерацию и сохранение completed delivery.

## Технический долг / риски
1. Excel import пока примитивно ищет точки: нужен matcher + canonical autofill + duplicate protection/report.
2. `infer_point_kind()` fallback `МО ...` слишком широкий; справочник должен иметь приоритет.
3. Unique `(code,address)` non-CMD пересмотреть после matcher.
4. Quick edit Delivery не синхронизирует справочник.
5. Excel fill parser ограничен.
6. Нужен основной UI маршрутов/шаблонов/подготовки дня; пока новые Route-модели доступны только технически через Admin/API-код.
7. Нужен UI управления курьерами; «резервный» делать меткой, не ограничивающей ролью.
8. При UI генерации RouteRun обязательно запрещать опасное переформирование завершённых точек; сервис уже сохраняет DONE.
9. `deliveries/views.py` требует постепенного service refactor.
10. Deployment ещё впереди.

## Следующий крупный блок
1. UI «Маршруты»: список Route, default courier, weekday/weekend/custom templates.
2. Редактор RouteTemplate: полный список точек, add/remove(enable), время, порядок, быстрые up/down; затем drag/drop enhancement.
3. UI «Подготовить день»: дата + template + фактический courier → выбрать активные точки → generate RouteRun.
4. UI смены курьера RouteRun одним действием.
5. Затем point_matching + canonical Excel autofill + safe re-import/report.
6. Проверить CI последних route commits и исправить до green.

## Протокол «Дальше»
Прочитать `PROJECT_STATE.md` + `ROADMAP.md` → проверить `main`/CI → взять следующий крупный блок → реализовать самостоятельно → проверить → commit → обновить state. Работать крупными блоками.
