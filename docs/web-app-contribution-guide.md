# Web App Contribution Guide

This guide explains how to contribute code to the React/Vite web app in `web-app`.
It assumes you have never worked on this app before.

The web app is the browser dashboard for the AGV project. It does not control the
robot directly. It reads files produced by the controller, exposes them through
small Vite API routes, and renders them as dashboard pages, maps, tables, image
feeds, and goal-order controls.

## Brief summary

1. Work inside `web-app` for the React dashboard.
2. Use `npm run dev` from `web-app` to run the local app.
3. Use `npm run build` from `web-app` after code changes.
4. Start from `web-app/src/App.tsx` for page layout, routing, dashboard cards,
   fleet status, logs, help, and shared UI components.
5. Start from `web-app/src/App.css` for visual layout, spacing, grid behavior,
   card sizing, responsive behavior, and the dark command-center theme.
6. Start from `web-app/vite.config.ts` for local API routes such as
   `/api/realtime-panel`, `/api/camera-feed`, `/api/local-planner-grid`,
   `/api/goals`, `/api/simulations`, `/api/events`, and
   `/api/event-telemetry`.
7. Start from `web-app/src/data.ts` and `web-app/src/SimulationTable.tsx` for
   simulation, event, and event-telemetry table behavior.
8. Start from `web-app/src/LiveMap.tsx`, `web-app/src/mapData.ts`, and
   `web-app/src/types.ts` for map rendering and realtime robot data shape.
9. Start from `web-app/src/goals.ts` and `web-app/src/goals.config.json` for
   dashboard goal-order loading, movement, and persistence.
10. Do not edit `web-app/node_modules` or `web-app/dist` by hand.
11. Do not use `web-app/app.py` for the active React app. It is the old
    Streamlit dashboard, not the current React/Vite surface.

## Mental model

The web app has three layers:

1. Controller output files:
   The Webots controller writes runtime files under `logging/logs`, including
   realtime telemetry, camera images, planner images, simulations, events, and
   event telemetry.

2. Vite API routes:
   `web-app/vite.config.ts` reads those files and serves them to the React app
   through `/api/...` endpoints during local development.

3. React UI:
   Files in `web-app/src` fetch those endpoints, store the current values in
   React state, and render the dashboard pages.

The most common contribution flow is:

1. Identify the visible feature you want to change.
2. Find the React page or component in `App.tsx`, `LiveMap.tsx`, or
   `SimulationTable.tsx`.
3. Check whether the data shape comes from `types.ts`, `data.ts`, `goals.ts`, or
   a Vite endpoint in `vite.config.ts`.
4. Make the smallest change that preserves the existing data source.
5. Update CSS in `App.css` if the change affects layout or styling.
6. Run `npm run build`.

## Commands

Run these from `web-app`:

```bash
npm run dev
npm run build
npm run preview
```

Use `npm run dev` while developing. Use `npm run build` as the standard
regression check after changing React, TypeScript, Vite routes, CSS, or package
metadata. Use `npm run preview` only when you specifically want to inspect the
production build locally.

## Main app files

### `web-app/src/App.tsx`

This is the central React file. Start here for most UI changes.

It contains:

- Route setup for `/`, `/map`, `/fleet`, `/logs`, `/help`, `/support`,
  `/tables`, and the fallback route.
- The application shell: top bar, sidebar, mobile nav, and content area.
- Shared UI components such as `Panel`, `MetricCard`, `MetricGroupCard`,
  `StatusPill`, `LiveImage`, `GoalOrder`, `PageHeader`, and `LoadingPanel`.
- The dashboard page.
- The map page wrapper and map toolbar.
- The fleet status page.
- The log analysis page and simple line chart.
- The help page.
- React hooks for realtime robot data, simulation table data, goal ordering,
  and README loading.

Use this file when you want to:

- Add, remove, or rename a page.
- Add or remove a navigation link.
- Change dashboard cards.
- Change `Realtime Telemetry` grouping.
- Change the fleet status layout.
- Change what image feeds appear.
- Change log-analysis metric cards or charts.
- Change the help page cards.
- Change how often frontend polling happens.

How to add a new page:

1. Create a new page function in `App.tsx`, following the existing page
   functions such as `DashboardPage`, `MapPage`, or `FleetPage`.
2. Add a route in the `<Routes>` block.
3. If it should appear in navigation, add an entry to `navItems`.
4. Add CSS classes in `App.css` only for layout or visual differences.

How to modify the dashboard:

