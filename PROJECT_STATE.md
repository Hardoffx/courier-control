# Courier Control — Project State

> Постоянная точка передачи контекста. Перед разработкой прочитать этот файл и `ROADMAP.md`, затем проверить актуальный `main` и CI. После каждого крупного блока обновлять.

**Последнее обновление:** 2026-09-15
**Репозиторий:** `Hardoffx/courier-control`
**Ветка:** `main`
**Стадия:** функциональный MVP в активной разработке, ещё не production-ready.

## Цель и ключевые решения
Django-система для ежедневной курьерской работы. Excel-подобный интерфейс диспетчера + мобильный интерфейс курьера. Цвет строки — только оформление. GPS optional. Excel основной вход MVP. `courier-route-bot` отдельный проект.

### Маршруты и курьеры — разные сущности
Route существует независимо от курьера. `default_courier` — обычный исполнитель; `RouteRun.assigned_courier` — кто реально едет в конкретную дату. Будни/выходные — независимые шаблоны. Подмена и правки RouteRun не должны менять постоянный шаблон.

## Реализовано
- User dispatcher/courier, DeliveryPoint, Delivery, DeliveryEvent и migrations.
- Мобильный маршрут: maps/call/done/problem/phone/GPS/reorder.
- Excel import foundation и UI справочника точек.
- Route / RouteTemplate weekday-weekend-custom / RouteTemplateItem / RouteRun / Delivery.route_run.
- Safe generate/reassign services + route tests.
- UI постоянных маршрутов: создание, default courier, шаблоны, add/toggle/remove point, время/comment, up/down, формирование дня с выбранным фактическим курьером.
- **Dashboard теперь ориентирован на рабочие маршруты дня:**
  - навигация по датам ← / → и возврат «Сегодня»;
  - карточка каждого RouteRun с progress done/total, проблемами, template kind;
  - быстрая замена фактического курьера всего маршрута прямо из карточки;
  - общая таблица ниже показывает принадлежность точки к RouteRun;
  - отдельный экран RouteRun показывает точки конкретного дня;
  - на RouteRun можно сменить курьера, переставить незавершённые точки вверх/вниз или убрать точку только из этого дня;
  - DONE точки защищены от удаления/перестановки через daily editor;
  - исправлен старый invalid nested-form dashboard: bulk form теперь отдельный, checkboxes используют HTML `form` attribute, quick-edit forms больше не вложены;
  - dashboard filters сохраняют выбранную дату.
- CI успешно проходил на commit с daily route editor (`c60f710...`); последующие UI commits проверяются автоматически.

## Технический долг / риски
1. Excel import: matcher + canonical autofill + duplicate protection/report.
2. `infer_point_kind()` fallback `МО ...` слишком широкий.
3. Unique `(code,address)` non-CMD пересмотреть после matcher.
4. Quick edit Delivery не синхронизирует справочник.
5. Excel fill parser ограничен.
6. Route template editor: добавить drag/drop + batch save.
7. Daily RouteRun editor пока умеет remove/reorder, но не добавляет новую точку из справочника непосредственно в конкретный день.
8. Нужен UI управления курьерами; резервный — метка, не ограничивающая роль.
9. RouteRun status пока не вычисляется/синхронизируется полноценно с Delivery progress.
10. `deliveries/views.py` требует service refactor.
11. Deployment ещё впереди.

## Следующий крупный блок
1. Point matching service: нормализация + code/address/name priority + canonical autofill.
2. Переделать Excel import: match existing points first, safe re-import, duplicate protection, summary/warnings.
3. Quick edit Delivery синхронизировать с canonical point там, где это безопасно.
4. Добавить новую точку из справочника непосредственно в RouteRun day editor.
5. Затем drag/drop template/day order и courier management/reserve marker.
6. UI/integration tests + latest CI green.

## Протокол «Дальше»
Прочитать `PROJECT_STATE.md` + `ROADMAP.md` → проверить `main`/CI → взять следующий крупный незавершённый блок → реализовать самостоятельно → проверить → commit → обновить state. Работать крупными блоками.
