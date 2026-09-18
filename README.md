# Courier Control

MVP системы управления курьерскими доставками: диспетчер создаёт и назначает заявки, курьер видит маршрут на телефоне и отмечает выполнение с временем и GPS.

## Быстрый запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations accounts deliveries
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

После входа суперпользователь попадает в панель диспетчера. Курьеров можно создать через `/admin/`, установив роль `Курьер`.

## Первый сквозной сценарий

1. Создать курьера.
2. В панели диспетчера создать заявку на сегодня и назначить курьера.
3. Войти под курьером: заявка появится в `Мой маршрут`.
4. Нажать `Выполнено`: система запросит геопозицию браузера и сохранит координаты/время, если разрешение выдано.
5. Диспетчер увидит статус `Выполнена`.

SQLite используется для быстрого локального старта. При наличии переменных `POSTGRES_*` приложение автоматически использует PostgreSQL.


## Current product direction

Dispatcher operations are route-centric: the selected day's RouteRun board is the primary surface, with global day KPIs above it and route-specific KPIs/details after opening a route. The flat delivery list remains a secondary search/bulk tool. See [docs/ROUTE_CENTRIC_OPERATIONS.md](docs/ROUTE_CENTRIC_OPERATIONS.md) before changing dispatcher information architecture.
