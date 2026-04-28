from dataclasses import dataclass
import numpy as np

from perception.perception import SensorData

from config import PhysicalConfig, PerceptionConfig



@dataclass
class Position:
    x: float
    y: float

@dataclass
class RobotState:
    x: float
    y: float
    theta: float
    v: float
    omega: float

    def copy(self):
        return RobotState(
            x=self.x,
            y=self.y,
            theta=self.theta,
            v=self.v,
            omega=self.omega
        )

class Localization:
    def __init__(self):
        self.physical_config = PhysicalConfig()
        self.perception_config = PerceptionConfig()
    
    def initial_state(self) -> RobotState:
        return RobotState(0,0,0,0,0)

    def localize(self, prev_state:RobotState, sensor_data:SensorData) -> RobotState:
        state = prev_state.copy()

        # Odometry
        dt = sensor_data.dt
        dL, dR = sensor_data.wheels_delta
        dS, dTheta = self.__calculate_odometry(dL, dR)
        state = self.__update_with_odometry(state, dt, dS, dTheta)

        # GPS Fusion
        gps_x, gps_y = sensor_data.gps
        state = self.__fuse_with_gps(state, gps_x, gps_y)

        return state

    def __calculate_odometry(self, dL, dR):
        """Convert left/right wheel movement into center displacement and rotation."""
        # noise threshold
        if abs(dL) < self.perception_config.encoder_thresh: dL = 0
        if abs(dR) < self.perception_config.encoder_thresh: dR = 0
        dS_L = dL * self.physical_config.wheel_radius
        dS_R = dR * self.physical_config.wheel_radius
        dS = (dS_L + dS_R) / 2.0
        dTheta = (dS_R - dS_L) / self.physical_config.wheel_base
        return dS, dTheta
    
    def __update_with_odometry(self, state:RobotState, dt:float, dS:float, dTheta:float) -> RobotState:
        state.x += dS * np.cos(state.theta)
        state.y += dS * np.sin(state.theta)
        state.theta += dTheta
        state.theta = (state.theta + np.pi) % (2 * np.pi) - np.pi
        state.v = dS / dt if dt != 0 else 0
        state.omega = dTheta / dt if dt != 0 else 0
        return state

    def __fuse_with_gps(self, state:RobotState, gps_x:float, gps_y:float, gps_weight=1.0) -> RobotState:
        state.x = (gps_x * gps_weight) + (state.x * (1 - gps_weight))
        state.y = (gps_y * gps_weight) + (state.y * (1 - gps_weight))
        return state