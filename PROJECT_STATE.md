# Courier Control — Project State

> Перед разработкой читать этот файл + `ROADMAP.md` + `DESIGN_SPEC.md`, затем проверять актуальный `main` и CI. После крупного блока обновлять.

**Последнее обновление:** 2026-09-15 · **repo:** `Hardoffx/courier-control` · **branch:** `main`
**Стадия:** functional demo MVP complete; **approved frontend Design V1 implementation active**.

## Continuation
`Дальше` / `Курьер Бот — продолжай` → read state + roadmap + DESIGN_SPEC, check main/CI, autonomously implement next large cohesive block, verify/fix CI, update handoff. Do not invent a new visual direction.

## Approved frontend source of truth
`DESIGN_SPEC.md` = Courier Control Design V1 — Minimal + Route Map. Official visual reference is `design/v1/courier-control-v1-reference.png`. The image controls visual character/composition; DESIGN_SPEC controls behavior and later approved refinements. Core contract: minimal list-first workflow + secondary route map; courier mobile-first; dispatcher first-class on desktop/tablet/phone; dispatcher modes List / Map / Split (split only where width permits); Yandex Maps is the sole embedded operational map provider and also external navigation to one stop. Material design-direction changes require explicit user approval.

## Existing product
Operational Django MVP, Excel import/staging, point directory, persistent routes/templates/runs, courier workflow, dispatcher workflow, GPS/problems/history, management statistics/CSV, repeatable demo seed, SQLite single-server pilot deployment foundation.

## Frontend V1 progress
- [x] DESIGN_SPEC and official PNG visual reference committed.
- [x] Shared V1 application shell: white sticky top bar, blue/navy tokens, desktop dispatcher sidebar, mobile dispatcher drawer, responsive components, courier bottom navigation, safe-area/touch sizing.
- [x] Courier main route screen: dominant next-stop card, Yandex/call actions, done/problem actions, compact route list, expandable stop details, bottom Route/Map navigation.
- [x] Dispatcher dashboard V1 rebuilt: KPI cards, route/courier progress, filters, status chips, bulk assignment, quick editing.
- [x] Dispatcher phone delivery-card layout with key operational controls.
- [x] Dispatcher List / Map / Split controls. Map remains an explicit honest placeholder until Yandex API + real point coordinates/geocoding are connected.
- [x] Statistics screen aligned to V1 with responsive courier results.
- [x] Excel import workflow aligned to V1 with staged 3-step presentation and responsive preview.
- [x] Permanent point directory aligned to V1 with first-class mobile cards.
- [ ] Align routes, route-run detail, courier-management, delivery/point forms and history secondary screens.
- [ ] Real Yandex Maps integration + geocoding/coordinate persistence/data contract.
- [ ] Final visual QA across 375/390/430, tablet, laptop and wide desktop.

## CI
CI #119 passed after dispatcher dashboard rebuild. CI #120 passed after moving the official visual reference into `design/v1/`. Subsequent V1 secondary-screen commits must be verified before the next block.

## Immediate next large block
1. Verify CI for current secondary-screen changes and fix regressions.
2. Align routes, route-run detail and courier-management screens to Design V1, including mobile operational controls.
3. Align delivery/point forms and history.
4. Then implement real Yandex Maps architecture: verify current JS API 3.0 requirements, env-based API key, real coordinates/geocoding only, no fake map data.

## External deployment
Deployment remains ready after frontend V1 reaches visual acceptance. SQLite/local staging remain intentional for single-server pilot. Real VPS/domain, Yandex Maps API key/domain restriction and real management XLSX are external dependencies; frontend V1 intentionally precedes deployment.
