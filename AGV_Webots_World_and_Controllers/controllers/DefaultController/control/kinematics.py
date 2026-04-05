# control/kinematics.py
import numpy as np

class KinematicsController:
    def __init__(self, config):
        self.config = config

    def calculate_odometry(self, dL, dR):
        """Convert left/right wheel movement into center displacement and rotation."""
        # noise threshold
        if abs(dL) < self.config.ENCODER_THRESH: dL = 0
        if abs(dR) < self.config.ENCODER_THRESH: dR = 0

        dS_L = dL * self.config.WHEEL_RADIUS
        dS_R = dR * self.config.WHEEL_RADIUS

        dS = (dS_L + dS_R) / 2.0
        dTheta = (dS_R - dS_L) / self.config.DISTANCE_BETWEEN_WHEELS
        return dS, dTheta

    def calculate_velocity(self, rho, alpha):
        """Compute linear and angular velocities from distance and heading errors."""
        lin_vel = self.config.K_DISTANCE * rho * np.cos(alpha)  
        ang_vel = self.config.K_HEADING * alpha
        
        # linear velocity limits
        lin_vel = max(0.0, lin_vel)                     
        lin_vel = min(lin_vel, self.config.MAX_LIN_VEL)   
        
        # angular velocity limits  
        ang_vel = max(-self.config.MAX_ANG_VEL, min(self.config.MAX_ANG_VEL, ang_vel))
        
        # dead-zone for angular velocity
        if abs(ang_vel) < self.config.ANG_VEL_DEADZONE:
            ang_vel = 0.0
            
        return lin_vel, ang_vel
    
    def get_wheel_velocities(self, lin_vel, ang_vel):
        """Converts commanded robot velocities into left/right wheel radians per second."""
        v_r = lin_vel + 0.5 * ang_vel * self.config.DISTANCE_BETWEEN_WHEELS
        v_l = lin_vel - 0.5 * ang_vel * self.config.DISTANCE_BETWEEN_WHEELS
        
        w_r = v_r / self.config.WHEEL_RADIUS
        w_l = v_l / self.config.WHEEL_RADIUS
        
        scale = max(abs(w_l), abs(w_r)) / self.config.MAX_WHEEL_SPEED
        if scale > 1.0:
            w_l /= scale
            w_r /= scale
            
        return w_l, w_r