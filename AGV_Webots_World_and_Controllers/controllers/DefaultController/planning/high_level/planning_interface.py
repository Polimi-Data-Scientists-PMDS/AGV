from abc import ABC, abstractmethod

from planning.path import Path
from perception.perception import SensorData
from localization.localization import RobotState, Position
from config import PlanningConfig


class HighLevelPlanner(ABC):
    def __init__(self, logger): 
        self.config = PlanningConfig()
        self.logger = logger

    @abstractmethod
    def plan(self, state:RobotState, goal:Position) -> Path:
        pass

