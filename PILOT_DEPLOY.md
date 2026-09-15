# Courier Control — быстрый demo/pilot deploy

На демонстрационном этапе используется **SQLite**. PostgreSQL намеренно отложен до production/существенной параллельной нагрузки.

## Сервер
Рекомендуется обычный Ubuntu VPS. Приложение: `/opt/courier-control`, venv: `.venv`, база: `/opt/courier-control/data/db.sqlite3`.

## Установка
```bash
sudo apt update && sudo apt install -y python3-venv nginx git
sudo useradd --system --create-home --shell /usr/sbin/nologin courier || true
sudo mkdir -p /opt/courier-control/data /opt/courier-control/backups
sudo chown -R courier:courier /opt/courier-control
sudo -u courier git clone https://github.com/Hardoffx/courier-control.git /opt/courier-control
cd /opt/courier-control
sudo -u courier python3 -m venv .venv
sudo -u courier .venv/bin/pip install -r requirements.txt
sudo -u courier cp deploy/.env.example .env
```

Отредактировать `.env`: секрет, IP/домен и HTTPS origin. Затем:
```bash
sudo -u courier .venv/bin/python manage.py migrate
sudo -u courier .venv/bin/python manage.py collectstatic --noinput
sudo -u courier .venv/bin/python manage.py createsuperuser
sudo cp deploy/courier-control.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now courier-control
```

Настроить nginx по `deploy/nginx.conf.example`. Для публичного пилота добавить HTTPS (например, через certbot) до выдачи логинов курьерам.

## Проверка
`/healthz/` должен отвечать `status=ok`, `database=ok`. Затем проверить login, диспетчерский день, импорт Excel и экран курьера с телефона.

## Backup SQLite
`deploy/backup_sqlite.sh` использует SQLite Online Backup API, а не небезопасное копирование живого файла. Хранит локальные backup-файлы 14 дней. Для ежедневного запуска можно добавить cron/systemd timer.

Восстановление: остановить сервис, сохранить текущую БД отдельно, заменить `data/db.sqlite3` выбранным backup-файлом, проверить владельца `courier:courier`, запустить сервис и открыть `/healthz/`.

## Ограничение пилота
SQLite подходит для демонстрации и небольшой тестовой группы. При переходе к полноценной эксплуатации с заметным числом одновременных записей выполнить миграцию на PostgreSQL. Бизнес-логику под это переписывать не требуется.
