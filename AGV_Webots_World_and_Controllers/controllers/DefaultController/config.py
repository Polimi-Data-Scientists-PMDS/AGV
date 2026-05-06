# config.py
import os
import numpy as np
from dataclasses import dataclass

DEFAULT_CONTROLLER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(DEFAULT_CONTROLLER_DIR, "..", "..", ".."))
LOGGER_DIR = os.path.join(PROJECT_ROOT, "logging", "logger")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logging", "logs")

@dataclass(frozen=True)
class TaskConfig:
    # List of targets
    CHARGING_STATION = (6.75, -4.5)
    DROPOFF_01 = (-29.3, 4)
    PICKUP_01 = (-24, 3.5)
    PICKUP_02 = (-18.5, 6.25)
    PICKUP_03 = (-13.5, 6.25)
    PICKUP_04 = (-8.25, 4.5)
    PICKUP_05 = (-2, 5.75)
    PICKUP_06 = (3.75, 5.75)
    PICKUP_07 = (18.75, 2.25)

    goal_positions = [
        # PICKUP_07,          # Pickup point 7
        # CHARGING_STATION,   # Charging station
        DROPOFF_01,         # Dropoff point 01
        PICKUP_03,          # Pickup point 3
        PICKUP_04,          # Pickup point 4
        CHARGING_STATION,   # Charging station
        PICKUP_01,          # Pickup point 1
        DROPOFF_01,         # Dropoff point 01
        PICKUP_02,          # Pickup point 2
        PICKUP_05,          # Pickup point 5
        PICKUP_06,          # Pickup point 6
        DROPOFF_01,         # Dropoff point 01
        PICKUP_07,          # Pickup point 7
        CHARGING_STATION,   # Charging station
    ]

@dataclass(frozen=True)
class WorldConfig:
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
    collision_distance = 0.25
    
@dataclass(frozen=True)
class GridPlanningConfig(PlanningConfig):
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
class SectorPlanningConfig(PlanningConfig):
    num_sectors = 32
    padding = 3
    vision_distance = 2.0                # (m)
    safe_distance = 2.0                  # (m)
    visualize = True
    
    
@dataclass(frozen=True)
class LogConfig:
    log_interval = 5.0      # s
    print_interval = 0.5    # s








