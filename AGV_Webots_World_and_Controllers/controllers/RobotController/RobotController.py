"""my_controller controller."""

from controller import Robot  # type: ignore
#Error due to library used by webots and not imported locally
from dataclasses import dataclass
import os
import sys
import numpy as np 
import time
import math


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "log"))
if LOG_DIR not in sys.path:
    sys.path.append(LOG_DIR)

from RobotLog import RobotLog  # type: ignore


def main():
    controller = RobotController()
    controller.set_goal_position((4, -4))
    try:
        while controller.is_alive():
            """
                1. CHECK IF GOAL IS REACHED
                    IF YES: LOAD NEXT GOAL OR STOP
            
                2. UPDATE THE STATE

                3. CALCULATE HEADING ERRORS TO THE GOAL
                    distance error is capped to 2m for better control and obstacle avoidance

                4. CHECK IF THERE ARE OBSTACLES ALONG THE LOCAL PATH
                    (check if the path from the robot to the local goal (2m from it) is free)
                    IF THERE ARE OBSTACLES: ADJUST THE GOAL (heading error)

                5. SEND FINAL ERRORS (position and heading) TO THE CONTROL
            """
            # 1. CHECK IF GOAL IS REACHED
            if controller.goal_position is not None and controller.has_reached_goal():
                controller.set_goal_position(None)
                print("GOAL REACHED!")

            # 2. UPDATE THE STATE
            controller.state_update()

            # 3. CALCULATE HEADING ERRORS TO THE GOAL
            distance_error, heading_error = controller.get_control_errors()

            # 4. CHECK IF THERE ARE OBSTACLES ALONG THE LOCAL PATH
            left_min, center_min, right_min = controller.read_lidar()
            has_obstacle = min(left_min, center_min, right_min) <= 0.2
            # TODO: check if the path from the robot to the local goal (2m from it) is free
            

            # 5. SEND FINAL ERRORS (position and heading) TO THE CONTROL
            lin_vel, ang_vel = controller.calculate_velocity(distance_error, heading_error)
            controller.set_robot_velocity(lin_vel, ang_vel)

            # LOGGING
            sim_time = controller.robot.getTime()
            controller.logger.update_obstacle_state(
                sim_time,
                has_obstacle,
                f"L={left_min:.3f}, C={center_min:.3f}, R={right_min:.3f}",
            )
            controller.logger.update(sim_time, lin_vel)

            # OUTPUT & PRINTING
            if controller.should_print():
                print("---------------------")
                if controller.has_reached_goal():
                    print("GOAL REACHED!")
                print(f"\nTime: {controller.robot.getTime()}s")
                # Print lidar values
                #print(f"Lidar values: L: {left_min}, C: {center_min}, R: {right_min}")
                # Print GPS values
                # print(f"GPS values: {gps_values}")
                # Get wheel speed and print it
                w_l, w_r = controller.get_wheel_velocity()
                lin_vel, ang_vel = controller.get_robot_velocity()
                print(f"\nWheel speeds:\n L: {w_l} rad/s, R: {w_r} rad/s")
                print(f"\nRobot speed:\n linear: {lin_vel} m/s, angular: {ang_vel} rad/s")
                if controller.goal_position is not None:
                    print(f"Goal position: \n x: {controller.goal_position.x} \n y: {controller.goal_position.y}")
                else:
                    print("Goal position: None")
                print(f"Current Robot state: \n x: {controller.state.x:.3f} \n y: {controller.state.y:.3f} \n th: {controller.state.theta:.3f}")
                print(f"Errors: \n rho: {distance_error:.3f} \n alpha: {heading_error:.3f}")

    
    finally:
        controller.logger.log_event(controller.robot.getTime(), "STOP", "Controller stopped")
        controller.logger.save()


@dataclass
class Position:
    x: float
    y: float

@dataclass
class State:
    x: float
    y: float
    theta: float

    def calculate_errors(self, goal: Position):
        """ Compute distance and heading errors to a goal position.
            Returns:
                rho (float): Euclidean distance to the goal.
                alpha (float): Heading error to the goal, wrapped to [-pi, pi].
        """
        if goal is None:
            return 0, 0
        dx = goal.x - self.x
        dy = goal.y - self.y
        rho = np.sqrt(np.square(dx) + np.square(dy))    # distance error
        alpha = np.arctan2(dy, dx) - self.theta         # heading error
        alpha = (alpha + np.pi) % (2 * np.pi) - np.pi   # normalized heading error
        return rho, alpha
    
    def update_with_odometry(self, dS, dTheta):
        self.x += dS * np.cos(self.theta)
        self.y += dS * np.sin(self.theta)
        self.theta += dTheta
        self.theta = (self.theta + np.pi) % (2 * np.pi) - np.pi
    
    def fuse_with_gps(self, x, y):
        gps_weight = 1.0
        x = x * gps_weight + self.x * (1 - gps_weight)
        y = y * gps_weight + self.y * (1 - gps_weight)
        self.x = x
        self.y = y


