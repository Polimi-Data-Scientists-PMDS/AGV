# config.py
import os
import numpy as np
from dataclasses import dataclass


DEFAULT_CONTROLLER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(DEFAULT_CONTROLLER_DIR, "..", "..", ".."))
LOGGER_DIR = os.path.join(PROJECT_ROOT, "logging", "logger")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logging", "logs")

# Dashboard selector. Keep False to launch the Streamlit dashboard in web-app/app.py.
# Set True to launch the React dashboard in web-app/app.tsx.
use_react = False

@dataclass(frozen=True)
class WorldConfig:
    goals = {
        "CHARGING_STATION": (6.75, -4.5),
        "DROPOFF_01": (-29.3, 4),
        "PICKUP_01": (-24, 3.5),
        "PICKUP_02": (-18.5, 6.25),
        "PICKUP_03": (-13.5, 6.25),
        "PICKUP_04": (-8.25, 4.5),
        "PICKUP_05": (-2, 5.75),
        "PICKUP_06": (3.75, 5.75),
        "PICKUP_07": (18.75, 2.25),
    }

    # Fixed Obstacles (Work Islands & Walls) [center_x, center_y, width, height]
    fixed_obstacles = [
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

    dynamic_obstacles = [
        # Humans
        {"def_name": "HUMAN_1", "amplitude": -8.5, "speed": 0.25, "axis": 'y'},
        {"def_name": "HUMAN_2", "amplitude": 7.0, "speed": 0.25, "axis": 'x'},
        {"def_name": "HUMAN_3", "amplitude": -14.0, "speed": 0.25, "axis": 'y'},
        {"def_name": "HUMAN_4", "amplitude": -17.0, "speed": 0.25, "axis": 'x'},
        {"def_name": "HUMAN_5", "amplitude": -6.0, "speed": 0.25, "axis": 'y'},
        {"def_name": "HUMAN_6", "amplitude": 14.0, "speed": 0.25, "axis": 'x'},
        {"def_name": "HUMAN_7", "amplitude": 8.0, "speed": 0.25, "axis": 'y'},
        
        # Forklifts
        {"def_name": "FORKLIFT_1", "amplitude": 13.0, "speed": 0.3, "axis": 'x'},
        {"def_name": "FORKLIFT_2", "amplitude": 40.0, "speed": 0.3, "axis": 'x'},
        {"def_name": "FORKLIFT_3", "amplitude": 13.0, "speed": 0.3, "axis": 'y'},
        {"def_name": "FORKLIFT_4", "amplitude": -12.0, "speed": 0.3, "axis": 'y'},
    ]


@dataclass(frozen=True)
class PhysicalConfig:
    wheel_base: float = 0.33            # (m)
    wheel_radius: float = 0.0975        # (m)
    max_wheel_speed: float = 12.3       # (rad/s)
    lidar_height: float = 0.8           # (m)
    camera_height: float = 1.2          # (m) mounting height above ground
    camera_fov = 1.5                    # (radians)
    camera_width_px = 640               # (pixels)
    camera_height_px = 480              # (pixels)
    lidar_max_range = 25.0              # (m)


@dataclass(frozen=True)
class PerceptionConfig:
    encoder_thresh = 1e-5

@dataclass(frozen=True)
class VisionConfig:
    enable_object_detection = True
    yolo_model = "yolov8n.pt"
    yolo_thresh = 0.4
    
@dataclass(frozen=True)
class ControlConfig:
    heading_p_gain = 0.6                     # Heading PID gain
    max_lin_vel = 0.4                   # (m/s)
    max_ang_vel = 1.0                   # (rad/s)
    ang_vel_deadzone = 0.05             # (rad/s)
    

@dataclass(frozen=True)
class PlanningConfig:
    goal_reached_thresh = 1
    global_map_res = 0.2
    world_width = 80.0   # (m) Total width of your simulated/real world
    world_height = 80.0  # (m) Total height of your simulated/real world
    tolerance_m = 0.4    # (m) How close a LiDAR hit can be to a wall to 

@dataclass(frozen=True)
class HighLevelPlanningConfig(PlanningConfig):
    goal_reached_thresh = 1
    collision_distance = 0.25

@dataclass(frozen=True)
class VisGraphPlanningConfig(HighLevelPlanningConfig):
    inflation = 0.8
    change_goal_thresh = 1
    
@dataclass(frozen=True)
class LowLevelPlanningConfig(PlanningConfig):
    goal_reached_thresh = 1
    collision_distance = 0.25
    
@dataclass(frozen=True)
class GridPlanningConfig(LowLevelPlanningConfig):
    vision_distance = 10    # (m)
    padding_size = 0.8
    grid_res = 0.2         # (m)
    grid_cells = int(np.ceil(vision_distance / grid_res))   
    padding_pixels = int(np.ceil(padding_size / grid_res)) 

    noise_tolerance = 1 
    
    unknown = -1
    free = 0
    occupied = 1
    padding = 2

    unknown_color = (0, 0, 0)          
    free_color = (128, 128, 128)   
    padding_color = (200, 200, 200)   
    occupied_color = (255, 255, 255)  
    walls_color = (0, 165, 255)   

    # A*
    free_cost = 1.0
    unknown_cost = 1.5
    padding_cost = 50.0
    heuristic_weight = 2

@dataclass(frozen=True)
class ObstacleTrackingConfig:
    """Tunables for the moving-obstacle pipeline: cluster -> track -> label -> pad.
    Pixel values refer to the local planning grid (GridPlanningConfig.grid_res)."""

    # --- Clustering (grouping LiDAR hits into objects) ---
    cluster_dilation_px = 1         # merges adjacent hits / closes 1-px gaps
    cluster_min_pixels = 3          # blobs smaller than this are noise
    cluster_max_radius_m = 2.5      # bigger blobs are wall fragments, not objects

    # --- Tracking (following objects across frames) ---
    assoc_gate_m = 1.0              # max match distance between track and new cluster
    max_unseen_frames = 8           # frames a lost track coasts before deletion
    min_frame_dt = 0.02             # (s) lower bound on frame delta
    history_len = 20                # position samples kept per track (~2s at 10Hz)
    velocity_min_samples = 3        # samples needed before estimating velocity
    velocity_min_baseline_s = 0.15  # (s) minimum elapsed time for a velocity estimate
    confirm_frames = 3              # sightings needed before a track is trusted
    moving_speed_thresh = 0.15      # (m/s) faster than this counts as "moving"
    heading_min_speed = 0.05        # (m/s) below this, heading is not updated

    # --- YOLO labeling ---
    label_stickiness = 0.85         # 0..1, higher = harder to flip an established label

    # --- Padding (costmap inflation) ---
    obstacle_padding_m = 0.9        # fixed MARGIN inflating the object's actual shape
    prediction_lookahead_s = 1.0    # (s) shape stamped again this far ahead of moving obstacles

    # --- Visualization ---
    arrow_lookahead_s = 1.0         # (s) arrow length = predicted travel in this time
    arrow_min_len_px = 14           # (display px) floor so slow motion is still visible
    arrow_max_len_frac = 0.25       # cap as fraction of display size
    arrow_color = (139, 0, 0)       # BGR dark blue
    person_color = (255, 0, 255)    # BGR magenta
    forklift_color = (0, 255, 255)  # BGR yellow
    unknown_track_color = (255, 255, 0)  # BGR cyan


@dataclass(frozen=True)
class SectorPlanningConfig(LowLevelPlanningConfig):
    num_sectors = 32
    padding = 3
    vision_distance = 2.0                # (m)
    safe_distance = 2.0                  # (m)
    visualize = True
    
    
@dataclass(frozen=True)
class LogConfig:
    log_interval = 5.0      # s
    print_interval = 0.5    # s