1. Edit `DashboardPage`.
2. Keep the top summary metrics in the `metric-grid metric-grid-top` section.
3. Keep map and image feeds in the `dashboard-grid` section.
4. Keep telemetry categories in the `Realtime Telemetry` panel.
5. If the new value comes from realtime telemetry, first verify it exists in
   `RobotData` in `types.ts`.

How to modify goal ordering:

1. Edit the `GoalOrder` component for UI behavior.
2. Edit `useGoalOrder` for loading and saving behavior.
3. Edit `goals.ts` for reorder logic or API helpers.
4. Edit `vite.config.ts` if persistence endpoint behavior changes.
5. Preserve the full `Goals` payload shape unless you also update the
   controller-side reader.

Important caution:

- Do not move API behavior into `web-app/app.py`. The active React app uses Vite
  middleware in `vite.config.ts`.
- Do not change `RobotData` usage in `App.tsx` without also checking
  `types.ts` and the controller JSON payload.
- Do not add a large new abstraction just to change one card. Existing patterns
  are intentionally simple.

### `web-app/src/App.css`

This is the main stylesheet for the current React app.

It contains:

- Global color variables.
- Top bar, sidebar, mobile navigation, and page layout styles.
- Panel and card styling.
- Dashboard, fleet, map, log, help, and table layout styles.
- Live map styling, including SVG markers and legend styles.
- Goal-order styling.
- Telemetry category styling.
- Responsive behavior through media queries.

Use this file when you want to:

- Change spacing, grid layout, widths, or card sizes.
- Change colors, borders, typography, or backgrounds.
- Fix overlap, clipping, wrapping, or mobile layout.
- Adjust map legend placement or marker visuals.
- Change dashboard/fleet/log/help visual behavior without changing data.

How to work safely in this file:

1. Search for the specific component class first.
2. Prefer adding a narrow class for the feature you are changing.
3. Check the media queries at the bottom when layout changes affect smaller
   screens.
4. Keep cards compact and avoid nested card designs unless the existing local
   pattern already does it.
5. Keep color changes aligned with the current dark industrial theme.

Important classes to know:

- `.command-center`, `.topbar`, `.sidebar`, `.content-shell`
- `.page`, `.page-header`, `.panel`, `.panel-heading`
- `.metric-grid`, `.metric-card`, `.metric-group-card`, `.metric-subgrid`
- `.dashboard-grid`, `.dashboard-map-panel`, `.dashboard-feeds`
- `.telemetry-category-grid`, `.telemetry-category`,
  `.telemetry-category-metrics`
- `.map-shell`, `.live-map`, `.map-legend`
- `.goal-order-card`, `.goal-order-list`, `.goal-order-item`
- `.unit-card`, `.unit-card-grid`, `.unit-small-card`, `.unit-error-card`
- `.simulation-table-section`, `.data-table`

### `web-app/vite.config.ts`

This file configures Vite and defines the local API routes used by the React app.
For this project, it is both build configuration and a lightweight development
server backend.

It reads runtime files from:

```text
logging/logs
```

It currently serves:

- `/api/realtime-panel` from `robot_controller_runs_realtime_panel.jsonl`
- `/api/local-planner-grid` from `local_planner_grid.jpg`
- `/api/camera-feed` from `camera_feed.jpg`
- `/api/simulations` from `simulations.jsonl`
- `/api/events` from `events.jsonl`
- `/api/event-telemetry` from `event_telemetry.jsonl`
- `/api/goals` from `web-app/src/goals.config.json`
- `/api/readme` from root `README.md`

Use this file when you want to:

- Add a new `/api/...` endpoint for the React app.
- Change where the app reads runtime files from.
- Change how image files are served.
- Change how JSONL files are served.
- Change goal persistence validation or saving behavior.

How to add a new read-only endpoint:

1. Define the filesystem path near the existing path constants.
2. Add a helper if the response type is new.
3. Add `server.middlewares.use("/api/name", async (_req, res) => { ... })`.
4. Set a correct `Content-Type`.
5. Set `Cache-Control: no-store` for live or frequently changing data.
6. Add a frontend fetch helper in `data.ts`, `goals.ts`, or a hook in
   `App.tsx`, depending on what consumes it.

How to change goal persistence:

1. Keep `isGoalPoint` and `isGoalsConfig` strict enough to reject malformed
   payloads.
2. Keep `writeGoalsConfig` atomic with a temporary file and rename.
3. Preserve the shape:

```json
{
  "Goals": [
    { "name": "PICKUP_01", "coordinates": [-24, 3.5] }
  ]
}
```

