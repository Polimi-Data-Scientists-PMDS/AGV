"""my_controller controller."""

from controller import Robot # type: ignore
#Error due to library used by webots and not imported locally
import numpy as np 
import time
import os
from log.RobotLog import RobotLog

DISTANCE_BETWEEN_WHEELS = 0.052 #(m) distance between wheels found in the robot manual
WHEEL_RADIUS = 0.02 #(m) wheel radius found in the robot manual
MAX_WHEEL_SPEED = 12.3 #(rad/s) actual max speed is 100, this setting is to not overspeed the robot


# Function to set the wheel velocity
def robot_to_wheel_velocity(lin_vel, ang_vel):
    # from set linear and angular velocity to wheel linear velocity
    v_r = lin_vel + 0.5 * ang_vel * DISTANCE_BETWEEN_WHEELS
    v_l = lin_vel - 0.5 * ang_vel * DISTANCE_BETWEEN_WHEELS

    # linear -> angular (rad/s)
    w_r = v_r / WHEEL_RADIUS
    w_l = v_l / WHEEL_RADIUS

    # saturation to preserve curvature
    scale = max(abs(w_l), abs(w_r)) / MAX_WHEEL_SPEED

    if scale > 1.0:
        w_l /= scale
        w_r /= scale

    #print(f"Giving motor velocities: L: {w_l}, R: {w_r}")
    
    # set motor velocity
    motorL.setVelocity(w_l)
    motorR.setVelocity(w_r)

# Function to get the current linear speed
def get_current_linear_speed():
    w_r = motorR.getVelocity()
    w_l = motorL.getVelocity()
    v_r = w_r * WHEEL_RADIUS
    v_l = w_l * WHEEL_RADIUS
    lin_vel = (v_r + v_l) / 2
    return lin_vel

# Function for linear acceleration
def acc_speed(target_speed, current_speed, delta_time, time_to_target):
    if current_speed <= target_speed:
        delta_vel = (target_speed - current_speed) / delta_time
    elif current_speed > target_speed:
        delta_vel = (target_speed - current_speed) / delta_time
    return current_speed + delta_vel*time_to_target


def read_lidar_image(lidar):
    raw_range_image = lidar.getRangeImage() # List of SP floats what describe the range
    clean_range_image = [x if x != float('inf') else lidar_max_range for x in raw_range_image] # Remove inf values
    # Split the list in three sectors (right, center, left) and get minimum of each secor
    left_sector = np.array(clean_range_image[0 : sector_size])
    center_sector = np.array(clean_range_image[sector_size : 2*sector_size])
    right_sector = np.array(clean_range_image[2*sector_size : 3*sector_size])
    return left_sector, center_sector, right_sector

def get_angle(x, y):
    # Get GPS values
    gps_values = gps.getValues()
    # Calculate the angle to the target point
    angle = np.arctan2(y - gps_values[1], x - gps_values[0])
    return angle

    
# create the Robot instance
robot = Robot()
# get the time step of the current world
timestep = int(robot.getBasicTimeStep()) #(ms) currently timestep is 1ms
# Get motor devices
motorL = robot.getDevice('left wheel motor')
motorR = robot.getDevice('right wheel motor')

# Set the motors to rotate indefinitely for velocity control
motorL.setPosition(float('inf'))
motorR.setPosition(float('inf'))

# Setup lidar sensor
ls1 = robot.getDevice('Lidar1')
ls1.enable(timestep)
# Get and print lidar constraints
lidar_fov = ls1.getFov()
lidar_width = ls1.getHorizontalResolution()
lidar_max_range = ls1.getMaxRange()
print(f"Lidar FOV: {lidar_fov} radians ({lidar_fov*180/np.pi} degrees), horizontal resolution: {lidar_width} points, max range: {lidar_max_range}m")
sector_size = lidar_width // 3
raw_range_image = []
clean_range_image = []
right_sector = []
center_sector = []
left_sector = []
right_min = 0
center_min = 0
left_min = 0

# Setup GPS sensor
gps = robot.getDevice('gps')
gps.enable(timestep)
print(f"GPS Coordinate System: {gps.getCoordinateSystem()}")


# Robot log setup
log_file_path = os.path.join(os.path.dirname(__file__), 'robot_history.jsonl')
robot_log = RobotLog(log_file_path)
robot_log.start(robot.getTime())

