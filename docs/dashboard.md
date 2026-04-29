# Real-Time AGV Streamlit Dashboard

## Section 1: Implementation Details, Motivation & Workflow

### What I did
I designed and implemented a lightweight, real-time dashboard using **Streamlit** to visualize the dynamics and live state of the Autonomous Guided Vehicle (AGV). 
The interface provides continuous updates to:
- The robot's spatial coordinates and heading ($x$, $y$, $\theta$).
- GPS sensor readings.
- Tracking metrics including distance and heading errors relative to the current goal.
- Current and target (commanded) velocities (linear and angular).
- A 2D live map plotting the robot's current position, orientation, and its relative location to known waypoints (Pickup/Dropoff/Charging stations) and the current goal.

### Why I did it
- **Why Streamlit:** Streamlit is highly optimized for Python data applications. It allows us to rapidly prototype user interfaces directly from our Python scripts without needing to build a complex frontend in JavaScript or setting up complicated API endpoints for real-time WebSockets.
- **Data Source Decision:** Instead of directly querying the MySQL database continuously—which could introduce latency and load—the dashboard reads from the localized `robot_controller_runs_realtime_panel.jsonl` file. This file is consistently overwritten by the controller with the absolute latest state variables (a single JSON object), ensuring $O(1)$ read complexity with minimal overhead.

### Workflow
1. The Webots Python controller captures the simulation state and dumps the latest telemetry frame to `logs/robot_controller_runs_realtime_panel.jsonl` every cycle.
2. The Streamlit application (`dashboard/app.py`) reads this file every 0.5 seconds (customizable).
3. Using `matplotlib`, the dashboard recalculates and draws the robot's coordinates on a grid against predefined fixed waypoints defined in the project's parameters.
4. Streamlit calls `st.rerun()` dynamically to auto-refresh the browser interface, presenting a smooth live feed of the metrics.

---

## Section 2: How to use the tool

### Prerequisites
Make sure your Python virtual environment has the required dependencies. If you haven't yet, activate your virtual environment and install the requirements:

```bash
# 1. Activate your virtual environment
source .venv/bin/activate

# 2. Install/Update requirements (includes streamlit and pandas)
pip install -r requirements.txt
```

### Running the Dashboard

To launch the dashboard, open a new terminal window, ensure your virtual environment is activated, and run:

```bash
streamlit run dashboard/app.py
```

### Expected Behavior
1. Streamlit will launch a local web server (usually at `http://localhost:8501`) and automatically open it in your default web browser.
2. If the AGV simulation **is currently running** in Webots, the metrics and the map will update in real-time.
3. If the simulation is **stopped**, the dashboard will display the very last known state of the robot before the simulation ended.
4. You can use the left sidebar to toggle the `Auto-Refresh` functionality or adjust the `Refresh Rate` to match your performance needs.
