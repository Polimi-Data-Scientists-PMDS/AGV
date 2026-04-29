# Real-Time AGV Streamlit Dashboard

## Section 1: Implementation Details, Motivation & Workflow

### What I did
I designed and implemented a lightweight, real-time dashboard using **Streamlit** to visualize the dynamics and live state of the Autonomous Guided Vehicle (AGV). 
The interface provides continuous updates to:
- The robot's spatial coordinates and heading ($x$, $y$, $\theta$).
- GPS sensor readings.
- Tracking metrics including distance and heading errors relative to the current goal.
- Current and target (commanded) velocities (linear and angular).
- A 2D live map plotting the robot's current position, orientation, fixed static obstacles (Work Islands and Walls), and its relative location to known waypoints, properly scaled to the warehouse's 69x22 meter dimensions.
- **Live Local Planner Grid**: A real-time video feed displaying the navigation logic matrix.
- **Robot AI Camera**: A real-time video feed displaying the YOLO-based object detection output from the robot's onboard camera.

### Why I did it
- **Why Streamlit:** Streamlit is highly optimized for Python data applications. It allows us to rapidly prototype user interfaces directly from our Python scripts without needing to build a complex frontend in JavaScript or setting up complicated API endpoints for real-time WebSockets.
- **Data Source Decision:** Instead of directly querying the MySQL database continuously—which could introduce latency and load—the dashboard reads from the localized `robot_controller_runs_realtime_panel.jsonl` file. It also reads individual JPEG image streams directly from the `logs` folder. These files are consistently overwritten by the controller with the absolute latest state variables, ensuring $O(1)$ read complexity with minimal overhead.

### Workflow
1. The Webots Python controller captures the simulation state and dumps the latest telemetry frame and image streams (`camera_feed.jpg` & `local_planner_grid.jpg`) to the `logs/` directory every cycle.
2. The Streamlit application (`dashboard/app.py`) reads these files at a customizable FPS.
3. Using `matplotlib`, the dashboard recalculates and draws the robot's coordinates on a static warehouse grid.
4. Streamlit avoids full-page flickering by utilizing an infinite `while True` loop that targets and updates specific UI components (`st.empty()`) in-place, creating a seamless, true video-feed experience.

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
2. If the AGV simulation **is currently running** in Webots, the metrics, map, and visualizers will update in real-time.
3. If the simulation is **stopped**, the dashboard will display the very last known state of the robot before the simulation ended.
4. You can use the left sidebar to adjust the `Refresh Rate (FPS)` slider to match your desired frame rate dynamically.
