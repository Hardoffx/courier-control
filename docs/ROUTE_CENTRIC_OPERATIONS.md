# Route-centric Operations — Product Direction

Status: **APPROVED / next product direction**
Approved: 2026-09-18

## Core model

Courier Control is route-centric. Dispatcher hierarchy:

**daily route (RouteRun) -> assigned courier -> ordered deliveries -> events/problems/history**

A persistent Route/RouteTemplate describes the reusable route. A RouteRun is the operational instance for a concrete date and is the primary unit of monitoring.

## Today dashboard

The dispatcher Today page is a board of today's RouteRuns, not a flat delivery table with routes as secondary metadata.

Global KPI cards summarize the whole selected day: routes, deliveries, completed (+ percent), problems / routes affected.

Below them, RouteRun cards form a dense responsive grid. Each card exposes at a glance: route name; assigned courier or “Не назначен”; completed / total and percent; progress; remaining; problems; last completed stop and exact completion time; next unfinished stop; route state.

Opening a card leads to the full RouteRun workspace.

The flat “Все точки дня” remains for global search, bulk operations and exceptional work, but is secondary to the route board.

## RouteRun workspace

A concrete route page preserves the same visual language as Today but changes context from global to route-specific.

Route KPI cards summarize only this RouteRun: total, completed (+ percent), remaining, problems.

The page also exposes assigned courier, last completed stop/time, next stop, route-order changes and attention items.

Long-term tabs: Overview / Points / Events / History / Map.

Existing route editing, reassignment and import controls remain available.

## Scaling

The UI must remain understandable with 100–200 couriers/routes. Do not assign unique colors to couriers. Route cards and searchable route selection are primary navigation.

Optional sorting/filtering: normal/name, needs attention, progress, courier, completed/in progress.

## Deferred map monitoring

Map monitoring is approved as a later feature, not part of the current implementation block.

Preferred simple model:
- dispatcher selects one RouteRun;
- map shows only that route's delivery markers;
- marker color is delivery status, not courier identity: yellow waiting, green completed, red problem;
- marker contains route-order number;
- click opens delivery details: address, organization/LPU, courier, status, completion/problem time/reason;
- no continuous courier GPS tracking is required.

Coordinates should belong to persistent delivery points and be resolved/cached once where possible. Map visualizes route/delivery state, not proof of courier physical location.

Provider decision is reopened for this future feature: prefer the simplest low-cost interactive option (for example Leaflet + OpenStreetMap) unless deployment constraints dictate otherwise. Do not require paid map APIs merely for visualization.

## UX principles

- Preserve existing UI Forge visual language; evolve, do not redesign from scratch.
- Desktop is deliberately dense; mobile remains first-class.
- Information hierarchy beats decoration.
- Color communicates operational state.
- Do not fake GPS/current courier location.
- Exact server completion timestamp remains authoritative.
- Moving one courier stop must not reorder unrelated stops.
- Global KPIs describe the day; route KPIs describe the selected RouteRun.
