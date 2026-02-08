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
ds1.enable(10*timestep)


# Set the motors to rotate indefinitely for velocity control
motorL.setPosition(float('inf'))
motorR.setPosition(float('inf'))

# Variables for printing the sensor value every 1 second 
last_print_time = 0.0

# Create variable to not have inst. acceleration
count = -1

# Main loop:
# - perform simulation steps until Webots is stopping the controller
while robot.step(timestep) != -1:
    # Read and print the sensor value every 1 second 
    current_time = robot.getTime()
    dist = ds1.getValue()
    if current_time - last_print_time >= 0.5:
        print(f"The distance mesured by the distance sensor 1 at time {current_time}s is: {dist}")
        last_print_time = current_time
        # Get wheel speed and print it
        w_r = motorR.getVelocity()
        w_l = motorL.getVelocity()
        print(f"Wheel speeds: L: {w_l}, R: {w_r}")

    # Simple obstacle avoidance with deceleration and acceleration
    if dist < 500:
        set_wheel_velocity(0.25, -5)
        count = 50
    elif dist < 750 and count == -1: 
        set_wheel_velocity(0.5, -1.5)
    elif count >= 0:
        set_wheel_velocity(0.5, -1.5)
        count -= 1
    else:
        set_wheel_velocity(0.75, -1.5)

    pass

# Enter here exit cleanup code.





