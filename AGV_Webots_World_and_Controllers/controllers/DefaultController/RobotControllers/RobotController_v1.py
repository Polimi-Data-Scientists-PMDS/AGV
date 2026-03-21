from controller import Robot  # type: ignore
#Error due to library used by webots and not imported locally
from dataclasses import dataclass
import os
import sys
import numpy as np 
import time
import math


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "RobotLog"))
if LOG_DIR not in sys.path:
    sys.path.append(LOG_DIR)

from RobotLog import RobotLog 

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


class RobotController_v1:
    def __init__(self):
        # CONSTANTS
        self.DISTANCE_BETWEEN_WHEELS = 0.33 # (m) distance between wheels found in the robot manual
        self.WHEEL_RADIUS = 0.0975 # (m) wheel radius found in the robot manual
        self.MAX_WHEEL_SPEED = 12.3 # (rad/s) actual max speed is 100, this setting is to not overspeed the robot
        self.CONTROL_VISION_DISTANCE = 2 # (m) distance where the robot can see
        #self.LIDAR_VISION_DISTANCE = 2 # (m) distance that the lidar sees
        self.SAFE_DISTANCE = 2 # (m) distance from where to avoid obstacles
        self.LIDAR_FOV = 180
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
        self.robot.step(self.initial_timestep)
        self.used_obstacle_ids = set()
        self.used_space_ids = set()
        self.previous_scan = None
        self.locked_obstacle = None
        self.locked_space = None
        print("Lidar set up correctly!")
        print("RangeImage size:", len(self.lidar.getRangeImage()))
        print("Horizontal resolution:", self.lidar.getHorizontalResolution())
        print(f"Lidar FOV: {self.lidar.getFov()} radians ({self.lidar.getFov()*180/np.pi} degrees), max range: {self.lidar.getMaxRange()}m")
        # print(f"Lidar output size: {len(self.lidar.getRangeImage())}")
        
        # Gps
        self.gps = self.robot.getDevice('gps')
        self.gps.enable(self.initial_timestep)
        self.robot.step(self.initial_timestep)
        self.gps_initial_state = self.gps.getValues()
        self.last_gps_x = 0.0
        self.last_gps_y = 0.0
        self.last_gps_dx = 0.0
        self.last_gps_dy = 0.0
        print("GPS set up correctly!")
        print(f"GPS initial coordinates: x: {self.gps_initial_state[0]}, y: {self.gps_initial_state[1]}")
        print(f"GPS coordinate system: {self.gps.getCoordinateSystem()}")

        # OTHER
        self.last_print_time = 0
        log_file_path = os.path.join(LOG_DIR, "robot_controller_runs.jsonl")
        self.logger = RobotLog(log_file_path, controller_version="v1")
        self.logger.start(self.robot.getTime())



    ##### PERCEPTION #####
    def update_wheel_odometry(self):
        """Compute robot displacement from wheel encoder changes.
            Returns:
                dS (float): Linear displacement of the robot (m).
                dTheta (float): Change in robot orientation (rad).
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
        """Update the robot's state using wheel odometry and GPS fusion."""
        # get position and orientation from gps and update the state
        # get delta movement
        dS, dTheta = self.update_wheel_odometry()
        # update state
        self.state.update_with_odometry(dS, dTheta)

        # get gps data
        x, y, _ = self.gps.getValues()
        x -= self.gps_initial_state[0]
        y -= self.gps_initial_state[1]
        
        self.last_gps_x = x
        self.last_gps_y = y
        self.last_gps_dx = x - self.state.x
        self.last_gps_dy = y - self.state.y

        # fuse with gps data
        self.state.fuse_with_gps(x, y)


        # dX = x - self.state.x
        # dY = y - self.state.y
        # print(f"GPS coordinates: x: {dX}, y: {dY}")
        # differences.append((dX, dY))
    
    # def read_lidar(self, heading_error):
    #     """Return LIDAR scan as a list of (angle, distance) tuples."""
    #     raw_range_image = self.lidar.getRangeImage()
    #     fov = self.lidar.getFov()  
    #     N = len(raw_range_image)
        
    #     points = []
    #     for i, r in enumerate(raw_range_image):
    #         angle = -fov/2 + i * fov/(N-1) #- heading_error
    #         points.append((angle, r))
            
    #     return points
    def read_lidar(self):
        """Return LIDAR scan as a list of (angle, distance) tuples."""

        ranges = self.lidar.getRangeImage()
        N = len(ranges)

        fov = self.lidar.getFov()
        resolution = self.lidar.getHorizontalResolution()

        # Webots guarantees this mapping
        angle_step = fov / resolution

        points = []

        for i, r in enumerate(ranges):
            angle = -fov/2 + i * angle_step
            points.append((angle, r))

        return points
    
    # def min_distances(self, pointcloud):
    #     # Angles step in each direction: 
    #     # 7,5 > 15 > 30 > 37,5 => 0,1308 > 0,2618 > 0,5236 > 0,6545
    #     # 7,5 > 22,5 > 52,5 > 90 => 0,1308 > 0,3927 > 0,9163 > 1,5708

    #     l4, l3, l2, l1, r1, r2, r3, r4 =  (self.lidar.getMaxRange() for _ in range(8))

    #     for angle, dist in pointcloud:
    #         if angle < -0.9163 and l4 > dist:
    #             l4 = dist
    #         elif angle < -0.3927 and l3 > dist:
    #             l3 = dist
    #         elif angle < -0.1308 and l2 > dist:
    #             l2 = dist
    #         elif angle < 0 and l1 > dist:
    #             l1 = dist
    #         elif angle < 0.1308 and r1 > dist:
    #             r1 = dist
    #         elif angle < 0.3927 and r2 > dist:
    #             r2 = dist
    #         elif angle < 0.9163 and r3 > dist:
    #             r3 = dist
    #         elif r4 > dist:
    #             r4 = dist
    #     return l4, l3, l2, l1, r1, r2, r3, r4
    
    # def old_obstacle_avoidance(self, pointcloud, lin_vel, ang_vel):
    #     l4, l3, l2, l1, r1, r2, r3, r4 = self.min_distances(pointcloud)

    #     # Compact summaries
    #     center_min = min(l1, r1, l2, r2)
    #     left_min   = min(l3, l4)
    #     right_min  = min(r3, r4)

    #     # In a dead end > reverse
    #     if center_min < 0.15 and right_min < 0.05 and left_min < 0.05:
    #         print("DEAD END! REVERSING!")
    #         return 0, 10*np.sign(ang_vel) 
    #     # Close object in front > turn
    #     elif center_min < 0.3:
    #         print ("OBSTACLE IN FRONT! TURNING!")
    #         if right_min > left_min:
    #             return lin_vel*0.5, -2.0 #turn left
    #         else:
    #             return lin_vel*0.5, 2.0 #turn rightight
    #     # # Object in front > slow down 
    #     # elif center_min < 0.5:
    #     #     return lin_vel*0.7, ang_vel
    #     # # Object on the right 
    #     # elif right_min < 0.05 and right_min < left_min:
    #     #     if ang_vel > 0:
    #     #         return lin_vel*0.7, ang_vel-3.0
    #     #     return lin_vel*0.7, ang_vel #small turn left
    #     # # Object on the left
    #     # elif left_min < 0.05 and left_min < right_min:
    #     #     if ang_vel < 0:
    #     #         return lin_vel*0.7, ang_vel+3.0
    #     #     return lin_vel*0.7, ang_vel #small turn right

    #     return lin_vel, ang_vel



    def obstacle_avoidance(self, pointcloud, dist_e, heading_e):
        def get_obstacle_id():
            for i in range(1, NUM_SECTORS):
                if i not in self.used_obstacle_ids:
                    self.used_obstacle_ids.add(i)
                    return i
            return None

        def get_space_id():
            for i in range(-1, -NUM_SECTORS, -1):
                if i not in self.used_space_ids:
                    self.used_space_ids.add(i)
                    return i
            return None
        
        # --- 1. SETUP ---
        NUM_SECTORS = 32
        PADDING = 3
        fov = self.lidar.getFov()
        sector_width = fov / NUM_SECTORS
        unnamed_sectors = ['f'] * NUM_SECTORS
        obstacle_found = False

        # --- 2. MAP LIDAR ---
        for angle, dist in pointcloud:
            if dist < self.SAFE_DISTANCE:
                sector_id = int((angle + fov/2) / sector_width)
                if 0 <= sector_id < NUM_SECTORS:
                    unnamed_sectors[sector_id] = 'o'
                    obstacle_found = True
                    for p in range(1, PADDING + 1):
                        if sector_id - p >= 0:
                            unnamed_sectors[sector_id - p] = 'o'
                        if sector_id + p < NUM_SECTORS:
                            unnamed_sectors[sector_id + p] = 'o'
        if not obstacle_found:
            self.used_obstacle_ids.clear()
            self.used_space_ids.clear()
            self.previous_scan = None
            self.locked_obstacle = None
            self.locked_space = None
            return dist_e, heading_e


        # --- 3. ASSIGN IDS TO THE SECTORS ---
        print("used obstacle ids:", self.used_obstacle_ids)
        print("used space ids:", self.used_space_ids)
        print(f"UNPROCESSED RADAR: [{' '.join(('|' if s == 'o' else '.') for s in unnamed_sectors)}] \n")
        sectors = unnamed_sectors.copy()
        if self.previous_scan is None:
            #print("NO PREV SCAN")
            # assign ids to this sector
            prev_id = None
            prev_was_obstacle = None
            for i, s in enumerate(unnamed_sectors):
                if s == 'o': # is an obstacle
                    if not prev_was_obstacle or i == 0:
                        prev_id = get_obstacle_id()
                    sectors[i] = prev_id
                    prev_was_obstacle = True

                else: # is free space
                    if prev_was_obstacle or i == 0:
                        prev_id = get_space_id()
                    sectors[i] = prev_id
                    prev_was_obstacle = False

        else:
            #print("HAS PREV SCAN")
            # 1 assign ids to this sector of the same position
            for i in range(NUM_SECTORS):
                is_old_obstacle = self.previous_scan[i] > 0
                is_new_obstacle = unnamed_sectors[i] == 'o'
                if is_old_obstacle and is_new_obstacle:
                    sectors[i] = self.previous_scan[i]
                elif not is_old_obstacle and not is_new_obstacle:
                    sectors[i] = self.previous_scan[i]
            print(f"RADAR AFTER STEP 1: [{' '.join(str(s) for s in sectors)}] \n")
            # 2 forward id propagation
            prev_id = None
            is_prev_obstacle = None
            for i in range(NUM_SECTORS):
                has_id = sectors[i] not in ['f', 'o']
                if has_id:
                    prev_id = sectors[i]
                    is_prev_obstacle = unnamed_sectors[i] == 'o'
                else:
                    if unnamed_sectors[i] == 'o' and is_prev_obstacle:
                        sectors[i] = prev_id
                    elif unnamed_sectors[i] == 'f' and is_prev_obstacle is False:
                        sectors[i] = prev_id
            print(f"RADAR AFTER STEP 2: [{' '.join(str(s) for s in sectors)}] \n")
            # backward id propagation
            next_id = None
            is_next_obstacle = None
            for i in range(NUM_SECTORS-1, -1, -1):
                has_id = sectors[i] not in ['f', 'o']
                if has_id:
                    next_id = sectors[i]
                    is_next_obstacle = unnamed_sectors[i] == 'o'
                else:
                    if unnamed_sectors[i] == 'o' and is_next_obstacle:
                        sectors[i] = next_id
                    elif unnamed_sectors[i] == 'f' and is_next_obstacle is False:
                        sectors[i] = next_id
            print(f"RADAR AFTER STEP 3: [{' '.join(str(s) for s in sectors)}] \n")
            # new id assignment 
            prev_id = None
            prev_was_obstacle = None
            for i in range(NUM_SECTORS):
                has_id = sectors[i] not in ['f', 'o']
                is_obstacle = unnamed_sectors[i] == 'o'
                if not has_id:
                    if is_obstacle:
                        if not prev_was_obstacle or i == 0:
                            sectors[i] = get_obstacle_id()
                            prev_id = sectors[i]
                        else:
                            sectors[i] = prev_id
                    else:
                        if prev_was_obstacle or i == 0:
                            sectors[i] = get_space_id()
                            prev_id = sectors[i]
                        else:
                            sectors[i] = prev_id
                prev_was_obstacle = is_obstacle

        if 0 in sectors or None in sectors:
            raise Exception("OBSTACLE AVOIDANCE -- Missing a sector assignment!")
            
        #print(f"FINAL RADAR: [{' '.join(str(s) for s in sectors)}] \n")
        self.previous_scan = sectors.copy()

        # CLEAN USED OBSTACLES BUFFER
        self.used_obstacle_ids.clear()
        self.used_space_ids.clear()
        for s in sectors:
            if s > 0:
                self.used_obstacle_ids.add(s)
            else:
                self.used_space_ids.add(s)


        # --- 4. CHOOSE DIRECTION ---
        # check if i have to remove lock
        if self.locked_obstacle not in sectors or self.locked_space not in sectors:
            self.locked_obstacle = None
            self.locked_space = None
        
        original_sector_index = None
        min_original_error = float('inf')
        best_sector_index = None
        best_sector_angle = None
        min_free_error = float('inf')
        for i in range(NUM_SECTORS):
            sector_angle = fov/2 - (i + 0.5) * sector_width 
            error = abs(np.arctan2(np.sin(sector_angle - heading_e), 
                                np.cos(sector_angle - heading_e)))
            
            # find the sector it would have chose if no obstacles were present
            if error < min_original_error:
                min_original_error = error
                original_sector_index = i

            # find the closest free sector to the goal heading 
            lock_ok = self.locked_space is None or self.locked_space == sectors[i]
            if sectors[i] < 0 and lock_ok: # if sector is free and lock is okay
                if error < min_free_error:
                    min_free_error = error
                    best_sector_index = i
                    best_sector_angle = sector_angle

        # update the lock
        if original_sector_index != best_sector_index: # if there is an obstacle in the path
            # -> add lock
            self.locked_obstacle = sectors[original_sector_index]
            self.locked_space = sectors[best_sector_index]
        else:
            # -> remove lock
            self.locked_obstacle = None
            self.locked_space = None

        print(f"LOCKED ON SPACE: {self.locked_space}")
        print(f"LOCKED ON OBSTACLE: {self.locked_obstacle}")
        
        if best_sector_index is None:
            print(f"RADAR: [FILLED] NO PATH - STOP")
            self.avoidance_side = 0
            return 0.0, 0.0
    
        visual_map = ""
        for i, s in enumerate(sectors):
            # char = '|' if s == 1 else '.'
            char = str(s)
            if i == original_sector_index:
                char = 'X'
            if i == best_sector_index:
                char = 'O'
            if i == original_sector_index and i == best_sector_index:
                char = '*'
            visual_map += char + " "

        print(f"COMPLETE RADAR: [{visual_map}] | Steering: {best_sector_angle:.2f} | LOCKED ON: {self.locked_space}")
        


        # --- 5. EXECUTION ---
        if original_sector_index == best_sector_index:
            final_steering_angle = heading_e
        else:
            final_steering_angle = best_sector_angle

        # Slow down when making sharp turns to avoid hitting obstacles
        speed_factor = max(0.2, np.cos(final_steering_angle))

        # The "error" for the PID/Control is simply the relative angle of our target path
        new_heading_error = final_steering_angle

        print(f"OLD HEADING ERROR: {heading_e:.2f}")
        print(f"STEERING TOWARD: {new_heading_error:.2f}")

        return dist_e * speed_factor, new_heading_error




    ##### CONTROL #####
    def set_goal_position(self, position: tuple):
        if position is None:
            self.goal_position = None
            return
        x, y = position
        self.goal_position = Position(x, y)

    def get_control_errors(self) -> tuple:
        rho, alpha = self.state.calculate_errors(self.goal_position)
        rho = min(self.CONTROL_VISION_DISTANCE, rho) # cap to max vision distance
        return rho, alpha
    
    def calculate_velocity(self, rho, alpha):
        """Compute linear and angular velocities from distance and heading errors.
            Args:
                rho (float): Distance error to the goal (m).
                alpha (float): Heading error to the goal (rad).
            Returns:
                lin_vel (float): Linear velocity (m/s), capped and non-negative.
                ang_vel (float): Angular velocity (rad/s), limited and dead-zoned.
        """
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
        v_r = w_r * self.WHEEL_RADIUS
        v_l = w_l * self.WHEEL_RADIUS
        return v_l, v_r

    def get_robot_velocity(self):
        v_l, v_r = self.get_wheel_velocity()
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
    