Important caution:

- The active React app does not use `web-app/app.py`.
- If an endpoint changes, update all matching frontend fetch calls.
- If a runtime file path changes, check controller-side writers too.

### `web-app/src/data.ts`

This file owns the simulation table data contract.

It contains:

- Shared table value types.
- Column definitions for simulations, events, and event telemetry.
- JSONL parsing.
- Numeric value detection.
- Fetch helpers for `/api/simulations`, `/api/events`, and
  `/api/event-telemetry`.
- `fetchSimulationTableData()`, which loads all table data in parallel.

Use this file when you want to:

- Add, remove, or rename a table column.
- Change how JSONL is parsed.
- Change how table data is fetched.
- Change how numeric table cells are detected.
- Add a new data helper shared between the logs page and table components.

How to add a column:

1. Confirm the JSONL producer writes that key.
2. Add `{ key: "...", label: "..." }` to the correct column array.
3. If the value should affect charts or metrics, also update `App.tsx`.
4. Run `npm run build`.

Important caution:

- Do not change existing column keys unless the log writer has changed too.
- `parseJsonLines` currently tolerates concatenated JSON objects by inserting
  line breaks between adjacent object boundaries. Keep that behavior unless the
  log format is deliberately changed.

### `web-app/src/SimulationTable.tsx`

This file renders the simulation, event, and event-telemetry tables.

It contains:

- `DataTable`, a reusable table renderer.
- `SimulationTables`, which renders the three current table sections.
- `latestNumericValue`, used by the logs page for summary metrics.
- The default standalone `/tables` page.

Use this file when you want to:

- Change table rendering.
- Change empty/loading/error display for the standalone table route.
- Change collapsible table behavior.
- Change how rows or cells are rendered.
- Reuse the table component somewhere else.

How to add a new table section:

1. Add a data shape and fetch helper in `data.ts`.
2. Add a new `DataTable` call inside `SimulationTables`.
3. Add styles in `App.css` only if the existing table styling is not enough.

Important caution:

- Keep column definitions in `data.ts`, not directly inside
  `SimulationTable.tsx`.
- Keep row keys stable enough to avoid React list warnings.

### `web-app/src/LiveMap.tsx`

This file renders the warehouse map as SVG.

It receives realtime robot data and renders:

- Static warehouse bounds.
- Optional grid lines.
- Static obstacle rectangles.
- Static pickup, dropoff, and charging points.
- Current active path.
- Current goal marker.
- Current robot marker and heading line.
- Map legend.

It supports two variants:

- `panel`, used on the dashboard.
- `expanded`, used on the map page.

Use this file when you want to:

- Change map SVG geometry.
- Change which layers are available.
- Change robot, goal, path, or point rendering.
- Change map zoom behavior.
- Add or remove map legend items.

Important map coordinate rule:

SVG Y coordinates grow downward, but warehouse Y coordinates are normal map
coordinates. This file flips Y with:

```ts
const y = (value: number) => -value;
```

If you add new geometry, use this helper consistently for Y values.

Important caution:

- If you change a marker shape in `LiveMap.tsx`, also update matching legend CSS
  in `App.css`.
- If you change static points or obstacles, prefer editing `mapData.ts`.
- Keep `LiveMap.tsx` focused on rendering, not fetching data.

### `web-app/src/mapData.ts`

This file stores static map data.

It contains:

- `MAP_BOUNDS`
- Pickup, dropoff, and charging points.
- Fixed obstacles.
- Types for map points and obstacles.

Use this file when you want to:

- Move a pickup/dropoff/charging marker.
- Add a new static marker.
- Change warehouse bounds.
- Add, remove, or resize fixed obstacles.

Important caution:

- Keep this file data-only.
- If a new point kind is added, update `PointKind`, `LiveMap.tsx`, and CSS
  legend styles in `App.css`.
- Check that map data stays consistent with controller/world coordinates.

### `web-app/src/types.ts`

This file defines the TypeScript shape of realtime robot telemetry.

It currently defines `RobotData`, including:

- `time`
- `state`
- `gps`
- `errors`
- `current_velocities`
- `target_velocities`
- `goal_position`
- `next_point`

Use this file when you want to:

- Add a new field from `/api/realtime-panel`.
- Remove a field that the controller no longer sends.
- Make frontend code safer by documenting the exact shape of a realtime payload.

How to add a realtime field:

1. Confirm the controller writes the field to
   `robot_controller_runs_realtime_panel.jsonl`.
