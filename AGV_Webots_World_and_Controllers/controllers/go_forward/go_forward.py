"""my_controller controller."""

from controller import Robot # type: ignore
#Error due to library used by webots and not imported locally
import numpy as np 
import time

robot = Robot()
timestep = int(robot.getBasicTimeStep())

left_motor = robot.getDevice("left wheel motor")
right_motor = robot.getDevice("right wheel motor")

# velocity control mode
left_motor.setPosition(float('inf'))
right_motor.setPosition(float('inf'))

# stop first
left_motor.setVelocity(0.0)
right_motor.setVelocity(0.0)

speed = 6.0  # rad/s

while robot.step(timestep) != -1:
    left_motor.setVelocity(speed)
    right_motor.setVelocity(speed)