from abc import ABC, abstractmethod

from planning.planning import Path, GlobalMap
from perception.perception import SensorData
from localization.localization import RobotState, Position
from config import PlanningConfig


class HighLevelPlanner(ABC):
    def __init__(self, logger, global_map: GlobalMap): 
        self.config = PlanningConfig()
        self.logger = logger
        self.global_map = global_map

    @abstractmethod
    def plan(self, state:RobotState, goal:Position) -> Path:
        pass

