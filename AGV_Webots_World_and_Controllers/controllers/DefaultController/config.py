# config.py

class RobotConfig:
    # 0. FEATURES
    ENABLE_OBJECT_DETECTION = False

    # 1. PHYSICAL ROBOT SPECS
    DISTANCE_BETWEEN_WHEELS = 0.33      # (m)
    WHEEL_RADIUS = 0.0975               # (m)
    MAX_WHEEL_SPEED = 12.3              # (rad/s)
    
    # 2. CONTROL & KINEMATICS
    K_DISTANCE = 0.5                    # Distance PID gain
    K_HEADING = 0.6                     # Heading PID gain
    MAX_LIN_VEL = 0.4                   # (m/s)
    MAX_ANG_VEL = 1.0                   # (rad/s)
    ANG_VEL_DEADZONE = 0.05             # (rad/s)
    ENCODER_THRESH = 1e-5               # (m)
    GOAL_REACHED_THRESH = 0.1           # (m)
    
    # 3. PERCEPTION & AVOIDANCE
    CONTROL_VISION_DISTANCE = 2.0       # (m)
    SAFE_DISTANCE = 2.0                 # (m)
    COLLISION_DISTANCE = 0.2            # (m)
    NUM_SECTORS = 32
    PADDING = 3
    
    # 4. SIMULATION
    LOG_INTERVAL_SEC = 5.0
    PRINT_INTERVAL_SEC = 0.5

    # 5. VISUALIZATIONS 
    PRINT_OBSTACLE_AVOIDANCE = True


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
GOAL_POSITIONS = [
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



DYNAMIC_OBSTACLES = [
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

