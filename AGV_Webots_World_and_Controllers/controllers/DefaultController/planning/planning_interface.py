from abc import ABC, abstractmethod

from perception.perception import SensorData
from localization.localization import RobotState, Position
from config import PlanningConfig

class Path:
    def __init__(self, waypoints):
        self.waypoints = waypoints  # [(x,y), ...]

class PlanningInterface(ABC):
    def __init__(self, logger, lidar_specs): 
        self.config = PlanningConfig()
        self.logger = logger
        self.fov = lidar_specs[0]

    @abstractmethod
    def plan(self, state:RobotState, goal:Position, sensor_data:SensorData) -> Path:
        pass

