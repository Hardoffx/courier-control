# Courier Control — Project State

> Перед разработкой читать этот файл + `ROADMAP.md`, затем проверять актуальный `main` и CI. После крупного блока обновлять.

**Последнее обновление:** 2026-09-15 · **repo:** `Hardoffx/courier-control` · **branch:** `main`
**Стадия:** functional MVP + SQLite demo deployment foundation; public-demo hardening in progress.

## Продолжение
В текущем или новом чате команды **`Дальше`** и **`Курьер Бот — продолжай`** означают: прочитать этот файл + ROADMAP, проверить main/CI, самостоятельно взять следующий крупный незавершённый блок, реализовать, протестировать, исправить CI и обновить handoff. Не требовать от пользователя пересказа проекта.

## Архитектурные решения
Django; Excel-like dispatcher UI + mobile courier UI. Цвет строки только оформление. GPS optional. Excel основной вход. Route независим от courier. Weekday/weekend независимы. Резервный courier — UX marker. **Demo/pilot uses SQLite; PostgreSQL postponed until production scale.**

## Реализовано
- Operational MVP: directory/deliveries/events/routes/templates/runs, dispatcher/courier UI, reserve couriers, GPS/problem/history, drag/drop, previous-day copy, actual-route→template learning.
- Canonical point matching + Excel preview/import.
- SQLite pilot foundation: env hardening, secure proxy/cookies, WhiteNoise, logging, healthz, PWA shell, Gunicorn/systemd, nginx example, online SQLite backup + deployment doc.
- **Excel public-demo hardening:** browser no longer sends the entire workbook back as base64 on confirm. Preview stores XLSX server-side under random key; browser receives a signed token only. Token is tied to dispatcher user ID, expires after 30 minutes, staged file is consumed once, filename is sanitized to basename, stale staged files are opportunistically cleaned, runtime staging directory is gitignored. Tests cover ownership and one-time consumption.
- CI before this block: run #94 success; #95 pilot-state commit was still running when block started.

## Технический долг / риски
1. Verify latest CI after staged-upload tests and fix to green.
2. Staging uses local filesystem, appropriate for current single-server SQLite demo. If horizontally scaled later, move to shared/object storage.
3. Need actual management XLSX end-to-end validation; theme/indexed fills can be improved from real evidence.
4. Dense views/services refactor and broader auth/form security review remain before production.
5. Service worker intentionally does not cache/sync operational mutations offline.
6. PostgreSQL remains required before serious concurrent production use.
7. Management statistics/export/demo scenario still pending.

## Следующий укрупнённый блок
1. Verify/fix CI.
2. Implement **management pitch block as one stage**: daily/weekly statistics screen, courier totals/done/problem/completion rate, date range controls, simple CSV export/report, navigation, and a safe demo-data management command for quickly populating a presentation environment.
3. Add tests for stats permissions/calculations/export and idempotent demo seed behavior.
4. Then inspect actual VPS/domain target. External deployment becomes the next dependency; ask user for target/credentials only when code-side demo is green.

## Протокол
`Дальше` → inspect state+roadmap+main+CI → large cohesive unfinished block → implement autonomously → verify → commit → update state. Не задавать планировочных вопросов без внешней зависимости.
