from abc import ABC, abstractmethod

from planning.planning import Path, GlobalMap
from perception.perception import SensorData
from localization.localization import RobotState, Position
from config import LowLevelPlanningConfig

class LowLevelPlanner(ABC):
    def __init__(self, logger, lidar_specs, global_map: GlobalMap, config): 
        self.logger = logger
        self.fov = lidar_specs[0]
        self.global_map = global_map
        self.config = config

    @abstractmethod
    def plan(self, state:RobotState, goal:Position, sensor_data:SensorData) -> Path:
        pass

