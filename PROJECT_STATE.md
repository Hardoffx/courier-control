# Courier Control — Project State

> Перед разработкой читать этот файл + `ROADMAP.md`, затем проверять актуальный `main` и CI. После крупного блока обновлять.

**Последнее обновление:** 2026-09-15 · **repo:** `Hardoffx/courier-control` · **branch:** `main`
**Стадия:** функциональный MVP, active development, приближается к deployable pilot.

## Продолжение
В текущем или новом чате команды **`Дальше`** и **`Курьер Бот — продолжай`** означают: прочитать этот файл + ROADMAP, проверить main/CI, самостоятельно взять следующий крупный незавершённый блок, реализовать, протестировать, исправить CI и обновить handoff. Не требовать от пользователя пересказа проекта.

## Архитектурные решения
Django; Excel-like dispatcher UI + mobile courier UI. Цвет строки только оформление. GPS optional. Excel основной вход. Route независим от courier: `default_courier` постоянный, `RouteRun.assigned_courier` фактический. Weekday/weekend независимы. Резервный courier имеет только UX-маркер и может взять любой RouteRun.

## Реализовано
- Accounts, DeliveryPoint, Delivery/Event, Route/Template/Item/Run.
- Dispatcher dashboard/date/filters/stats/assignment/RouteRun; courier management + reserve marker.
- Persistent route memory: weekday/weekend, drag/drop, safe day generation, substitutes, one-off day points, copy previous actual route.
- **Actual route → permanent template learning:** dispatcher explicitly selects which template to update from a corrected RouteRun. Service validates same Route, copies canonical point composition/order/time/comment, enables learned points, removes points absent from that actual day, deduplicates repeated canonical point, and does not touch weekday/weekend/other variants. Nothing learns automatically.
- Mobile courier action-first screen: explicit next stop, navigator/call, done with optional GPS, problem presets+comment, phone, reorder.
- Full dispatcher-only delivery event history.
- Canonical point matching + Excel importer with preamble header detection, duplicate protection, legitimate repeat visits and canonical data reuse.
- Excel two-step preview→confirm, `.xlsx`/5 MB/corrupt-file validation; preview does not write DB.
- CI was green through route-learning UI commit `37eef97...`; route-learning test commit `1a64b719...` was in progress when state was written.

## Технический долг / риски
1. Verify latest route-learning tests CI and fix to green.
2. Excel preview payload currently base64 round-trip in POST; replace with server-side temporary token/storage before production.
3. Theme/indexed Excel fills pending; current RGB palette only.
4. Need first real management XLSX validation.
5. Dense views/services need refactor and broader security review before production.
6. PWA/home-screen/offline shell and deployment/backup/logging/health checks pending.
7. Management statistics/export/demo pending.

## Следующий укрупнённый блок
1. Verify/fix latest CI.
2. Take **deployable pilot foundation** as one large block: production-safe settings/env validation, health endpoint, structured/basic logging, static/WhiteNoise, PostgreSQL/Gunicorn config, Docker/reverse-proxy-friendly files, backup/restore commands/docs, PWA manifest/service-worker/home-screen shell.
3. During that block replace base64 Excel confirmation payload with server-side temporary upload token or another bounded server-side mechanism and add upload security tests.
4. Improve theme/indexed Excel fills if practical without delaying pilot.
5. After code-side pilot readiness, external dependency becomes actual VPS/domain/database credentials; ask only then.
6. Then management statistics/report/export/demo.

## Протокол
`Дальше` → inspect state+roadmap+main+CI → large cohesive unfinished block → implement autonomously → verify → commit → update state. Не задавать планировочных вопросов без внешней зависимости.
