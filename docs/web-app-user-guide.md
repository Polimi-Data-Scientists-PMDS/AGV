# Web App User Guide

The AGV Command Center monitors independent AGV units, their live telemetry,
unit-specific images, controller-owned routes, and persisted simulation data.

## Start Here

The services must be started in this order:

1. Start MySQL.
2. Start the logging server.
3. Start Webots and press Play.
4. Start the web app, or leave it running if it is already open.

The web app automatically discovers active units after Webots starts. There is
no need to restart the web app just because a simulation begins.

### One-Time Setup

From the project root, create the Python environment:

```bash
./setup.sh
```

Install frontend dependencies once:

```bash
cd web-app
npm install
```

Configure Webots to use the Python interpreter printed by `./setup.sh` in
`Webots > Preferences > Python commands`.

### Start MySQL

For an existing container:

```bash
docker start agv-logger
```

For a first-time database setup, create the container:

```bash
docker run --name agv-logger -e MYSQL_ROOT_PASSWORD=agv_pass -p 3306:3306 -d mysql:latest
```

Then create the `agv_data` database and its tables using
`Database_Structure.sql`. See the project `README.md` for the complete
first-time database procedure.

### Start The Logging Server

In a terminal at the project root, run:

```bash
.venv/bin/python logging/logging_server.py
```

It listens on `127.0.0.1:8080` by default. Start it before Webots: each
`DefaultController` creates its simulation record through this service before it
is allowed to move.

### Start Webots

Open this world in Webots:

```text
AGV_Webots_World_and_Controllers/worlds/AGV_Warehouse_World.wbt
```

Confirm the AGVs use `DefaultController`, then press Webots Play. Keep Webots
open while the robots are running.

### Start Or Reuse The Web App

In a separate terminal:

```bash
cd web-app
npm run dev
```

Open the local URL printed by Vite, normally `http://localhost:5173`.

If the web app is already running, leave it open. Once Webots starts producing
unit telemetry and images, the app discovers the units and begins receiving
data automatically. Persistent simulation, event, and event-telemetry data
also becomes available once the logging server commits it to MySQL.

The current API routes are provided by `npm run dev`. A Vite production preview
does not provide these development-server routes.

## Navigation And Page Controls

Use the sidebar or top navigation on desktop. On small screens, navigation is
at the bottom.

The page-control dock is fixed near the bottom of the page. It contains only
controls that affect the current page:

| Page | Available controls |
|---|---|
| Dashboard | Robot, Live refresh, Database refresh |
| Map View | Robot, Live refresh |
| Fleet Status | Live refresh |
| Log Analysis | Robot, Simulation, Live refresh, Database refresh |
| Help Center | None |

- **Robot** selects one unit for pages that show a single robot.
- **Simulation** selects one simulation for the selected unit. `All
  simulations` keeps tables broad but charts use the selected unit's newest
  simulation.
- **Live refresh** controls unit telemetry and image requests. Choices are
  50 ms, 100 ms, 250 ms, 500 ms, and 1 s; 50 ms is the default.
- **Database refresh** controls MySQL snapshot requests. Choices are 3 s, 5 s,
  10 s, 15 s, and 30 s; 10 s is the default.

The selected robot and refresh intervals are retained in the browser for the
next visit.

## Dashboard

The Dashboard is the single-robot operational view. Select a unit in the
bottom dock, then use it to monitor:

- Mission runtime and estimated navigation state.
- Current goal and next local-planner point.
- Unit-specific warehouse map, AI camera image, and local-planner grid.
- Current telemetry: state, GPS, errors, current velocities, and target
  velocities.
- The selected robot's controller-owned goal route.
- Compact MySQL simulation, event, and event-telemetry tables.

### Goal Route Management

Goal routes belong to
`AGV_Webots_World_and_Controllers/controllers/DefaultController/goals.config.json`.
The web app updates that controller-owned file; it does not use a frontend goal
configuration.

For the selected robot, you can:

1. Use the arrows to move a goal earlier or later in that robot's route.
2. Add a goal with a unique name and finite X/Y coordinates. It is appended to
   the selected route.
3. Remove a goal with the trash control. The app prevents removing the final
   remaining goal in a route and retains shared goals used by another route.

Avoid editing the same goals configuration file manually while saving a goal
change from the web app.

### Emergency Stop

The desktop sidebar button is a global stop, not a selected-robot stop.

1. Select **Emergency Stop** to stop every active robot using
   `DefaultController`.
2. Webots remains running; each controller replaces its motion command with
   zero linear, angular, and wheel velocities on its next controller cycle.
3. Select **Resume Robots** to remove the global stop and allow normal commands
   again.

The stop remains active until it is explicitly resumed, including if the web
app is reloaded.

## Map View

Map View is a larger, single-robot warehouse view. Select the robot in the
bottom dock, then use the map controls to toggle Grid, Obstacles, Path, and
Goals, or adjust zoom. The page also displays that unit's camera and
local-planner images.

## Fleet Status

Fleet Status is the only multi-robot page. It shows one live summary card for
each discovered unit; there is no robot selector. Use Live refresh to control
how often those unit snapshots are retrieved.

If a unit is listed but has no current payload, its card reports that it is
waiting or unavailable rather than showing another robot's data.

## Log Analysis

Log Analysis reads persistent data from MySQL, not from the JSONL mirrors.
Select a unit and optionally a simulation in the bottom dock.

The page shows simulation rows, events, event telemetry, and two charts:

- **Linear Velocity Over Time** uses `current_vel_linear`.
- **Heading Error Deviation** uses `error_heading`.

Both charts use up to the latest 100 event-telemetry rows for the selected
unit/simulation. When `All simulations` is selected, they use only the selected
unit's highest simulation ID. Fewer rows are shown when fewer samples exist.

Event telemetry is recorded when an event is logged; it is not the continuous
50 ms realtime stream.

### Normal And Full Database Loads

Automatic snapshots return at most 200 rows from each of the three tables. Use
**Load all matching records** only when necessary. The confirmation warns that a
large query can temporarily block logging-server database access, consume memory,
or make the page slow.

After a full load, automatic database refresh is paused. Choose **Resume latest
200** to return to normal polling.

## Live Data And Common Problems

### No Signal Or An Unavailable Unit

Check the startup order:

1. MySQL container is running.
2. Logging server is running.
3. Webots is open with the warehouse world loaded and Play pressed.
4. The robot uses `DefaultController` and a valid `PIONEER_3_<number>` name.

The web app discovers valid realtime unit snapshots periodically. A just-started
robot can take a few seconds to appear.

### Logs Are Empty

Make sure the logging server was running before Webots started. Persistent data
appears only after the controller has created and saved simulation records to
MySQL. Empty data is normal before the first saved run or for a unit/simulation
combination with no matching records.

### Camera Or Local Planner Image Is Stale

Images are selected by robot unit ID. If telemetry updates but an image does
not, the corresponding camera or local-planner writer may not be producing a
new file for that robot.

### Database Service Is Unavailable

Check that MySQL is running and that `logging/logging_server.py` is still
listening on the URL expected by the web app. The default is
`http://127.0.0.1:8080`.

## Help Center

Help Center displays this guide inside the web app. It has no robot or refresh
controls.
