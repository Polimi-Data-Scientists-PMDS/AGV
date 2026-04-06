# config.py

class RobotConfig:
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