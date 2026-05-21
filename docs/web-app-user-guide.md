# Web App User Guide

This guide explains how to use the AGV web app as an operator or observer.

If you want to contribute to the web app follow the instructions in:
`docs/web-app-contribution-guide.md`.

## What The Web App Shows

The web app is an operational dashboard for monitoring the AGV while it runs.
It brings together live telemetry, mission targets, map position, camera view,
local planner view, fleet status, and recorded logs.

The app is organized into five main areas:

1. **Dashboard**
2. **Map View**
3. **Fleet Status**
4. **Log Analysis**
5. **Help Center**

The left sidebar and top navigation let you switch between these areas. On small
screens, navigation appears at the bottom.

## General Status Indicators

### Live Signal

`Live Signal` means the app is receiving current AGV telemetry. If this changes
to a missing or disconnected state, the app is not receiving a fresh realtime
payload.

When there is no live signal, the dashboard cannot reliably show the current
position, velocities, goal, or map state.

### Live Badges

Image feeds have a `Live` badge. This means the panel is intended to show the
latest available image. If the image does not visually change, the source image
may not be updating even if the web page itself is refreshing.

### Saved, Saving, And Save Failed

The goal order panel can show save status:

- `Saved`: the current goal order was stored successfully.
- `Saving...`: the app is trying to store the new order.
- `Save failed`: the app could not store the latest goal order.
- `Using local goal order`: the app could not load the persisted order and is
  showing the local default order.

## Dashboard

The Dashboard is the main monitoring page. Use it when you want the complete
live picture of the AGV mission.

It contains:

- Mission runtime.
- Active unit count.
- Navigation coordinates.
- Goal target.
- Goal order.
- Warehouse map.
- AI camera.
- Local planner view.
- Realtime telemetry.
- Simulation logs.

### Mission Runtime

Mission runtime is the elapsed time of the active AGV run.

Use it to understand how long the current mission has been running. If the
runtime continues to move forward, the AGV system is likely still active and
publishing telemetry.

### Active Unit

Active Unit shows how many AGV units the dashboard currently sees as active.
The current app is focused on a single unit, so this normally shows one active
unit.

### Navigation Coordinates

The `Nav. Coordinates` card summarizes the robot state:

- `State X`: the AGV's estimated X position.
- `State Y`: the AGV's estimated Y position.
- `Theta`: the AGV's estimated orientation angle.

`Theta` is measured in radians. It describes where the AGV is pointing, not
where it is located.

Use this card to quickly check the estimated pose of the AGV.

### Goal Target

The `Goal Target` card shows the current navigation target and next local point:

- `Goal X`: X coordinate of the current final goal.
- `Goal Y`: Y coordinate of the current final goal.
- `Next X`: X coordinate of the immediate next point the AGV is following.
- `Next Y`: Y coordinate of the immediate next point the AGV is following.

The goal is the larger mission target. The next point is the short-term target
chosen by the path planner on the way to that goal.

If `Next X` or `Next Y` is missing, the app does not currently have a next local
planner point to display.

### Goal Order

The `Goal Order` panel controls the sequence of mission goals.

Each row represents one goal. The number on the left is its current order in the
mission sequence. The goal name tells you which pickup, dropoff, or charging
location it represents. The coordinate text shows where that goal is located.

You can interact with it by:

1. Selecting a goal row.
2. Moving it up or down with the arrow buttons.
3. Checking the save status at the top of the card.

The AGV follows the saved goal order. Reordering goals changes the mission
sequence for future navigation behavior.

### Warehouse Map

The map shows the AGV position inside the warehouse layout.

It includes:

- AGV marker.
- Heading direction.
- Pickup points.
- Dropoff point.
- Charging station.
- Current goal marker.
- Active path.
- Fixed obstacles.
- Legend.

The AGV marker shows where the robot is estimated to be. The heading line shows
the direction it is facing. The path shows the route between the current robot
position, next local point, and goal.

Use the map to understand whether the AGV is moving toward the expected goal and
whether its route makes visual sense.

### AI Camera

The AI Camera panel shows the latest camera feed intended for object detection
and visual inspection.

Use it to see what the AGV camera currently sees. If object detection is active,
the image may include visual annotations such as detection boxes or labels.

