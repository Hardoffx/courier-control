# Courier Control Design V1 — Minimal + Route Map

Status: **APPROVED / source of truth for frontend V1**
Approved: 2026-09-15

## Product principle
The primary working surface is deliberately minimal and list-first. The route map is a powerful secondary view, never visual noise. Real frontend must preserve the approved mockup's hierarchy, spacing, status language and interaction model; adapt only where real data/responsive constraints require it.

## Visual language
- Light, clean operational UI; white surfaces on a cool very-light background.
- Deep navy navigation/brand, saturated blue primary action/current state, green done, red problem, amber waiting, neutral gray secondary.
- Rounded 10–14 px controls/cards, restrained shadows/borders, high contrast.
- Large touch targets (>=44 px), compact desktop density, generous mobile spacing.
- No decorative gradients/noisy dashboards. Color communicates state, not business type.
- Row color from imported Excel remains dispatcher annotation only and never affects business logic.

## Courier — mobile first
Default screen is **Маршрут**, not map.
1. Compact app header.
2. Progress (`done / total`).
3. Dominant `Следующая точка` card: order, object/source, address, time, phone.
4. Primary actions: `Открыть в Яндекс Картах`, `Позвонить`.
5. Strong operational actions: green `Выполнено`, red `Проблема`.
6. Compact `Мой маршрут сегодня` list below, with done/current/upcoming/problem states.
7. Bottom navigation includes `Маршрут` and `Карта`; route header also exposes a small map shortcut.
8. `Карта` is an alternate view of the same day's route: completed green, current blue, upcoming neutral, problem red, ordered path. A compact route list remains accessible below/alongside it.
9. Internal route map answers “where am I in the whole route?”; Yandex Maps action answers “how do I drive to this next point?”.
10. Completion confirmation clearly shows time/GPS when available and next-stop CTA. Problem flow uses presets + optional comment.

## Dispatcher / logistician — desktop
Default is **Список**.
- Dark left sidebar: Сегодня, Курьеры, Маршруты, Постоянные точки, Импорт Excel, Статистика/Отчёты; settings/admin only where useful.
- Top bar/date controls and add/import actions.
- KPI cards: total, done, problems, in progress/remaining.
- Search + compact filters.
- Main delivery table is the dominant work surface.
- Clear status chips and fast actions; bulk assignment remains available.
- Courier progress cards/summary visible without overwhelming the delivery table.
- View switch: `Список | Карта | Список + карта`.
- `Список + карта`: list ~65–70%, map ~30–35%; selecting courier/row focuses corresponding route/point and vice versa.

## Dispatcher — phone (mandatory, not fallback)
Dispatcher must be able to control operations fully from a phone.
- Sidebar becomes drawer/menu.
- KPI cards become compact horizontally scrollable/grid cards.
- Desktop table becomes delivery cards optimized for touch.
- Filters open as compact panel/sheet.
- `Список | Карта`; no simultaneous split view on narrow phones.
- Assignment/reassignment, edit, add point, problem inspection, route view, import and statistics remain usable.
- Tablet may use near-desktop layout and split list+map when width permits.

## Responsive targets
Must be intentionally checked at ~375/390/430 px phone widths, tablet ~768–1024 px, laptop ~1280–1440 px and wide desktop. Courier prioritizes phone. Dispatcher must be first-class on phone, tablet and desktop.

## Map implementation contract
Map is lazy/secondary: do not make initial list workflow depend on map loading. V1 may ship visual/map container before provider integration, but production route map must use actual route points/order/status. Never fake route progress as operational data. Provider choice/configuration is implementation detail; external Yandex navigation remains one-stop navigation.

## Visual acceptance checklist
- [ ] Shared V1 design tokens/components
- [ ] Courier next-stop card matches approved hierarchy
- [ ] Courier compact route list/states
- [ ] Courier done/problem flows
- [ ] Courier map mode + route/map navigation
- [ ] Dispatcher desktop shell/sidebar/KPIs
- [ ] Dispatcher delivery table/filter/action hierarchy
- [ ] Dispatcher courier progress summary
- [ ] Dispatcher List/Map/Split control
- [ ] Dispatcher phone card layout and controls
- [ ] Tablet layout
- [ ] Statistics/import/routes/couriers visually aligned to V1
- [ ] PWA safe areas/touch targets
- [ ] Final visual QA against approved mockup direction

## Change control
This file is authoritative for V1. Do not introduce a new visual direction during normal `Дальше` development. Material design-direction changes require explicit user approval. Small responsive/accessibility corrections do not.
