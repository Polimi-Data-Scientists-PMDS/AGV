import numpy as np

from localization.localization import RobotState
from planning.planning_interface import Path
from utils.utils import calculate_control_errors
from config import ControlConfig, PhysicalConfig

class ControlCommand:
    def __init__(self, rho:float, alpha:float, v:float, omega:float, w_l:float, w_r:float):
        self.rho = rho
        self.alpha = alpha
        self.v = v
        self.omega = omega
        self.w_l = w_l
        self.w_r = w_r

class Control:
    def __init__(self):
        self.physical_config = PhysicalConfig()
        self.control_config = ControlConfig()

    def follow_path(self, state:RobotState, path:Path) -> ControlCommand:
        next_point = path.waypoints[0] if len(path.waypoints) > 0 else None
        if next_point is None:
            return ControlCommand(0, 0, 0, 0, 0, 0)
        rho, alpha = calculate_control_errors(state, next_point)
        v, omega = self.__compute_target_vel(rho, alpha)
        w_l, w_r = self.__compute_target_wheel_vel(v, omega)
        return ControlCommand(rho, alpha, v, omega, w_l, w_r)


    def __compute_target_vel(self, rho, alpha):
        """Compute linear and angular velocities from distance and heading errors."""
        lin_vel = self.control_config.max_lin_vel * np.cos(alpha)  
        ang_vel = self.control_config.heading_p_gain * alpha
        
        # linear velocity limits
        lin_vel = max(0.0, lin_vel)                     
        lin_vel = min(lin_vel, self.control_config.max_lin_vel)   
        
        # angular velocity limits  
        ang_vel = max(-self.control_config.max_ang_vel, min(self.control_config.max_ang_vel, ang_vel))
        
        # dead-zone for angular velocity
        if abs(ang_vel) < self.control_config.ang_vel_deadzone:
            ang_vel = 0.0
            
        return lin_vel, ang_vel
    
    def __compute_target_wheel_vel(self, lin_vel, ang_vel):
        """Converts commanded robot velocities into left/right wheel radians per second."""
        v_r = lin_vel + 0.5 * ang_vel * self.physical_config.wheel_base
        v_l = lin_vel - 0.5 * ang_vel * self.physical_config.wheel_base
        
        w_r = v_r / self.physical_config.wheel_radius
        w_l = v_l / self.physical_config.wheel_radius
        
        scale = max(abs(w_l), abs(w_r)) / self.physical_config.max_wheel_speed
        if scale > 1.0:
            w_l /= scale
            w_r /= scale
            
        return w_l, w_r