If the image stays visually identical for a long time, the camera feed may not
be updating. This is different from the web app being frozen: other dashboard
values may continue to update while the image source stays unchanged.

### Local Planner / Lidar

The Local Planner / Lidar panel shows the local planning view.

This view is useful for understanding how the AGV perceives nearby space and how
the short-term planner is interpreting obstacles, free space, and local route
choices.

If this feed updates while the AI Camera does not, the planner image source is
active but the camera image source may be stale.

### Realtime Telemetry

Realtime Telemetry groups the detailed live values into categories.

#### State

State values describe the AGV's estimated pose:

- `State X`: estimated X position.
- `State Y`: estimated Y position.
- `State Theta`: estimated heading angle in radians.

These values are the robot's internal estimate of where it is and how it is
oriented.

#### Velocities

Velocity values compare what the AGV is doing with what the control system is
asking it to do:

- `Current Linear`: actual or estimated forward movement speed.
- `Current Angular`: actual or estimated turning speed.
- `Target Linear`: requested forward movement speed.
- `Target Angular`: requested turning speed.

Linear velocity describes forward/backward movement. Angular velocity describes
rotation.

`Current` values describe what the AGV is currently doing. `Target` values
describe what the control system wants the AGV to do. If current and target
values are close, the AGV is following the requested motion well. If they differ
strongly for a long time, the robot may be limited by physics, movement limits,
obstacles, or a control issue.

#### Coordinates

Coordinate values show the GPS-based position:

- `GPS X`: measured X position.
- `GPS Y`: measured Y position.

These values are useful for comparing measured position against the estimated
state position.

#### Errors

Errors show how far the AGV is from its intended path or target:

- `Distance Error`: how far the AGV is from the target point.
- `Heading Error`: how much the AGV's facing direction differs from the desired
  direction.

Distance error is measured as a distance. Heading error is measured as an angle.

A large distance error means the AGV is physically far from where it is trying
to go. A large heading error means the AGV is pointing in a direction that does
not align well with where it needs to move.

### Simulation Logs On The Dashboard

The dashboard includes simulation logs in a collapsed form. They are present for
quick access without taking over the main monitoring view.

Open them when you need to inspect recorded simulation, event, or telemetry
rows without leaving the dashboard.

## Map View

The Map View is a larger spatial-analysis page.

Use it when the dashboard map is too small and you want to inspect the AGV route
and warehouse layout more carefully.

### Map Layers

The map controls let you toggle visible layers:

- `Grid`: shows coordinate grid structure.
- `Obstacles`: shows fixed physical obstacles.
- `Path`: shows the active route.
- `Goals`: shows pickup, dropoff, charging, and target markers.

Turning layers on and off helps isolate one kind of information. For example,
if the map feels visually busy, hide goals or grid lines temporarily to focus on
the active path.

### Zoom

Zoom controls change the map scale.

Zoom in when you need to inspect local movement around the AGV. Zoom out when
you need to understand the full warehouse route.

### Active Unit Dashboard Card

The Active Unit Dashboard card tells you that the map is currently following
the active AGV unit. Use its dashboard action to return to the main monitoring
page.

### Map Page Feeds

The Map View also shows planner and camera feeds. These help connect spatial
map behavior with the AGV's local perception and visual camera input.

## Fleet Status

The Fleet Status page summarizes the current fleet view.

The current system is prepared for a multi-unit layout, but the visible data is
for the active single unit.

### Top Fleet Cards

The top cards summarize fleet-level information:

- `Total Active`: how many units are active.
- `Idle Units`: how many units are idle, if available.
- `Maintenance Required`: whether maintenance information is available.
- `Average Battery`: battery information, if available.

Some values can show unavailable states because the current data source may not
provide those fields.

### UNIT-00 Card

The UNIT-00 card shows the active robot:

- Current active state.
- Mission runtime.
- Current linear velocity.
- Current angular velocity.
- Distance error.
- Heading error.
- Goal position.

Use this page when you want a compact unit-focused view rather than the full
dashboard.

### Mission Runtime Format

The fleet runtime is shown in minutes and seconds. It is intentionally shorter
than the full dashboard runtime so it fits inside the unit card.

### Current Linear And Current Angular Velocity

