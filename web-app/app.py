import streamlit as st
import json
import time
import os
import matplotlib.pyplot as plt

st.set_page_config(page_title="AGV Real-Time Dashboard", layout="wide", initial_sidebar_state="expanded")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, ".."))
LOGS_DIR = os.path.join(PROJECT_ROOT, "logging", "logs")

# Path to the realtime panel JSONL file
LOG_FILE_PATH = os.path.join(LOGS_DIR, "robot_controller_runs_realtime_panel.jsonl")

# Relevant points from documentation
POINTS = {
    "Dropoff 01": [-29.3, 4],
    "Pickup 1": [-24, 3.5],
    "Pickup 2": [-18.5, 6.25],
    "Pickup 3": [-13.5, 6.25],
    "Pickup 4": [-8.25, 4.5],
    "Pickup 5": [-2, 5.75],
    "Pickup 6": [3.75, 5.75],
    "Pickup 7": [18.75, 2.25],
    "Charging Station": [6.75, -4.5]
}

# Fixed Obstacles (Work Islands & Walls) [center_x, center_y, width, height]
OBSTACLES = [
    [-24.94, 1.92, 1.2, 3],
    [-19.22, 4, 1, 5],
    [-14.18, 4, 1, 5],
    [-9.34, 3.43, 1, 2],
    [-9.34, 0.92, 3, 4],
    [-2.71, 4, 1, 4],
    [2.96, 4, 1, 4],
    [26.36, -0.1, 12, 3],
    [12.5, -1.08, 6, 2.5],
    [0, 10.9, 69, 0.2],
    [-13.65, -10.9, 41.75, 0.2],
    [20.6, -2.8, 27.6, 0.2],
    [-34.4, 0, 0.2, 21.94],
    [34.4, 4.1, 0.2, 13.8],
    [7.3, -2.45, 0.2, 17.1],
    [-5.09814, -7.46193, 0.5, 7],
    [-28.57, 0, 0.5, 14.71]
]

LOCAL_GRID_PATH = os.path.join(LOGS_DIR, "local_planner_grid.jpg")

CAMERA_FEED_PATH = os.path.join(LOGS_DIR, "camera_feed.jpg")

def load_data():
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        return {}

