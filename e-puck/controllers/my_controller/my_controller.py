"""my_controller controller."""

# You may need to import some classes of the controller module. Ex:
#  from controller import Robot, Motor, DistanceSensor
from controller import Robot
import numpy as np 

# create the Robot instance.
robot = Robot()

# get the time step of the current world.
timestep = int(robot.getBasicTimeStep())

# You should insert a getDevice-like function in order to get the
# instance of a device of the robot. Something like:
#  motor = robot.getDevice('motorname')
# ds = robot.getDevice('dsname')
#  ds.enable(timestep)

motorL = robot.getDevice('left wheel motor')
motorR = robot.getDevice('right wheel motor')

# Set the motors to rotate indefinitely for velocity control
motorL.setPosition(float('inf'))
motorR.setPosition(float('inf'))

# Set the target velocity (e.g., 50% of max speed which is 2*pi)
MAX_SPEED = 6.28
speed = 0.5 * MAX_SPEED

# Main loop:
# - perform simulation steps until Webots is stopping the controller
while robot.step(timestep) != -1:
    # Read the sensors:
    # Enter here functions to read sensor data, like:
    # val = ds.getValue()

    
    if robot.getTime() < 10.0:
        motorL.setVelocity(0.0)
    else:
        motorL.setVelocity(speed)
    motorR.setVelocity(speed)

    # Process sensor data here.

    # Enter here functions to send actuator commands, like:
    #  motor.setPosition(10.0)
    pass

# Enter here exit cleanup code.
