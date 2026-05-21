# Web App Restyle Preservation Notes

This file preserves the important long-term ideas from `web-app-restyle` before
that directory is removed. It is intentionally a compact design summary, not a
full archive of the deleted mockups.

## Core Direction

The restyle direction is the **AGV Command Center**: a dark, industrial,
high-density dashboard for monitoring an AGV mission in real time.

The intended feeling is:

- Calm and operational.
- Technical, but readable.
- Dense enough for monitoring, but grouped enough to avoid clutter.
- Strongly focused on situational awareness: telemetry, map, image feeds,
  mission status, and logs must be easy to scan quickly.

## Design System To Preserve

The design system name in the restyle material was **Cybernetic Industrial
Command**.

Important design principles:

- Use a dark-first interface to reduce eye strain during long monitoring
  sessions.
- Use compact, high-contrast cards for live telemetry.
- Use monospaced numeric values so changing telemetry does not visually jump.
- Use clean geometric alignment and predictable grids.
- Use subtle glass-like surfaces and thin technical borders for depth.
- Keep corners tight and modern, generally around 8px for cards and buttons.
- Use status pills for live, saved, active, warning, and critical states.
- Keep visual density high, but separate information into clear categories.

## Colors To Preserve

The important palette direction is:

- Deep charcoal backgrounds, especially near `#0d0e0f`, `#121414`,
  `#1b1c1c`, and `#1f2020`.
- Slightly brighter card surfaces such as `#292a2a` and `#343535`.
- Light foreground text near `#e3e2e2`.
- Muted industrial outline tones near `#b18780`.
- Coral/red primary accents near `#ffb4a8` and stronger red near `#ff5540`.
- Green for success, amber for warnings, and red for critical/emergency states.
- Avoid pure black as the main background; use charcoal instead.

## Typography To Preserve

The restyle uses two font roles:

- **Inter** for interface structure, headings, labels, and body text.
- **JetBrains Mono** for telemetry values, coordinates, timestamps, table data,
  and other numbers.

Important typography behavior:

- Numeric values should be stable and easy to compare.
- Labels should be compact, uppercase, and scannable.
- Large headings should be used sparingly.
- Dense operational panels should avoid oversized marketing-style text.

## Component Rules To Preserve

### Metric Cards

Metric cards should behave like compact telemetry modules:

- Label at the top.
- Value as the visual focus.
- Unit visually secondary.
- Monospaced value text.
- Consistent sizing inside grouped cards.
- Group related values instead of leaving isolated uneven cards.

### Panels

Panels should:

- Use a thin border.
- Use dark elevated surfaces.
- Keep spacing compact.
- Group one clear operational purpose.
- Avoid unnecessary nested cards.

### Tables

Tables should:

- Keep uppercase headers.
- Use monospaced table data.
- Right-align numeric values when possible.
- Preserve the current simulation, event, and event telemetry schemas.
- Use subtle row separation and low-contrast striping.
- Stay readable in dense diagnostic views.

### Live Feeds

Camera and planner feed frames should:

- Look like operational viewfinders.
- Use thin corner bracket styling.
- Show a clear live indicator.
- Keep image content unobstructed.

### Map

The map should:

- Remain a major visual focus.
- Use a dark technical background.
- Show the active AGV clearly.
- Show heading direction.
- Show the active goal.
- Show route/path information.
- Show pickup, dropoff, and charging points.
- Keep the legend close to the map and visually attached to the map surface.
- Use a bright lightning-style charging marker rather than the old orange
  diamond.

## Page Concepts To Preserve

### Dashboard

The dashboard is the main monitoring page.

It should preserve:

- Mission runtime.
- Active unit status.
- Navigation/state coordinates.
- Goal target information.
- Editable goal order.
- Live warehouse map.
- AI camera feed.
- Local planner feed.
- Realtime telemetry grouped by category.
- Collapsed simulation log tables.

The dashboard should prioritize what an operator needs during a live run.

### Map View

The map view is for deeper spatial inspection.

It should preserve:

- Expanded map space.
- Layer controls for grid, obstacles, path, and goals.
- Zoom controls.
- Dashboard pointer or active-unit context.
- Planner and camera feeds below or near the map workspace.

The map page should not duplicate every dashboard metric. It should focus on
spatial analysis.

### Fleet Status

The fleet page is designed for a future multi-unit system but currently reflects
a single active unit.

It should preserve:

- Top-level fleet summary cards.
- UNIT-00 status.
- Mission runtime.
- Current linear and angular velocity.
- Distance and heading error.
- Goal information.

Values that do not exist in the current data source should remain clearly marked
as unavailable rather than invented.

### Log Analysis

The logs page is for diagnostics after or during a run.

It should preserve:

- Simulation count.
- Event count.
- Telemetry row count.
- Current linear velocity summary.
- Linear velocity chart.
- Heading error chart.
- Full simulation, event, and event telemetry tables.

The page should stay oriented around real saved data, not mock analytics.

### Help Center

The help page should remain a support and reference page.

It should preserve:

- Quick operational help cards.
- Repository documentation display.
- Clear guidance without interfering with the live monitoring pages.

## Prototype Ideas Worth Keeping

The `react-app-idea.html` file was useful as a static visual prototype, but it
should not be preserved as an implementation source.

Keep these ideas:

- Fixed top command bar.
- Fixed left navigation on desktop.
- Bottom navigation on mobile.
- Emergency stop as a strong critical action.
- Dense metric cards.
- Map-first visual layout.
- Technical dark theme.
- Live feed framing.
- Log analysis as a diagnostic workspace.

Do not preserve these parts as requirements:

- CDN-based React setup.
- Tailwind-specific implementation details.
- Placeholder avatars or stock imagery.
- Mock-only fields that are not backed by current data.
- Features not currently implemented, such as advanced filtering or CSV export,
  unless they are explicitly requested later.

## Image References That Existed

The deleted directory contained visual references for:

- Overall AGV command center redesign.
- Dashboard.
- Map view.
- Fleet status.
- Log analysis.
- Help center.

Future work should treat those images as design direction only. The current app
should continue to preserve real data sources and current React/Vite behavior.

## Non-Negotiable Constraints From The Restyle

- Keep the app usable with the current React/Vite workflow.
- Keep existing runtime data sources.
- Keep images sourced from the runtime logs directory.
- Keep table schemas stable unless the logging format changes deliberately.
- Keep the goal order UI functional and persistent.
- Keep map, camera, planner feed, fleet, logs, and help surfaces available.
- Validate web-app changes with a production build.
