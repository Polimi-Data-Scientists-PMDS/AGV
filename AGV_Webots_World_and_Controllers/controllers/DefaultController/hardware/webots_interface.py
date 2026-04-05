# hardware/webots_interface.py
from controller import Supervisor # type: ignore
import numpy as np

class WebotsInterface:
    def __init__(self, config):
        self.config = config
        self.robot = Supervisor()
        self.timestep = int(self.robot.getBasicTimeStep())
        
        # MOTORS
        self.motorL = self.robot.getDevice('left wheel motor')
        self.motorR = self.robot.getDevice('right wheel motor')
        self.motorL.setPosition(float('inf'))
        self.motorR.setPosition(float('inf'))
        print("Motors set up correctly!")
        
        # ENCODERS
        self.posL = self.motorL.getPositionSensor()
        self.posR = self.motorR.getPositionSensor()
        self.posL.enable(self.timestep)
        self.posR.enable(self.timestep)
        self.prevL, self.prevR = 0.0, 0.0
        print("Motor encoders set up correctly!")
        
        # CAMERA
        self.camera = self.robot.getDevice("camera")
        if self.camera:
            self.camera.enable(self.timestep)
            
        # LIDAR
        self.lidar = self.robot.getDevice('Lidar1')
        self.lidar.enable(self.timestep)
        print("Lidar set up correctly!")
        
        # GPS
        self.gps = self.robot.getDevice('gps')
        self.gps.enable(self.timestep)
        
        # INIT STEP & STATES
        self.robot.step(self.timestep)
        self.gps_initial_state = self.gps.getValues()
        print("GPS set up correctly!")

    def is_alive(self) -> bool:
        return self.robot.step(self.timestep) != -1

    def get_time(self) -> float:
        return self.robot.getTime()

    def get_lidar_specs(self):
        return self.lidar.getFov(), self.lidar.getMaxRange()

    def get_odometry(self):
        """Read encoders and return delta values."""
        curr_L = self.posL.getValue()
        curr_R = self.posR.getValue()
        dL = curr_L - self.prevL
        dR = curr_R - self.prevR
        self.prevL, self.prevR = curr_L, curr_R
        return dL, dR

    def get_gps(self):
        """Read GPS and normalize to start position."""
        x, y, _ = self.gps.getValues()
        x -= self.gps_initial_state[0]
        y -= self.gps_initial_state[1]
        return x, y

    def read_lidar(self):
        """Return LIDAR scan as a list of (angle, distance) tuples."""
        ranges = self.lidar.getRangeImage()
        fov = self.lidar.getFov()
        resolution = self.lidar.getHorizontalResolution()
        angle_step = fov / resolution
        
        points = []
        for i, r in enumerate(ranges):
            angle = -fov/2 + i * angle_step
            points.append((angle, r))
        return points

    def apply_wheel_velocities(self, w_l, w_r):
        self.motorL.setVelocity(w_l)
        self.motorR.setVelocity(w_r)

    def get_wheel_velocity(self):
        """Get actual current wheel velocities in m/s"""
        w_r = self.motorR.getVelocity()
        w_l = self.motorL.getVelocity()
        v_r = w_r * self.config.WHEEL_RADIUS
        v_l = w_l * self.config.WHEEL_RADIUS
        return v_l, v_r
    
    def stop_motors(self):
        """Stops the robot safely."""
        self.motorL.setVelocity(0.0)
        self.motorR.setVelocity(0.0)