Current linear velocity tells you how fast the AGV is moving forward. Current
angular velocity tells you how fast it is turning.

These values describe actual current behavior, not requested behavior.

### Distance Error And Heading Error

Distance error indicates how far the unit is from its target. Heading error
indicates how far its orientation is from the desired direction.

In practice:

- High distance error means the AGV still has distance to close.
- High heading error means the AGV should turn or correct its orientation.
- Low values usually mean the AGV is better aligned with its current target.

## Log Analysis

The Log Analysis page is for reviewing saved run data.

Use it when you want to inspect what happened during a mission or compare
telemetry trends.

### Summary Cards

The top cards show:

- Number of simulations.
- Number of events.
- Number of telemetry rows.
- Latest current linear velocity.

These cards tell you whether there is meaningful recorded data to inspect.

### Linear Velocity Chart

This chart shows recent linear velocity values over time.

Use it to see whether the AGV moved smoothly, slowed down, stopped, or changed
speed unexpectedly.

### Heading Error Chart

This chart shows recent heading error values.

Use it to see whether the AGV had trouble aligning with its target direction.
Repeated spikes may indicate sharp turns, obstacle reactions, or control
instability.

### Event Telemetry Tables

The tables contain detailed recorded data:

- Simulation summary rows.
- Event rows.
- Event telemetry rows.

Open these tables when you need exact values instead of chart-level summaries.

### Reading Numeric Tables

Numeric table values are useful for comparing magnitude. Larger values are not
always worse; they must be interpreted by field:

- Larger runtime means the mission took longer.
- Larger distance error means the AGV was farther from its target.
- Larger heading error means stronger orientation mismatch.
- Velocity values can be positive, negative, or near zero depending on movement
  and rotation.

## Help Center

The Help Center is a reference area.

It contains quick help cards and repository documentation. Use it when you need
operational reminders, setup context, or project notes while staying inside the
web app.

## Common Situations

### The Dashboard Says There Is No Signal

This means the app is not receiving current telemetry.

Check whether the AGV simulation is running and whether telemetry is being
produced. The web app can only display the latest available data.

### The Map Moves But The Camera Does Not

This means telemetry and map data may be updating while the camera image is not.

The camera panel displays the latest available camera image. If that source
image is stale, the web app will keep showing the same frame.

### Goal Order Shows Save Failed

The app attempted to save the new order but could not complete the save.

The visible order may still change locally, but you should not assume it was
stored until the status returns to `Saved`.

### Some Fleet Values Show Unavailable

Unavailable values mean the current data source does not provide that
information. The app avoids inventing values that the AGV is not reporting.

### Logs Are Empty

Empty logs mean no matching saved data is currently available to the app.

This can happen before a run has produced records or if the run did not save the
expected information.

## Recommended User Workflow

1. Start on the Dashboard.
2. Check `Live Signal`.
3. Check mission runtime and active unit status.
4. Check the map to confirm the AGV is moving toward the expected goal.
5. Check Goal Target and Goal Order to confirm the mission sequence.
6. Watch the AI Camera and Local Planner feeds for perception context.
7. Use Realtime Telemetry to inspect detailed values.
8. Move to Map View if spatial inspection is needed.
9. Move to Fleet Status for a compact unit-health view.
10. Move to Log Analysis when you need saved run diagnostics.
11. Use Help Center when you need project or operation reference material.

## Key Terms

**State**: the AGV's estimated pose: X position, Y position, and orientation.

**GPS**: the measured position values. These can be compared with the estimated state
values.

**Theta**: the robot's orientation angle. It tells you which direction the robot is facing.

**Linear Velocity**: forward or backward movement speed.

**Angular Velocity**: turning speed.

**Current Velocity**: what the AGV is currently doing.

**Target Velocity**: what the control system is asking the AGV to do.

**Distance Error**: how far the AGV is from its current target point.

**Heading Error**: how far the AGV's current facing direction is from the desired facing direction.

**Goal**: the mission target the AGV is trying to reach.

**Next Point**: the short-term navigation point the AGV is currently following on the way to the
goal.

## Getting started

This section summarizes the setup flow around the web app. For more detailed
and precise setup information, use `README.md` in the project root.

Use this section when you need to prepare the project environment around the
web app before monitoring the AGV.

