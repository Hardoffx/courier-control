# Courier Workspace — Product Contract

Status: **APPROVED / future implementation contract**
Approved: 2026-09-19

## Goal

The courier screen is a working instrument for one route and one workday. It must be extremely fast on a phone, require minimal taps, and keep the courier oriented in the ordered route.

The courier must always understand:
- which route is assigned;
- overall progress;
- which point is currently selected;
- what was completed previously;
- what comes next;
- whether there are problems;
- what action to take at the selected point.

## Primary screen

Mobile-first hierarchy:

1. Compact header: route name, courier, date, progress.
2. Selected-point card.
3. Ordered route list.
4. Secondary controls/details.

The selected-point card is not permanently synonymous with the first unfinished point. The courier can tap any unfinished route row to select it without changing route order and without an unwanted automatic page scroll.

The initial selection on page load is the first unfinished non-problem point. If all remaining points are problems, select the first unfinished point.

## Selected-point card

Show:
- route order number / total;
- laboratory/source badge and LPU where available;
- full address;
- time window;
- visible phone number;
- comment/important note when present;
- problem state/reason when relevant.

Primary actions:
- Open in Yandex Maps;
- Call;
- Done;
- Problem.

The card should also expose clear Previous / Next navigation through the route without changing order.

Selecting Previous/Next or tapping a route row changes only the UI selection. It does not mutate route_order.

## Completion

Done is available from the selected card and from an expanded unfinished route row.

On completion:
- server writes exact completed_at;
- optional browser geolocation may be submitted when available;
- absence of GPS must never block completion;
- dispatcher sees exact completion time;
- UI advances selection to the next unfinished point after refresh.

Do not introduce a separate “не посещал / пропустил” completion state. If the work for a point is legitimately complete without a physical visit, ordinary Done is sufficient.

GPS is supporting metadata only and must never be presented as proof that the courier physically visited the address.

## Problems

Problem action opens compact presets plus optional comment.

Existing presets remain suitable:
- Нет доступа
- Не принимают
- Получатель недоступен
- Неверный адрес
- Нужно вернуться позже
- Другая проблема

Problem points remain visible and visually distinct. They are not silently treated as completed.

## Route list

The list must remain compact enough for a long route and show at minimum:
- order;
- lab/source + LPU;
- address;
- time/status;
- done/current/problem/upcoming state.

Tap expands details and selects the point, but must not unexpectedly scroll the whole page.

Expanded unfinished point exposes:
- navigation;
- phone/call;
- Done;
- Problem;
- reorder controls;
- add phone when missing.

Completed points show completion state and time where useful, without unnecessary action controls.

## Reordering

Courier may change only the order of unfinished points in their current daily route.

Required invariant: moving one point must not reorder unrelated points.

Current neighbor Up/Down controls are valid. Future UX may add a drag handle, but Up/Down must remain as a reliable touch/accessibility fallback.

Every effective reorder is recorded and remains visible to dispatcher through the existing order-suggestion/comparison flow.

## Route context

The courier screen should display the assigned RouteRun/route name prominently enough that a courier working different routes on different days cannot confuse the context.

If no route or deliveries are assigned, show a clear empty state instead of a broken/blank working surface.

## Map

External Yandex Maps remains the primary driving/navigation action for a selected address.

An embedded whole-route map is secondary and must never make the core route workflow dependent on a paid/slow map API. If retained, it visualizes route progress only.

Continuous courier tracking is not required for the courier workspace.

## Phone UX requirements

Target first: 375 / 390 / 430 px.

- no overlapping/fixed action controls over route content;
- >=44 px primary touch targets;
- two-column actions only where labels remain readable;
- Done should be visually dominant and easy to reach;
- no horizontal page overflow;
- long addresses/phones/comments wrap safely;
- route list stays usable with dozens of points;
- browser back/refresh must not corrupt route state.

## Dispatcher consistency

Courier and dispatcher are two views of the same RouteRun:
- same order;
- same statuses;
- same completion timestamps;
- same problem reasons;
- dispatcher sees courier reorder suggestions.

The courier UI must not maintain a hidden independent copy of operational route state.

## Implementation gaps to close

- [ ] Make “selected point” real client-side/server-compatible state instead of merely renaming next_delivery.
- [ ] Tapping a route row selects it without automatic scrolling.
- [ ] Add Previous / Next controls for selection.
- [ ] Show assigned route name/context in courier header.
- [ ] Show exact completion time on completed route rows where useful.
- [ ] Audit long-route density and 375/390/430 px behavior.
- [ ] Consider drag reorder only after the reliable neighbor-swap workflow is preserved.
- [ ] Keep completion GPS optional and non-blocking.
