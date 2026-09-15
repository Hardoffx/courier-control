# Courier Control — Project State

> Перед разработкой читать этот файл + `ROADMAP.md`, затем проверять актуальный `main` и CI. После крупного блока обновлять.

**Последнее обновление:** 2026-09-15 · **repo:** `Hardoffx/courier-control` · **branch:** `main`
**Стадия:** функциональный MVP, active development, ещё не production-ready.

## Продолжение
В текущем или новом чате команды **`Дальше`** и **`Курьер Бот — продолжай`** означают: прочитать этот файл + ROADMAP, проверить main/CI, самостоятельно взять следующий крупный незавершённый блок, реализовать, протестировать, исправить CI и обновить handoff. Не требовать от пользователя пересказа проекта.

## Архитектурные решения
Django; Excel-like dispatcher UI + mobile courier UI. Цвет строки только оформление. GPS optional. Excel основной вход. Route независим от courier: `default_courier` постоянный, `RouteRun.assigned_courier` фактический. Weekday/weekend независимы. Резервный courier имеет только UX-маркер и может взять любой RouteRun.

## Реализовано
- Accounts, DeliveryPoint, Delivery/Event, Route/Template/Item/Run.
- Dispatcher dashboard/date/filters/stats/assignment/RouteRun; courier management + reserve marker.
- Persistent route memory: weekday/weekend, drag/drop, safe day generation, substitutes, one-off day points, copy previous actual route.
- Mobile courier action-first screen: explicit next stop, navigator/call, done with optional GPS, problem presets+comment, phone, reorder.
- Full dispatcher-only delivery event history.
- Canonical point matching + Excel importer with preamble header detection, duplicate protection, legitimate repeat visits and canonical data reuse.
- **Excel safety/preview milestone:** `.xlsx` only, 5 MB limit, corrupt workbook error normalization, two-step preview→confirm flow. Preview does not create DeliveryPoint or Delivery rows and shows recognized/new/duplicate rows before commit.
- CI failure from nullable courier rendering in history was diagnosed from Actions logs and fixed (`a047013...`). New preview implementation CI pending at state write time.

## Технический долг / риски
1. Verify latest preview CI and fix to green.
2. Preview payload is currently round-tripped as base64 in POST; acceptable for <=5 MB pilot but production should use server-side temporary storage/session token.
3. Theme/indexed Excel fills pending; current RGB palette only.
4. Need first real management XLSX validation.
5. Learn/update permanent template from imported/corrected real route pending.
6. Dense views/services need refactor and broader security review before production.
7. PWA/home-screen/offline shell and deployment/backup/logging/health checks pending.
8. Management statistics/export/demo pending.

## Следующий укрупнённый блок
1. Verify/fix latest CI.
2. Implement **learn/update template from actual RouteRun** safely: dispatcher explicitly chooses a permanent template; actual route order/points/time become template only after explicit action; protect unrelated template and preserve weekday/weekend independence; tests.
3. Improve Excel color handling where practical and add upload/preview security tests.
4. Then take **deployable pilot** as one large block: production settings, health/logging/static, PWA manifest/service worker shell, PostgreSQL/Gunicorn/reverse-proxy/Docker-friendly setup and deployment docs. External VPS/domain input only when actually needed.
5. Then management statistics/report/demo.

## Протокол
`Дальше` → inspect state+roadmap+main+CI → large cohesive unfinished block → implement autonomously → verify → commit → update state. Не задавать планировочных вопросов без внешней зависимости.
