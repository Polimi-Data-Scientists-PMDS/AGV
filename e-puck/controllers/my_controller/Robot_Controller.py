"""my_controller controller."""

from controller import Robot 
#Error due to library used by webots and not imported locally
import numpy as np 
import time

class RobotController:
    def __init__(self):
        self.DISTANCE_BETWEEN_WHEELS = 0.052 # (m) distance between wheels found in the robot manual
        self.WHEEL_RADIUS = 0.02 # (m) wheel radius found in the robot manual
        self.MAX_WHEEL_SPEED = 50 # (rad/s) actual max speed is 100, this setting is to not overspeed the robot
         
        self.CRUISE_SPEED = 0.4 # (m/s)
        self.TURN_SPEED = 0.35 # (m/s)
        self.HARD_TURN_SPEED = 0.2 # (m/s)

        # ROBOT
        self.robot = Robot() # Robot instance
        # Get the time step of the current world
        self.initial_timestep = int(self.robot.getBasicTimeStep()) # (ms) currently timestep is 1ms

        # DEVICES
        # Motors
        self.motorL = self.robot.getDevice('left wheel motor')
        self.motorR = self.robot.getDevice('right wheel motor')
        # setup for velocity control
        self.motorL.setPosition(float('inf'))
        self.motorR.setPosition(float('inf'))
        # Lidar
        self.lidar = self.robot.getDevice('Lidar1')
        self.lidar.enable(self.initial_timestep)
        print("Lidar set up correctly!")
        print(f"Lidar FOV: {self.lidar.getFov()} radians ({self.lidar.getFov()*180/np.pi} degrees), horizontal resolution: {self.lidar.getHorizontalResolution()} points, max range: {self.lidar.getMaxRange()}m")
        # Gps
        self.gps = self.robot.getDevice('gps')
        self.gps.enable(self.initial_timestep)
        print("GPS set up correctly!")
        print(f"GPS coordinate system: {self.gps.getCoordinateSystem()}")

        # OTHER
        self.last_print_time = 0

        self.goal_position = None
    
    def is_alive(self) -> bool:
        return self.robot.step(self.initial_timestep) != -1
    
    def is_print_time(self) -> bool:
        current_time = self.robot.getTime()
        should_print = current_time - last_print_time >= 0.5
        if should_print:
            last_print_time = current_time
        return should_print

    def set_goal_position(self, position):
        self.goal_position = position

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
    
    def get_wheel_velocity(self):
        w_r = self.motorR.getVelocity()
        w_l = self.motorL.getVelocity()
        return w_l, w_r
    
    def get_robot_velocity(self):
        w_l, w_r = self.get_actual_wheel_velocity()
        v_r = w_r * self.WHEEL_RADIUS
        v_l = w_l * self.WHEEL_RADIUS
        lin_vel = (v_r + v_l) / 2
        ang_vel = (v_r - v_l) / self.DISTANCE_BETWEEN_WHEELS
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
    
    def get_acceleration_speed(self, target_speed, current_speed, delta_time, time_to_target):
        if current_speed <= target_speed:
            delta_vel = (target_speed - current_speed) / delta_time
        elif current_speed > target_speed:
            delta_vel = (target_speed - current_speed) / delta_time
        return current_speed + delta_vel*time_to_target

    def get_angle_to_target(self):
        # Get GPS values
        gps_values = self.gps.getValues()
        # Calculate the angle to the target point
        angle = np.arctan2(self.goal_position[1] - gps_values[1], self.goal_position[0] - gps_values[0])
        return angle
    
    def get_robot_position_orientation(self):
        # returns robot's position and orientation in GPS coordinates
        # (x, y, theta)
        pass
    
    def get_heading_error(self):
        if self.goal_position is None:
            raise Exception("No goal position found!")
        # returns heading error (angle) between robot's orientation and goal position
        

#############################################

controller = RobotController()
controller.set_goal_position((5, 5))

while controller.isAlive():
    # constatly calculate the angle between robot heading 
    left_min, center_min, right_min = controller.read_lidar()
    
    target_robot_velocity = controller.calculate_robot_velocity()
    controller.set_robot_velocity(target_robot_velocity)

    curr_wheel_velocity = controller.get_wheel_velocity()
    curr_robot_velocity = controller.get_robot_velocity()

    if controller.is_print_time():
        # Print distance sensor value
        print(f"Time: {controller.robot.getTime()}s")
        # Print lidar values
        print(f"Lidar values: L: {left_min}, C: {center_min}, R: {right_min}")
        # Print GPS values
        # print(f"GPS values: {gps_values}")
        # Get wheel speed and print it
        w_l, w_r = curr_wheel_velocity
        lin_vel, ang_vel = curr_robot_velocity
        print(f"\nWheel speeds:\n L: {w_l}, R: {w_r}")
        print(f"\nRobot speed:\n linear: {lin_vel}, angular: {ang_vel}")





