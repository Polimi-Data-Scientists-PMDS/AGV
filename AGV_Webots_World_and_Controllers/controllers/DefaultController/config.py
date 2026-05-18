# config.py
import json
import os
import numpy as np
from dataclasses import dataclass, field


DEFAULT_CONTROLLER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(DEFAULT_CONTROLLER_DIR, "..", "..", ".."))
LOGGER_DIR = os.path.join(PROJECT_ROOT, "logging", "logger")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logging", "logs")

@dataclass(frozen=True)
class WorldConfig:
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
        {"def_name": "HUMAN_1", "amplitude": -8.5, "speed": 1, "axis": 'y'},
        {"def_name": "HUMAN_2", "amplitude": 7.0, "speed": 1, "axis": 'x'},
        {"def_name": "HUMAN_3", "amplitude": -14.0, "speed": 1, "axis": 'y'},
        {"def_name": "HUMAN_4", "amplitude": -17.0, "speed": 1, "axis": 'x'},
        {"def_name": "HUMAN_5", "amplitude": -6.0, "speed": 1, "axis": 'y'},
        {"def_name": "HUMAN_6", "amplitude": 14.0, "speed": 1, "axis": 'x'},
        {"def_name": "HUMAN_7", "amplitude": 8.0, "speed": 1, "axis": 'y'},
        
        # Forklifts
        {"def_name": "FORKLIFT_1", "amplitude": 13.0, "speed": 1.5, "axis": 'x'},
        {"def_name": "FORKLIFT_2", "amplitude": 40.0, "speed": 1.5, "axis": 'x'},
        {"def_name": "FORKLIFT_3", "amplitude": 13.0, "speed": 1.5, "axis": 'y'},
        {"def_name": "FORKLIFT_4", "amplitude": -12.0, "speed": 1.5, "axis": 'y'},
    ]


@dataclass(frozen=True)
class PhysicalConfig:
    wheel_base: float = 0.33            # (m)
    wheel_radius: float = 0.0975        # (m)
    max_wheel_speed: float = 12.3       # (rad/s)

@dataclass(frozen=True)
class PerceptionConfig:
    encoder_thresh = 1e-5

@dataclass(frozen=True)
class VisionConfig:
    enable_object_detection = False
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
    
    unknown = 0
    free = 128
    padding = 200
    occupied = 255

    # A*
    free_cost = 1.0
    unknown_cost = 1.5
    padding_cost = 50.0
    heuristic_weight = 2

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




