# Courier Control — Project State

> Перед разработкой читать этот файл + `ROADMAP.md`, затем проверять актуальный `main` и CI. После крупного блока обновлять.

**Последнее обновление:** 2026-09-15 · **repo:** `Hardoffx/courier-control` · **branch:** `main`
**Стадия:** code-side management-pitch demo MVP essentially complete; next major dependency is real deployment/pilot input.

## Продолжение
Команды **`Дальше`** и **`Курьер Бот — продолжай`**: прочитать state+roadmap, проверить main/CI, самостоятельно взять следующий крупный блок, реализовать/проверить/починить CI и обновить handoff.

## Решения
Django; Excel-like dispatcher + mobile courier; colors presentation-only; GPS optional; Excel primary input; persistent routes independent from courier; weekday/weekend templates independent; reserve is marker. **SQLite for demo/pilot; PostgreSQL later.**

## Реализовано
- Full operational MVP + canonical point directory/import + route memory/templates/runs + courier/dispatcher UX + history/GPS/problems/copy/learning.
- SQLite pilot deployment foundation + PWA + backup + health + nginx/Gunicorn examples.
- Excel preview hardened with server-side, user-bound, signed, 30-minute, one-use staged token; no workbook base64 round-trip.
- **Management pitch block:** `/dispatcher/stats/` supports today/7/30/custom up to 93 days; overall total/done/problem/completion rate; per-courier performance including reserve marker; daily trend table; UTF-8 semicolon CSV export for Excel; navigation link.
- **Demo presentation data:** `python manage.py seed_demo` creates/updates repeatable demo dispatcher, three couriers, known-looking points, two routes and seven days of deliveries with completed/in-progress/problem examples. Command uses stable demo identifiers and update/get-or-create semantics so rerunning does not intentionally multiply demo data.
- CI #100 and #101 were green before management-pitch commits.

## Риски / remaining code-side work
1. Verify latest management-pitch CI and fix to green.
2. Add explicit tests for stats calculations/export and seed idempotency if not yet present; these are the immediate quality gate.
3. Real management XLSX validation remains important; theme/indexed fills should be improved only from actual evidence.
4. Dense views and broader security review remain pre-production technical debt.
5. Local filesystem staging and SQLite are intentionally single-server pilot choices.

## Следующий укрупнённый блок
1. Verify/fix CI, then add management stats/export/seed tests and any resulting fixes.
2. After green: **deployment becomes the main next step.** Need actual VPS target and either domain or willingness to start by IP. Deploy SQLite demo, HTTPS if domain available, create pilot accounts, run seed only for presentation/demo environment, and perform smoke test.
3. Then ingest one real management XLSX and fix import/UI mismatches from actual workflow.

## Протокол
`Дальше` → state+roadmap+main+CI → large cohesive unfinished block → autonomous implementation → verify → update state. Ask user only when external VPS/domain access is genuinely required.
