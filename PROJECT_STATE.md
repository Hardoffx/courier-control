# Courier Control — Project State

> Перед разработкой читать этот файл + `ROADMAP.md`, затем проверять актуальный `main` и CI. После крупного блока обновлять.

**Последнее обновление:** 2026-09-15 · **repo:** `Hardoffx/courier-control` · **branch:** `main`
**Стадия:** функциональный MVP, demo/pilot deployment foundation готовится.

## Продолжение
В текущем или новом чате команды **`Дальше`** и **`Курьер Бот — продолжай`** означают: прочитать этот файл + ROADMAP, проверить main/CI, самостоятельно взять следующий крупный незавершённый блок, реализовать, протестировать, исправить CI и обновить handoff. Не требовать от пользователя пересказа проекта.

## Архитектурные решения
Django; Excel-like dispatcher UI + mobile courier UI. Цвет строки только оформление. GPS optional. Excel основной вход. Route независим от courier. Weekday/weekend независимы. Резервный courier — UX marker, не отдельная роль.

**Новое решение:** demo/pilot работает на SQLite. PostgreSQL сознательно отложен до полноценного production/существенной параллельной нагрузки. Не тратить время demo-этапа на PostgreSQL.

## Реализовано
- Полный текущий operational MVP: accounts, directory, deliveries/events, routes/templates/runs, dispatcher/courier UI, reserve couriers, GPS/problem/history, drag/drop, previous-day copy, explicit actual-route→template learning.
- Canonical point matching + Excel importer + safe preview→confirm.
- CI перед pilot block был полностью green, включая route-learning tests (run #83 success).
- **SQLite demo deployment foundation:**
  - SQLite is explicit pilot DB with configurable persistent `SQLITE_PATH` and busy timeout;
  - DEBUG-off requires real secret; allowed hosts/CSRF origins/env config added;
  - secure cookies/proxy HTTPS settings for public deployment;
  - WhiteNoise compressed manifest static files;
  - console logging;
  - `/healthz/` checks DB connectivity;
  - PWA manifest + root service worker + standalone/iOS meta/safe-area/mobile input improvements;
  - Gunicorn systemd example and nginx reverse-proxy example;
  - SQLite Online Backup API script with 14-day local retention and restore instructions;
  - `PILOT_DEPLOY.md` provides a short Ubuntu VPS path;
  - tests added for health/manifest/service-worker endpoints.

## Технический долг / риски
1. Verify latest pilot-foundation CI and fix to green.
2. Excel preview still round-trips base64 workbook in POST; replace with bounded server-side temporary storage/token before public pilot.
3. Need actual management XLSX end-to-end validation; theme/indexed fills can be improved then from real evidence.
4. Dense views/services need refactor/security review before production.
5. Service worker intentionally provides only a tiny fallback shell; no offline mutation/data synchronization.
6. SQLite is pilot-only decision; PostgreSQL migration remains required before serious concurrent production use.
7. Management statistics/export/demo scenario pending.

## Следующий укрупнённый блок
1. Verify/fix latest CI.
2. Finish **public demo hardening**: replace base64 Excel confirmation with server-side temporary file/token; ownership+expiry+size controls; cleanup; tests. Add basic security headers/upload tests and improve PWA install shell if CI-safe.
3. Then implement **management pitch block** together: daily/weekly statistics, courier performance/problem counts, CSV/XLSX-style report/export if practical, and seeded/demo-data command so presentation can be populated quickly.
4. After those code blocks, the next external dependency is actual VPS/domain/HTTPS target. Ask user only then; SQLite remains DB for this demo.

## Протокол
`Дальше` → inspect state+roadmap+main+CI → large cohesive unfinished block → implement autonomously → verify → commit → update state. Не задавать планировочных вопросов без внешней зависимости.
