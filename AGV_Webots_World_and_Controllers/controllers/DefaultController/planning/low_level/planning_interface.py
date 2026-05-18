from abc import ABC, abstractmethod

from planning.path import Path
from perception.perception import SensorData
from localization.localization import RobotState, Position
from config import LowLevelPlanningConfig

class LowLevelPlanner(ABC):
    def __init__(self, logger, lidar_specs): 
        self.config = LowLevelPlanningConfig()
        self.logger = logger
        self.fov = lidar_specs[0]

    @abstractmethod
    def plan(self, state:RobotState, goal:Position, sensor_data:SensorData) -> Path:
        pass

