"""my_controller controller."""

from controller import Robot 
#Error due to library used by webots and not imported locally
import numpy as np 
import time

DISTANCE_BETWEEN_WHEELS = 0.052 #(m) distance between wheels found in the robot manual
WHEEL_RADIUS = 0.02 #(m) wheel radius found in the robot manual
MAX_WHEEL_SPEED = 50 #(rad/s) actual max speed is 100, this setting is to not overspeed the robot

# Function to set the wheel velocity
def set_wheel_velocity(lin_vel, ang_vel):
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

# create the Robot instance
robot = Robot()
# get the time step of the current world
timestep = int(robot.getBasicTimeStep()) #(ms) currently timestep is 1ms
# Get motor devices
motorL = robot.getDevice('left wheel motor')
motorR = robot.getDevice('right wheel motor')

# Setup distance sensor 
ds1 = robot.getDevice('distance_sensor_1')
# enable distance sensor with in order to have a good precision
ds1.enable(timestep)

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
    # Read distance sensor value
    dist = ds1.getValue()

    # Read lidar values
    raw_range_image = ls1.getRangeImage() # List of SP floats what describe the range
    clean_range_image = [x if x != float('inf') else lidar_max_range for x in raw_range_image] # Remove inf values
    # Split the list in three sectors (right, center, left) and get minimum of each secor
    left_sector = np.array(clean_range_image[0 : sector_size])
    center_sector = np.array(clean_range_image[sector_size : 2*sector_size])
    right_sector = np.array(clean_range_image[2*sector_size : 3*sector_size])
    left_min = np.min(left_sector)
    center_min = np.min(center_sector)
    right_min = np.min(right_sector)

    current_time = robot.getTime()
    #Print sensor values every 0.5 seconds
    if current_time - last_print_time >= 0.5:
        # Print distance sensor value
        print(f"The distance mesured by the distance sensor 1 at time {current_time}s is: {dist}mm")
        # Print lidar values
        print(f"Lidar values: L: {left_min}, C: {center_min}, R: {right_min}")
        # Get wheel speed and print it
        w_r = motorR.getVelocity()
        w_l = motorL.getVelocity()
        print(f"Wheel speeds: L: {w_l}, R: {w_r}")
        # Update last print time
        last_print_time = current_time
    
    # Lidar obstacle avoidance
    # In a dead end > reverse
    if center_min < 0.1 and right_min < 0.05 and left_min < 0.05:
        set_wheel_velocity(0, 10)
        time_to_target = 0.0
    # Close object in front > turn
    elif center_min < 0.2:
        if right_min > left_min:
            set_wheel_velocity(HARD_TURN_SPEED, -7.5) #turn left
        else:
            set_wheel_velocity(HARD_TURN_SPEED, 7.5) #turn right
        time_to_target = 0.0
    # Object in front > slow down 
    elif center_min < 0.35:
        current_speed = get_current_linear_speed()
        time_to_target += 0.005
        new_speed = acc_speed(HARD_TURN_SPEED, current_speed, OBSTACLE_DECELERATION_TIME, time_to_target)
        set_wheel_velocity(new_speed, 0)
    # Object on the right 
    elif right_min < 0.15 and right_min < left_min:
        set_wheel_velocity(TURN_SPEED, -3) #small turn left
    # Object on the left
    elif left_min < 0.15 and left_min < right_min:
        set_wheel_velocity(TURN_SPEED, 3) #small turn right
    # No obstacle (+ acceleration)
    else:
        current_speed = get_current_linear_speed()
        if current_speed < CRUISE_SPEED:
            time_to_target += 0.01 #faster acceleration vs dec.
            new_speed = acc_speed(CRUISE_SPEED, current_speed, OBSTACLE_DECELERATION_TIME, time_to_target)
            set_wheel_velocity(new_speed, 0)
        else:
            time_to_target = 0.0
            set_wheel_velocity(CRUISE_SPEED, 0)

    pass

# Enter here exit cleanup code.


"""
OLD DISTANCE SENSOR OBSTACLE AVOIDANCE   
    # Simple obstacle avoidance with deceleration and acceleration
    if dist < 500:
        set_wheel_velocity(0.1, -5)
        time_to_target = 0.0
    elif dist < 750: 
        current_speed = get_current_linear_speed()
        time_to_target += 0.010
        new_speed = acc_speed(0.1, current_speed, OBSTACLE_DECELERATION_TIME, time_to_target)
        set_wheel_velocity(new_speed, 0)
    else:
        current_speed = get_current_linear_speed()
        if current_speed < 0.1:
            time_to_target += 0.010
            new_speed = acc_speed(0.1, current_speed, OBSTACLE_DECELERATION_TIME, time_to_target)
            set_wheel_velocity(new_speed, 0)
        else:
            time_to_target = 0.0
            set_wheel_velocity(0.1, 0)
"""