class RobotController:
    def __init__(self):
        # CONSTANTS
        self.DISTANCE_BETWEEN_WHEELS = 0.33 # (m) distance between wheels found in the robot manual
        self.WHEEL_RADIUS = 0.0975 # (m) wheel radius found in the robot manual
        self.MAX_WHEEL_SPEED = 12.3 # (rad/s) actual max speed is 100, this setting is to not overspeed the robot
        self.MAX_VISION_DISTANCE = 2 # (m) distance where the robot can see
        self.K_DISTANCE = 0.5 # distance gain 
        self.K_HEADING = 0.6 # heading gain - TO BE TUNED
        self.MAX_LIN_VEL = 0.4 # (m/s) - TO BE TUNED
        self.MAX_ANG_VEL = 1 # (rad/s) - TO BE TUNED
        self.ANG_VEL_DEADZONE = 0.05 # (rad/s) - TO BE TUNED
        self.ENCODER_THRESH = 1e-5 # (m)
        self.GOAL_REACHED_THRESH = 0.1 # (m)
        # self.TURN_SPEED = 0.35 # (m/s)
        # self.HARD_TURN_SPEED = 0.2 # (m/s)

        # ROBOT
        self.robot = Robot() # Robot instance
        self.initial_timestep = int(self.robot.getBasicTimeStep()) # (ms) currently timestep is 1ms
        
        #self.state = None
        self.state = State(0, 0, 0)
        self.goal_position = None
        self.gps_initial_state = None


        # DEVICES
        # Motors
        self.motorL = self.robot.getDevice('left wheel motor')
        self.motorR = self.robot.getDevice('right wheel motor')
        self.motorL.setPosition(float('inf'))         # setup for velocity control
        self.motorR.setPosition(float('inf'))         # setup for velocity control
        print("Motors set up correctly!")
        # Motor Encoders
        self.posL = self.motorL.getPositionSensor()
        self.posR = self.motorR.getPositionSensor()
        self.posL.enable(self.initial_timestep)
        self.posR.enable(self.initial_timestep)
        self.prevL, self.prevR = 0, 0
        print("Motor encoders set up correctly!")
        # Lidar
        self.lidar = self.robot.getDevice('Lidar1')
        self.lidar.enable(self.initial_timestep)
        print("Lidar set up correctly!")
        print(f"Lidar FOV: {self.lidar.getFov()} radians ({self.lidar.getFov()*180/np.pi} degrees), horizontal resolution: {self.lidar.getHorizontalResolution()} points, max range: {self.lidar.getMaxRange()}m")
        # Gps
        self.gps = self.robot.getDevice('gps')
        self.gps.enable(self.initial_timestep)
        self.gps_initial_state = self.gps.getValues()
        print("GPS set up correctly!")
        print(f"GPS coordinate system: {self.gps.getCoordinateSystem()}")

        # OTHER
        self.last_print_time = 0
        log_file_path = os.path.join(LOG_DIR, "robot_controller_runs.jsonl")
        self.logger = RobotLog(log_file_path)
        self.logger.start(self.robot.getTime())

    
    ##### PERCEPTION #####
    def update_wheel_odometry(self):
        """

        """
        posL = self.posL.getValue()
        posR = self.posR.getValue()
        dL = posL - self.prevL
        dR = posR - self.prevR
        self.prevL = posL
        self.prevR = posR

        # noise treshold
        if abs(dL) < self.ENCODER_THRESH:
            dL = 0
        if abs(dR) < self.ENCODER_THRESH:
            dR = 0

        dS_L = dL * self.WHEEL_RADIUS
        dS_R = dR * self.WHEEL_RADIUS

        dS = (dS_L + dS_R) / 2
        dTheta = (dS_R - dS_L) / self.DISTANCE_BETWEEN_WHEELS
        return dS, dTheta


    def state_update(self):
        # get position and orientation from gps and update the state
        # get delta movement
        dS, dTheta = self.update_wheel_odometry()
        # update state
        self.state.update_with_odometry(dS, dTheta)

        # get gps data
        x, y, _ = self.gps.getValues()
        x -= self.gps_initial_state[0]
        y -= self.gps_initial_state[1]
        # fuse with gps data
        self.state.fuse_with_gps(x, y)

        # dX = x - self.state.x
        # dY = y - self.state.y
        # print(f"GPS coordinates: x: {dX}, y: {dY}")
        # differences.append((dX, dY))

  
        
    def read_lidar(self):
        raw_range_image = self.lidar.getRangeImage() # List of SP floats what describe the range
        clean_range_image = [x if x != float('inf') else self.lidar.getMaxRange() for x in raw_range_image] # Remove inf values
        # Split the list in three sectors (right, center, left) and get minimum of each secor
        sector_size = self.lidar.getHorizontalResolution() // 3
        left_sector = np.array(clean_range_image[0 : sector_size])
        center_sector = np.array(clean_range_image[sector_size : 2*sector_size])
        right_sector = np.array(clean_range_image[2*sector_size : 3*sector_size])
        left_min = np.min(left_sector)
        center_min = np.min(center_sector)
        right_min = np.min(right_sector)
        return left_min, center_min, right_min
    

    ##### CONTROL #####
    def set_goal_position(self, position: tuple):
        if position is None:
            self.goal_position = None
            return
        x, y = position
        self.goal_position = Position(x, y)

    def get_control_errors(self) -> tuple:
        rho, alpha = self.state.calculate_errors(self.goal_position)
        rho = min(self.MAX_VISION_DISTANCE, rho) # cap to max vision distance
        return rho, alpha
    
    def calculate_velocity(self, rho, alpha):
        lin_vel = self.K_DISTANCE * rho * np.cos(alpha)  # cos(alpha) is to slow down forward motion in case alpha is big
        ang_vel = self.K_HEADING * alpha
        # linear velocity limits
        lin_vel = max(0.0, lin_vel)                     # don't go backward
        lin_vel = min(lin_vel, self.MAX_LIN_VEL)   # max forward speed (tune for your robot)
        # angular velocity limits  
        ang_vel = min(self.MAX_ANG_VEL, ang_vel)
        ang_vel = max(-self.MAX_ANG_VEL, ang_vel)
        # dead-zone for angular velocity (avoid oscillations near zero)
        if abs(ang_vel) < self.ANG_VEL_DEADZONE:
            ang_vel = 0.0
        return lin_vel, ang_vel
    
    def set_robot_velocity(self, lin_vel, ang_vel):
        # from set linear and angular velocity to wheel linear velocity
        v_r = lin_vel + 0.5 * ang_vel * self.DISTANCE_BETWEEN_WHEELS
        v_l = lin_vel - 0.5 * ang_vel * self.DISTANCE_BETWEEN_WHEELS
        # linear -> angular (rad/s)
        w_r = v_r / self.WHEEL_RADIUS
        w_l = v_l / self.WHEEL_RADIUS
        # saturation to preserve curvature
        scale = max(abs(w_l), abs(w_r)) / self.MAX_WHEEL_SPEED
        if scale > 1.0:
            w_l /= scale
            w_r /= scale
        # set motor velocity
        self.motorL.setVelocity(w_l)
        self.motorR.setVelocity(w_r)
        return w_l, w_r
    
    def get_wheel_velocity(self):
        w_r = self.motorR.getVelocity()
        w_l = self.motorL.getVelocity()
        return w_l, w_r

    def get_robot_velocity(self):
        w_l, w_r = self.get_wheel_velocity()
        v_r = w_r * self.WHEEL_RADIUS
        v_l = w_l * self.WHEEL_RADIUS
        lin_vel = (v_r + v_l) / 2
        ang_vel = (v_r - v_l) / self.DISTANCE_BETWEEN_WHEELS
        return lin_vel, ang_vel


    ##### OTHER FUNCTIONS #####
    def is_alive(self) -> bool:
        return self.robot.step(self.initial_timestep) != -1
    
    def should_print(self) -> bool:
        current_time = self.robot.getTime()
        should_print = current_time - self.last_print_time >= 0.5
        if should_print:
            self.last_print_time = current_time
        return should_print

    def has_reached_goal(self) -> bool:
        return self.state.calculate_errors(self.goal_position)[0] < self.GOAL_REACHED_THRESH
    
if __name__ == "__main__":
    main()
