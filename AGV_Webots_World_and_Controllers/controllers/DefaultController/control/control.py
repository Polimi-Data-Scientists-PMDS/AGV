import numpy as np

from localization.localization import RobotState
from planning.planning import Path
from utils.utils import calculate_control_errors
from config import ControlConfig, MovingObstacleSafetyConfig, PhysicalConfig
from planning.low_level.planning_interface import PlannerSafetyStatus

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
        w_l, w_r = compute_wheel_velocities(v, omega, self.physical_config)
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
    


def compute_wheel_velocities(lin_vel, ang_vel, physical_config):
    """Convert robot velocity into bounded left/right wheel speeds."""
    v_r = lin_vel + 0.5 * ang_vel * physical_config.wheel_base
    v_l = lin_vel - 0.5 * ang_vel * physical_config.wheel_base

    w_r = v_r / physical_config.wheel_radius
    w_l = v_l / physical_config.wheel_radius

    scale = max(abs(w_l), abs(w_r)) / physical_config.max_wheel_speed
    if scale > 1.0:
        w_l /= scale
        w_r /= scale

    return w_l, w_r


class MovingObstacleSafetyLimiter:
    """Apply slowdown and latched-stop rules to a path-following command."""

    def __init__(self, config=None):
        self.config = config or MovingObstacleSafetyConfig()
        self.physical_config = PhysicalConfig()
        self._stop_started_at = None

    def limit(
        self,
        command: ControlCommand,
        status: PlannerSafetyStatus,
        current_time: float,
    ) -> ControlCommand:
        obstacle_clearance = status.nearest_confirmed_clearance_m
        if (
            obstacle_clearance is not None
            and obstacle_clearance < self.config.stop_clearance_m
            and self._stop_started_at is None
        ):
            self._stop_started_at = current_time

        if self._stop_started_at is not None:
            held_long_enough = (
                current_time - self._stop_started_at
                >= self.config.minimum_stop_hold_s
            )
            confirmed_clearance = status.nearest_confirmed_clearance_m
            all_confirmed_clear = (
                confirmed_clearance is None
                or confirmed_clearance > self.config.release_clearance_m
            )
            if not (held_long_enough and all_confirmed_clear):
                return ControlCommand(command.rho, command.alpha, 0.0, 0.0, 0.0, 0.0)
            self._stop_started_at = None

        linear_velocity = command.v
        if (
            obstacle_clearance is not None
            and obstacle_clearance < self.config.slowdown_clearance_m
        ):
            linear_velocity = min(linear_velocity, self.config.slowdown_speed_mps)

        if linear_velocity == command.v:
            return command

        w_l, w_r = compute_wheel_velocities(
            linear_velocity, command.omega, self.physical_config
        )
        return ControlCommand(
            command.rho,
            command.alpha,
            linear_velocity,
            command.omega,
            w_l,
            w_r,
        )