# Variables for printing the sensor value every 1 second 
last_print_time = -0.5
current_time = 0.0

# Speed constants
CRUISE_SPEED = 0.4 #(m/s)
TURN_SPEED = 0.35 #(m/s)
HARD_TURN_SPEED = 0.2 #(m/s)

# Variables for acceleration
OBSTACLE_DECELERATION_TIME = 1 #(s)
time_to_target = 0.0

# Main loop:
# - perform simulation steps until Webots is stopping the controller
while robot.step(timestep) != -1:
    # Read lidar values
    left_sector, center_sector, right_sector = read_lidar_image(ls1)
    left_min = np.min(left_sector)
    center_min = np.min(center_sector)
    right_min = np.min(right_sector)

    # Get GPS values
    gps_values = gps.getValues()

    current_time = robot.getTime()
    current_linear_speed = get_current_linear_speed()

    # Update time + idle stats
    robot_log.update(current_time, current_linear_speed)

    # Update obstacle encounter stats (count only transition into obstacle state)
    has_obstacle = (center_min < 0.35) or (left_min < 0.15) or (right_min < 0.15) #! if any of the three sectors has a minimum distance below the threshold, then we consider to be in an obstacle state
    obstacle_details = f"L={left_min:.3f}, C={center_min:.3f}, R={right_min:.3f}"
    robot_log.update_obstacle_state(current_time, has_obstacle, obstacle_details)
    #Print sensor values every 0.5 seconds
    if current_time - last_print_time >= 0.5:
        # Print distance sensor value
        print(f"Time: {current_time}s")
        # Print lidar values
        print(f"Lidar values: L: {left_min}, C: {center_min}, R: {right_min}")
        # Print GPS values
        print(f"GPS values: {gps_values}")
        # Get wheel speed and print it
        w_r = motorR.getVelocity()
        w_l = motorL.getVelocity()
        print(f"Wheel speeds: L: {w_l}, R: {w_r}")
        # Update last print time
        last_print_time = current_time

    if gps_values[0] > 0.45 and gps_values[1] > 0.45 and gps_values[0] < 0.55 and gps_values[1] < 0.55:
        robot_to_wheel_velocity(0, 0)
        robot_log.log_event(current_time, "TARGET_REACHED", "Robot reached target area")
        print("Target reached!")
        break
    
    angle = get_angle(0.5, 0.5)
    
    # Lidar obstacle avoidance
    # In a dead end > reverse
    if center_min < 0.1 and right_min < 0.05 and left_min < 0.05:
        robot_to_wheel_velocity(0, 10)
        time_to_target = 0.0
    # Close object in front > turn
    elif center_min < 0.2:
        if right_min > left_min:
            robot_to_wheel_velocity(HARD_TURN_SPEED, -7.5) #turn left
        else:
            robot_to_wheel_velocity(HARD_TURN_SPEED, 7.5) #turn right
        time_to_target = 0.0
    # Object in front > slow down 
    elif center_min < 0.35:
        current_speed = get_current_linear_speed()
        time_to_target += 0.005
        new_speed = acc_speed(HARD_TURN_SPEED, current_speed, OBSTACLE_DECELERATION_TIME, time_to_target)
        robot_to_wheel_velocity(new_speed, angle)
    # Object on the right 
    elif right_min < 0.15 and right_min < left_min:
        if angle > 0:
            angle = -3
        robot_to_wheel_velocity(TURN_SPEED, angle) #small turn left
    # Object on the left
    elif left_min < 0.15 and left_min < right_min:
        if angle < 0:
            angle = 3
        robot_to_wheel_velocity(TURN_SPEED, angle) #small turn right
    # No obstacle (+ acceleration)
    else:
        current_speed = get_current_linear_speed()
        if current_speed < CRUISE_SPEED:
            time_to_target += 0.01 #faster acceleration vs dec.
            new_speed = acc_speed(CRUISE_SPEED, current_speed, OBSTACLE_DECELERATION_TIME, time_to_target)
            robot_to_wheel_velocity(new_speed, angle)
        else:
            time_to_target = 0.0
            robot_to_wheel_velocity(CRUISE_SPEED, angle)

# Enter here exit cleanup code.
robot_log.log_event(robot.getTime(), "STOP", "Controller stopped")
robot_log.save()
print(f"Robot history saved in: {log_file_path}")