2. Add the field to `RobotData`.
3. Render it in `App.tsx` or another component.
4. If it is optional, type it as optional or nullable and handle the missing
   case in the UI.

Important caution:

- Do not pretend a field exists just because it would be useful. The source of
  truth is the controller payload served by `/api/realtime-panel`.

### `web-app/src/goals.ts`

This file owns client-side goal-order logic.

It contains:

- `GoalPoint`
- `GoalsConfig`
- `MoveDirection`
- `initialGoalPoints`
- `moveGoal`
- `buildGoalsConfig`
- `loadGoalsConfig`
- `saveGoalsConfig`

Use this file when you want to:

- Change how the goal order is represented in frontend code.
- Change movement behavior for up/down buttons.
- Add helpers for goal editing.
- Change how React loads or saves goal order through `/api/goals`.

How goal movement currently works:

1. `GoalOrder` in `App.tsx` calls `onMoveGoal`.
2. `useGoalOrder` calls `moveGoal`.
3. `moveGoal` swaps a selected goal with the adjacent goal.
4. `saveGoalsConfig` sends the whole ordered `Goals` payload to `/api/goals`.
5. `vite.config.ts` validates and writes `goals.config.json`.

Important caution:

- Keep `moveGoal` predictable and side-effect free.
- Keep persistence in `saveGoalsConfig`, not inside `moveGoal`.
- Preserve the full ordered `Goals` payload because the controller reads ordered
  goals from the same file.

### `web-app/src/goals.config.json`

This JSON file is the canonical goal order used by the web app and controller
workflow.

Use this file when you want to:

- Change the default goal order.
- Change a goal coordinate.
- Add or remove a goal, but only if the controller can handle it.

Expected structure:

```json
{
  "Goals": [
    {
      "name": "CHARGING_STATION",
      "coordinates": [6.75, -4.5]
    }
  ]
}
```

Important caution:

- Keep `Goals` as a non-empty array.
- Keep every `coordinates` value as exactly two finite numbers.
- Be aware that the dashboard can write this file through `/api/goals`.
- Be aware that controller shutdown logic may also rewrite this file as the
  canonical ordered goals payload.

### `web-app/src/main.tsx`

This is the React entrypoint.

It imports fonts, imports `App`, finds the `root` element in `index.html`, and
mounts the React app.

Use this file when you want to:

- Add global React providers.
- Change global font imports.
- Change app bootstrap behavior.

Important caution:

- Do not put page logic here.
- Do not put API fetch logic here.
- If you add a provider, keep it minimal and document why it belongs globally.

## Supporting files

### `web-app/index.html`

This is the HTML shell loaded by Vite.

Use this file when you want to:

- Change page title.
- Add global metadata.
- Add a root-level static script or stylesheet that must exist before React
  loads.

Important caution:

- Keep `<div id="root"></div>` because `main.tsx` mounts React there.
- Most UI changes belong in React files, not this HTML file.

### `web-app/package.json`

This file defines npm scripts and dependencies.

Use this file when you want to:

- Add a dependency.
- Add or change an npm script.
- Check how to run the app.

Current useful scripts:

- `npm run dev`
- `npm run build`
- `npm run preview`

Important caution:

- Add dependencies only when they solve a real problem.
- After dependency changes, keep `package-lock.json` in sync by using npm.

### `web-app/package-lock.json`

This file locks exact dependency versions.

Use this file when:

- npm updates it after dependency install, removal, or version change.

Important caution:

- Do not edit it manually.
- Do not remove it just because it is large.

### `web-app/tsconfig.json`

This file configures TypeScript.

Use this file when you want to:

- Change TypeScript compiler behavior.
- Add global type environments.

Important caution:

- Most app work does not require changing this file.
- If changing it breaks `npm run build`, revert the compiler setting or adjust
  the affected TypeScript code deliberately.

### `web-app/app.py`

This is the older Streamlit dashboard.

For the current React/Vite app, treat this file as legacy/reference code.

Use this file only when you intentionally want to:

- Inspect old dashboard behavior.
- Compare old Streamlit concepts with the current React implementation.
- Maintain the old Streamlit dashboard separately.

Important caution:

- Do not add React API routes here.
- Do not fix current React dashboard data bugs here.
- Do not assume this file drives `npm run dev`; it does not.

### `web-app/dist`

This is generated production output from `npm run build`.

Use this directory only as build output.

Important caution:

- Do not edit files in `dist` manually.
- If something in `dist` is wrong, fix source files and rerun `npm run build`.

