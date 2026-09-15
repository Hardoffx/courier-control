# Courier Control — demo/pilot deploy

На пилоте используется **SQLite**. PostgreSQL намеренно отложен до production/существенной параллельной нагрузки.

## Вариант A — VPS, где уже работает Courier Bot

Рекомендуемый путь для текущего пилота. Courier Control ставится изолированно:
- `/opt/courier-control`
- отдельный Linux user `courierctl`
- отдельный systemd service `courier-control.service`
- Gunicorn только на `127.0.0.1:8010`
- временный nginx listener на `:8088`
- существующий `courier-route-bot.service` скрипт не изменяет

На сервере выполнить одну команду:

```bash
curl -fsSL https://raw.githubusercontent.com/Hardoffx/courier-control/main/deploy/install_shared_vps.sh | sudo bash
```

Инсталлятор проверяет занятость портов до установки listener, создаёт private data/staging directories, генерирует production Django secret, запускает migrations/static collection, systemd/nginx и делает два `/healthz/` smoke-check.

Временный `http://SERVER_IP:8088/` предназначен только для проверки доступности до домена. **Не вводить реальные пароли по HTTP.** Следующий шаг — домен + HTTPS, затем pilot accounts и Yandex credentials.

Обновление уже установленного пилота:

```bash
curl -fsSL https://raw.githubusercontent.com/Hardoffx/courier-control/main/deploy/update_shared_vps.sh | sudo bash
```

## Вариант B — отдельный чистый VPS / ручная установка

Приложение: `/opt/courier-control`, venv: `.venv`, база: `/opt/courier-control/data/db.sqlite3`.

Важно: сначала клонировать repository, **потом** создавать `data/backups`; `git clone` нельзя направлять в заранее созданный непустой `/opt/courier-control`.

```bash
sudo apt update && sudo apt install -y python3-venv nginx git
sudo useradd --system --home-dir /opt/courier-control --shell /usr/sbin/nologin courierctl || true
sudo git clone https://github.com/Hardoffx/courier-control.git /opt/courier-control
sudo mkdir -p /opt/courier-control/data /opt/courier-control/backups /opt/courier-control/var/import-staging
sudo chown -R courierctl:courierctl /opt/courier-control
cd /opt/courier-control
sudo -u courierctl python3 -m venv .venv
sudo -u courierctl .venv/bin/pip install -r requirements.txt
sudo -u courierctl cp deploy/.env.example .env
```

Отредактировать `.env`, затем:

```bash
sudo -u courierctl .venv/bin/python manage.py migrate
sudo -u courierctl .venv/bin/python manage.py collectstatic --noinput
sudo cp deploy/courier-control.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now courier-control
```

Для public login сначала настроить nginx по домену и HTTPS. После HTTPS создать dispatcher/superuser и pilot courier accounts.

## Проверка

`/healthz/` должен отвечать `status=ok`, `database=ok`. После HTTPS проверить login, диспетчерский день, импорт Excel и экран курьера с телефона.

## Backup SQLite

`deploy/backup_sqlite.sh` использует SQLite Online Backup API. Восстановление: остановить сервис, сохранить текущую БД отдельно, заменить `data/db.sqlite3` выбранным backup-файлом, проверить владельца `courierctl:courierctl`, запустить сервис и открыть `/healthz/`.

## Ограничение пилота

SQLite подходит для небольшой тестовой группы. Перед серьёзной параллельной эксплуатацией — PostgreSQL и concurrency validation.