### Install The Python Environment

The recommended setup path is to run `./setup.sh` from the project root.

The setup script creates a virtual environment, installs the required Python
dependencies, and prints the absolute path to the Python interpreter that Webots
must use.

If you prefer a manual setup, create the virtual environment with
`python3.12 -m venv .venv`, activate it with `source .venv/bin/activate`, and
install the requirements with `pip install -r requirements.txt`.

Activate the virtual environment every time you open a new terminal before
running project Python commands.

### Install The React Dashboard Dependencies

The React dashboard dependencies live inside `web-app/`.

For an initial local install, run `cd web-app`, then
`npm install react react-dom`, then
`npm install -D typescript vite @vitejs/plugin-react @types/react @types/react-dom`.

After dependencies have been installed once, restore the same local packages
from `package-lock.json` by running `cd web-app` and `npm install`.

Start the web app with `cd web-app` and `npm run dev`.

### Configure Webots

Webots must use the Python interpreter from the project virtual environment.

Use the path printed by `./setup.sh`. If you set up the environment manually,
copy the absolute path to `.venv/bin/python3.12`.

Open Webots, go to `Webots > Preferences > Python commands`, and paste that
absolute Python path into the dedicated input box.

Never save the world directly from Webots with `Cmd + Shift + S` or
`Ctrl + Shift + S`, because doing so overwrites the `.wbt` file and removes its
custom comments.

### Run The Webots Simulation

Open Webots and load
`AGV_Webots_World_and_Controllers/worlds/AGV_Warehouse_World.wbt`.

The checked-in world file is configured to use `DefaultController`.

If you want the simulation to save data to MySQL, start the `agv-logger`
container before pressing run in Webots.

Press the Webots run/play control to start the simulation. Keep Webots open
while monitoring the AGV from the React dashboard.

If the controller does not start, re-check the Python commands setting in
Webots preferences and confirm that it points to the absolute Python path inside
`.venv`.

### Set Up The Docker Database

Install Docker Desktop for your operating system, open Docker Desktop, and wait
for the Docker Engine to fully start.

Start the MySQL container with
`docker run --name agv-logger -e MYSQL_ROOT_PASSWORD=agv_pass -p 3306:3306 -d mysql:latest`.

This creates a container named `agv-logger`, sets the MySQL root password to
`agv_pass`, runs the database in the background, and maps port `3306` so the
Python code can communicate with MySQL.

Open the MySQL console with `docker exec -it agv-logger mysql -u root -p`.
When prompted, enter `agv_pass`.

Inside the `mysql>` prompt, create and select the database with
`CREATE DATABASE agv_data;` and `USE agv_data;`.

Open `Database_Structure.sql`, copy its queries into the MySQL console, and run
each query separately. A successful query prints `Query OK`.

Ensure `mysql-connector-python` is installed in the Python environment. When
pulling new updates, check `Database_Structure.sql` again because schema changes
must be applied to the local database.

### Verify The Database

Open the MySQL console with `docker exec -it agv-logger mysql -u root -p` and
enter `agv_pass`.

Inside the `mysql>` prompt, run `SHOW DATABASES;`, `USE agv_data;`, and
`SHOW TABLES;`.

The table list should include `Events`, `EventTelemetry`, and `Simulations`.

To verify the table structures, run `DESCRIBE Simulations;`,
`DESCRIBE Events;`, and `DESCRIBE EventTelemetry;`.

After a Webots run that should save data, check saved row counts with
`SELECT COUNT(*) FROM Simulations;`, `SELECT COUNT(*) FROM Events;`, and
`SELECT COUNT(*) FROM EventTelemetry;`.

Counts of `0` are normal before the first saved run. If the database or tables
are missing, re-run the database creation commands and the queries from
`Database_Structure.sql`.

### Manage The Database Container

Exit the MySQL console with `exit;`.

Stop the database container with `docker stop agv-logger` when you want to free
up system resources.

Restart the existing database container with `docker start agv-logger` when you
are ready to resume the Webots simulation.

Do not run the original `docker run` command again after the container already
exists. To manage the database manually after restarting it, re-enter the console
with `docker exec -it agv-logger mysql -u root -p`, enter the password, and
select the database with `USE agv_data;`.