### `web-app/node_modules`

This is the installed dependency directory.

Important caution:

- Do not edit files in `node_modules`.
- Do not document manual changes to dependency internals as a fix.
- If dependency code seems wrong, solve it in app code or change the dependency
  version through `package.json` and npm.

## Common contribution tasks

### Add a new dashboard metric

1. Confirm the value exists in `/api/realtime-panel`.
2. Add the field to `RobotData` in `types.ts` if needed.
3. Render it in `DashboardPage` in `App.tsx`.
4. Add or reuse CSS classes in `App.css`.
5. Run `npm run build`.

### Add a new telemetry table column

1. Confirm the JSONL file contains the key.
2. Add the column to `simulationColumns`, `eventColumns`, or
   `telemetryColumns` in `data.ts`.
3. If the column should appear in a chart or metric, update `App.tsx`.
4. Run `npm run build`.

### Add a new image feed

1. Make sure the controller writes an image file under `logging/logs`.
2. Add a path constant and API route in `vite.config.ts`.
3. Render it with `LiveImage` in `App.tsx`.
4. Add any required styling in `App.css`.
5. Run `npm run build`.

### Add a new page

1. Add a page component in `App.tsx`.
2. Add a route in the `<Routes>` block.
3. Add a navigation item to `navItems` if users should access it from nav.
4. Add styles in `App.css`.
5. Run `npm run build`.

### Change live map visuals

1. Update static map data in `mapData.ts` if the change is data-driven.
2. Update SVG rendering in `LiveMap.tsx` if the change is visual or structural.
3. Update map and legend styles in `App.css`.
4. Check both dashboard map and expanded map behavior.
5. Run `npm run build`.

### Change goal-order behavior

1. Update UI rendering in `GoalOrder` in `App.tsx`.
2. Update movement or API helpers in `goals.ts`.
3. Update `/api/goals` validation or persistence in `vite.config.ts` if the JSON
   shape changes.
4. Keep `goals.config.json` compatible with the controller.
5. Run `npm run build`.

### Change API data sources

1. Update path constants in `vite.config.ts`.
2. Update API route logic in `vite.config.ts`.
3. Update frontend fetch code in `App.tsx`, `data.ts`, or `goals.ts`.
4. Update TypeScript types in `types.ts` if realtime payload shape changes.
5. Run `npm run build`.

## Data contracts to preserve

### Realtime panel payload

The dashboard expects `/api/realtime-panel` to return a JSON object matching
`RobotData` in `types.ts`.

If this payload changes, update:

1. The controller writer.
2. `web-app/src/types.ts`.
3. Any rendering in `web-app/src/App.tsx`.

### Image feeds

The dashboard expects:

- `/api/local-planner-grid` to serve `logging/logs/local_planner_grid.jpg`
- `/api/camera-feed` to serve `logging/logs/camera_feed.jpg`

If image filenames or formats change, update:

1. The controller writer.
2. `vite.config.ts`.
3. The React `LiveImage` usage if the endpoint name changes.

### Tables

The logs page expects:

- `/api/simulations`
- `/api/events`
- `/api/event-telemetry`

The columns live in `data.ts`, and the rendering lives in
`SimulationTable.tsx`.

### Goals

The goal-order dashboard expects:

- `web-app/src/goals.config.json`
- `/api/goals`
- `goals.ts`
- `GoalOrder` and `useGoalOrder` in `App.tsx`

The JSON shape should remain a top-level `Goals` array unless the controller is
updated too.

## Validation checklist

After any web-app code change:

1. Run:

```bash
cd web-app
npm run build
```

2. If the change affects runtime endpoints, also run:

```bash
cd web-app
npm run dev
```

3. Open the affected route:

- Dashboard: `/`
- Map: `/map`
- Fleet: `/fleet`
- Logs: `/logs`
- Help: `/help`
- Standalone tables: `/tables`

4. If the change uses controller output files, confirm the relevant file under
   `logging/logs` is being updated by the controller.

## What not to do

- Do not hand-edit `node_modules`.
- Do not hand-edit generated files in `dist`.
- Do not put active React API logic into `web-app/app.py`.
- Do not change table column keys without checking the JSONL producer.
- Do not change realtime telemetry fields without checking `RobotData` and the
  controller payload.
- Do not change map point names, point kinds, or coordinates without checking
  map rendering and controller/world consistency.
- Do not make visual changes only for desktop; check the responsive CSS rules.
- Do not skip `npm run build` after TypeScript, React, Vite, or CSS changes.
