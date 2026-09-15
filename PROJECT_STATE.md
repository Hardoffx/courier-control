# Courier Control — Project State

> Перед разработкой читать этот файл + `ROADMAP.md` + `DESIGN_SPEC.md`, затем проверять актуальный `main` и CI. После крупного блока обновлять.

**Последнее обновление:** 2026-09-15 · **repo:** `Hardoffx/courier-control` · **branch:** `main`
**Стадия:** functional demo MVP complete; **approved frontend Design V1 implementation started**.

## Continuation
`Дальше` / `Курьер Бот — продолжай` → read state + roadmap + DESIGN_SPEC, check main/CI, autonomously implement next large cohesive block, verify/fix CI, update handoff. Do not invent a new visual direction.

## Approved frontend source of truth
`DESIGN_SPEC.md` = **Courier Control Design V1 — Minimal + Route Map**, explicitly approved by user on 2026-09-15.
Core contract: minimal list-first workflow + secondary route map; courier mobile-first; dispatcher first-class on desktop/tablet/**phone**; dispatcher modes List / Map / Split (split only where width permits); internal map shows whole-route progress, Yandex Maps remains navigation to one stop. Material design-direction changes require explicit user approval.

## Existing product
Operational Django MVP, Excel import/staging, point directory, persistent routes/templates/runs, courier workflow, dispatcher workflow, GPS/problems/history, management statistics/CSV, repeatable demo seed, SQLite single-server pilot deployment foundation.

## Frontend V1 progress
- [x] `DESIGN_SPEC.md` committed with visual tokens, responsive contract, courier/dispatcher/map behavior, acceptance checklist and change control.
- [x] Shared application shell rebuilt toward V1: white sticky top bar, blue/navy design tokens, desktop dispatcher sidebar, mobile dispatcher drawer, responsive components, courier bottom navigation, safe-area/touch sizing.
- [x] Courier main route screen rebuilt toward approved mockup: dominant blue next-stop card, Yandex/call actions, strong done/problem actions, compact state-aware route list, expandable stop details, mobile bottom Route/Map navigation.
- [x] Courier map section/interaction placeholder established. It is explicitly non-fake; real provider/data integration remains pending.
- [ ] Dispatcher dashboard V1 visual rebuild.
- [ ] Dispatcher mobile delivery-card layout.
- [ ] Dispatcher List / Map / Split interaction and real map provider.
- [ ] Align routes/couriers/points/import/stats secondary screens.
- [ ] Final visual QA.

## Immediate next large block
1. Check CI after frontend shell/courier changes and fix any template regressions.
2. Rebuild **dispatcher dashboard V1**: desktop sidebar-compatible layout, KPI cards, clean filters/table/status chips/courier progress; add responsive phone card presentation without losing actions.
3. Establish List / Map / Split UI controls with honest map placeholder/data contract; real provider integration can follow as its own block.
4. Add/adjust smoke/template tests where useful.

## External deployment
Deployment remains ready after frontend V1 reaches visual acceptance. SQLite/local staging remain intentional for single-server pilot. Real VPS/domain and real management XLSX are still external dependencies, but frontend V1 now intentionally precedes deployment per user approval.