def main():
    st.title("AGV Real-Time Dynamics Dashboard")
    
    # Settings in sidebar
    st.sidebar.header("Settings")
    fps = st.sidebar.slider("Refresh Rate (FPS)", 1, 60, 30, 1)

    # Pre-allocate containers to avoid flickering
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Robot Dynamics")
        time_placeholder = st.empty()
        
        st.markdown("### Targets")
        w1, w2 = st.columns(2)
        goal_pt_x = w1.empty()
        goal_pt_y = w2.empty()
        
        w3, w4 = st.columns(2)
        next_pt_x = w3.empty()
        next_pt_y = w4.empty()
        
        st.markdown("### Coordinates")
        c1, c2, c3 = st.columns(3)
        state_x = c1.empty()
        state_y = c2.empty()
        state_th = c3.empty()
        
        g1, g2 = st.columns(2)
        gps_x = g1.empty()
        gps_y = g2.empty()
        
        st.markdown("### Tracking Errors")
        e1, e2 = st.columns(2)
        err_d = e1.empty()
        err_h = e2.empty()
        
        st.markdown("### Velocities")
        v1, v2 = st.columns(2)
        cur_vl = v1.empty()
        cur_va = v2.empty()
        
        t1, t2 = st.columns(2)
        tgt_vl = t1.empty()
        tgt_va = t2.empty()

    with col2:
        st.subheader("Live Map")
        map_placeholder = st.empty()
        
        gc1, gc2 = st.columns(2)
        with gc1:
            st.subheader("Live Local Planner Grid")
            grid_placeholder = st.empty()
        with gc2:
            st.subheader("Robot AI Camera")
            camera_placeholder = st.empty()

    while True:
        data = load_data()
        
        if not data:
            map_placeholder.info("No real-time data found. Please ensure the AGV simulation is running and generating data.")
        else:
            time_placeholder.metric(label="Current Time (s)", value=f"{data.get('time', 0.0):.2f}")
            
            goal = data.get('goal_position', {})
            goal_pt_x.metric("Goal X", f"{goal.get('x', 0.0):.2f}")
            goal_pt_y.metric("Goal Y", f"{goal.get('y', 0.0):.2f}")
            
            next_pt = data.get('next_point')
            if next_pt:
                next_pt_x.metric("Next Point X", f"{next_pt.get('x', 0.0):.2f}")
                next_pt_y.metric("Next Point Y", f"{next_pt.get('y', 0.0):.2f}")
            else:
                next_pt_x.metric("Next Point X", "None")
                next_pt_y.metric("Next Point Y", "None")
                
            state = data.get('state', {})
            state_x.metric("State X", f"{state.get('x', 0.0):.2f}")
            state_y.metric("State Y", f"{state.get('y', 0.0):.2f}")
            state_th.metric("State Theta (rad)", f"{state.get('theta', 0.0):.2f}")
            
            gps = data.get('gps', {})
            gps_x.metric("GPS X", f"{gps.get('x', 0.0):.2f}")
            gps_y.metric("GPS Y", f"{gps.get('y', 0.0):.2f}")
            
            errors = data.get('errors', {})
            err_d.metric("Distance Error (m)", f"{errors.get('distance', 0.0):.4f}")
            err_h.metric("Heading Error (rad)", f"{errors.get('heading', 0.0):.4f}")
            
            cur_vel = data.get('current_velocities', {})
            cur_vl.metric("Current Linear (m/s)", f"{cur_vel.get('linear', 0.0):.4f}")
            cur_va.metric("Current Angular (rad/s)", f"{cur_vel.get('angular', 0.0):.4f}")
            
            tgt_vel = data.get('target_velocities', {})
            tgt_vl.metric("Target Linear (m/s)", f"{tgt_vel.get('linear', 0.0):.4f}")
            tgt_va.metric("Target Angular (rad/s)", f"{tgt_vel.get('angular', 0.0):.4f}")

            # Plot map
            fig, ax = plt.subplots(figsize=(10, 6))
            
            for name, coord in POINTS.items():
                if 'Dropoff' in name:
                    color = 'green'
                    marker = 's'
                elif 'Pickup' in name:
                    color = 'blue'
                    marker = 'p'
                else:
                    color = 'orange'
                    marker = 'D'
                
                ax.scatter(coord[0], coord[1], c=color, s=100, marker=marker)
                
                # Plot the real name index
                label = name.split()[-1] if name != "Charging Station" else ""
                ax.text(coord[0], coord[1]+0.5, label, fontsize=10, ha='center', fontweight='bold')
                
            # Fixed Obstacles
            import matplotlib.patches as patches
            for obs in OBSTACLES:
                cx, cy, w, h = obs
                rect = patches.Rectangle((cx - w/2, cy - h/2), w, h, linewidth=1, edgecolor='black', facecolor='gray', alpha=0.5)
                ax.add_patch(rect)
                
            # Robot Position
            rx = state.get('x', 0.0)
            ry = state.get('y', 0.0)
            ax.scatter(rx, ry, c='red', s=200, marker='o', edgecolors='black', linewidth=2, label="AGV")
            
            import numpy as np
            theta = state.get('theta', 0.0)
            ax.plot([rx, rx + 1.5 * np.cos(theta)], [ry, ry + 1.5 * np.sin(theta)], color='red', linewidth=3)
            
            goal = data.get('goal_position')
            if goal:
                ax.scatter(goal['x'], goal['y'], c='purple', s=200, marker='X', label="Current Goal")

            ax.set_xlabel("X coordinate")
            ax.set_ylabel("Y coordinate")
            ax.set_title("AGV Live Position relative to Waypoints")
            ax.grid(True, linestyle='--', alpha=0.7)
            
            ax.set_xlim(-34.5, 34.5)
            ax.set_ylim(-11, 11)
            
            from matplotlib.lines import Line2D
            legend_elements = [
                Line2D([0], [0], marker='o', color='w', label='AGV', markerfacecolor='red', markersize=12),
                Line2D([0], [0], marker='s', color='w', label='Dropoff', markerfacecolor='green', markersize=10),
                Line2D([0], [0], marker='p', color='w', label='Pickup', markerfacecolor='blue', markersize=10),
                Line2D([0], [0], marker='D', color='w', label='Charging Station', markerfacecolor='orange', markersize=10),
                Line2D([0], [0], marker='X', color='w', label='Current Goal', markerfacecolor='purple', markersize=12)
            ]
            ax.legend(handles=legend_elements, loc="upper right", bbox_to_anchor=(1.25, 1))
            ax.set_aspect('equal')
            plt.tight_layout()
            
            # Update placeholders
            map_placeholder.pyplot(fig)
            plt.close(fig)
            
            # Local grid & Camera Feed
            if os.path.exists(LOCAL_GRID_PATH):
                try:
                    with open(LOCAL_GRID_PATH, "rb") as f:
                        grid_placeholder.image(f.read(), use_container_width=True)
                except Exception:
                    pass
            
            if os.path.exists(CAMERA_FEED_PATH):
                try:
                    with open(CAMERA_FEED_PATH, "rb") as f:
                        camera_placeholder.image(f.read(), use_container_width=True)
                except Exception:
                    pass

        time.sleep(1.0 / fps)

if __name__ == "__main__":
    main()
