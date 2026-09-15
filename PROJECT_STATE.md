# Courier Control — Project State

> Постоянная точка передачи контекста. Перед разработкой прочитать этот файл и `ROADMAP.md`, затем проверить актуальный `main` и CI. После каждого крупного блока обновлять.

**Последнее обновление:** 2026-09-15
**Репозиторий:** `Hardoffx/courier-control`
**Ветка:** `main`
**Стадия:** функциональный MVP в активной разработке, ещё не production-ready.

## Цель и ключевые решения
Django-система для ежедневной курьерской работы. Excel-подобный интерфейс диспетчера + мобильный интерфейс курьера. Цвет строки — только оформление. GPS optional. Excel основной вход MVP. `courier-route-bot` отдельный проект.

### Маршруты и курьеры
Route существует независимо от курьера. `default_courier` — обычный исполнитель; `RouteRun.assigned_courier` — кто реально едет в дату. Будни/выходные независимы. Подмена и правки RouteRun не меняют шаблон.

## Реализовано
- User dispatcher/courier, DeliveryPoint, Delivery/Event.
- Courier mobile workflow.
- Route/Template/Item/Run foundation + safe generation/reassignment.
- UI постоянных маршрутов и подготовки дня.
- Dashboard по дате и RouteRun: progress, проблемы, быстрая подмена, daily editor, remove/reorder с защитой DONE.
- UI справочника точек.
- **Canonical point matching:**
  - отдельный `point_matching.py`;
  - нормализация регистра/пробелов/пунктуации/ё;
  - CMD сначала ищется по коду независимо от пришедшего адреса;
  - затем exact normalized address, address+name и exact name;
  - найденная точка даёт канонический адрес/телефон;
  - неизвестная точка может быть добавлена в справочник с fallback classification.
- **Safe Excel import service:**
  - логика вынесена из плотного `views.py` в `import_services.py`;
  - импорт сначала использует справочник;
  - канонический адрес/телефон имеют приоритет над грязными значениями Excel;
  - повторная активная точка на ту же дату пропускается вместо дубля;
  - отчёт: создано доставок / распознано / новых справочных точек / пропущено;
  - warnings показывают конкретные строки повторов/неверного порядка;
  - empty workbook получает отдельную ошибку;
  - quick edit теперь также пытается привязать Delivery к canonical DeliveryPoint.
- Добавлены tests: CMD code-first match, canonical address/phone import, safe re-import.
- CI успешно прошёл на подключении нового importer (`78a4e04...`); тестовый commit `c4777e4...` был queued на момент записи state.

## Технический долг / риски
1. Matcher намеренно консервативный: fuzzy matching пока нет, чтобы не склеивать разные лаборатории ошибочно.
2. Unique `(code,address)` для non-CMD всё ещё нужно пересмотреть перед более агрессивным learning.
3. Duplicate rule сейчас `date + canonical point` для незавершённых; при реальном файле проверить случаи, когда одну точку действительно посещают дважды за день.
4. Import preview перед записью ещё нет; сейчас отчёт показывается после безопасного импорта.
5. Excel header detection всё ещё ожидает первую строку заголовков; реальный management XLSX может требовать поиск header row.
6. Theme/indexed Excel colors ещё не обрабатываются полноценно.
7. Daily RouteRun editor пока не добавляет новую точку из справочника.
8. Route template editor: drag/drop + batch save ещё нет.
9. Нужен UI управления курьерами; резервный — метка, не отдельная ограничивающая роль.
10. RouteRun status sync требует доводки.
11. Deployment ещё впереди.

## Следующий крупный блок
1. Проверить новый matcher/import tests в CI и исправить до green.
2. Import preview + более устойчивое обнаружение заголовков реального Excel.
3. Обработать важный сценарий повторного посещения одной точки за день через более точный duplicate fingerprint (route/time/order/source context), не запрещая легитимные повторы.
4. Добавление точки из справочника непосредственно в RouteRun day editor.
5. Drag/drop + batch reorder для template/day.
6. Courier management + reserve marker.
7. Затем pilot/deploy readiness.

## Протокол «Дальше»
Прочитать `PROJECT_STATE.md` + `ROADMAP.md` → проверить `main`/CI → взять следующий крупный незавершённый блок → реализовать самостоятельно → проверить → commit → обновить state. Работать крупными блоками.
