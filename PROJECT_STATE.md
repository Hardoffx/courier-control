# Courier Control — Project State

> Перед разработкой читать этот файл + `ROADMAP.md`, затем проверять актуальный `main` и CI. После крупного блока обновлять.

**Последнее обновление:** 2026-09-15 · **repo:** `Hardoffx/courier-control` · **branch:** `main`
**Стадия:** code-side management-pitch demo MVP complete; deployment is next external milestone.

## Продолжение
Команды **`Дальше`** и **`Курьер Бот — продолжай`**: прочитать state+roadmap, проверить main/CI, самостоятельно взять следующий крупный блок, реализовать/проверить/починить CI и обновить handoff.

## Решения
Django; Excel-like dispatcher + mobile courier; colors presentation-only; GPS optional; Excel primary input; persistent routes independent from courier; weekday/weekend independent; reserve marker. **SQLite for demo/pilot; PostgreSQL later.**

## Реализовано
- Operational MVP + point directory/import + route templates/runs + courier/dispatcher workflow + history/GPS/problems/copy/learning.
- SQLite deployment foundation, PWA, backup/restore, health, nginx/Gunicorn examples.
- Hardened Excel preview with user-bound expiring one-use server-side staging.
- Management statistics: today/7/30/custom range, overall and per-courier totals/done/problem/rate, daily table, UTF-8 CSV export.
- Repeatable `seed_demo` presentation dataset.
- **Management quality gate added:** tests now verify dispatcher-only stats access, exact total/done/problem/rate calculation, courier denial, Excel-friendly UTF-8 BOM CSV content, and repeatable demo seeding with stable expected counts (4 demo users, 2 routes, 70 deliveries after one or repeated runs).
- CI #110 was green. CI #111 for the new management quality-gate tests started after commit `e1bfcf069ab2f8f071b1e639d8f5b4c68efedfe6` and was in progress at this update.

## Remaining
1. Verify CI #111 and fix if needed.
2. Real management XLSX end-to-end validation; improve theme/indexed fills only if actual file exposes mismatch.
3. Dense views/broader security review are pre-production debt, not demo blocker.
4. SQLite + local staging are intentional single-server pilot choices.

## Следующий этап — внешний dependency
Once CI #111 is green, code-side demo is ready to deploy. Need **actual VPS access/target** and either a domain or explicit IP-only initial demo. Then: install app, persistent SQLite, env/secret, migrate, collectstatic, systemd Gunicorn, nginx, HTTPS if domain, create pilot accounts, smoke-test `/healthz/`, dispatcher, courier, Excel import and PWA.

After deployment, ingest one real management XLSX and do evidence-driven fixes from the actual workflow.

## Протокол
`Дальше` → state+roadmap+main+CI → large cohesive unfinished block → autonomous implementation → verify → update state. Ask user only when external VPS/domain access is genuinely required.
