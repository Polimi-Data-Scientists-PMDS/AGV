from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from planning.planning import Path, GlobalMap
from perception.perception import SensorData
from localization.localization import RobotState, Position
from config import LowLevelPlanningConfig


@dataclass(frozen=True)
class PlannerSafetyStatus:
    """Forward surface clearances reported by the local obstacle tracker."""

    nearest_moving_clearance_m: Optional[float] = None
    nearest_confirmed_clearance_m: Optional[float] = None

    @property
    def has_moving_obstacle(self) -> bool:
        return self.nearest_moving_clearance_m is not None

class LowLevelPlanner(ABC):
    def __init__(self, logger, lidar_specs, global_map: GlobalMap, config): 
        self.logger = logger
        self.fov = lidar_specs[0]
        self.global_map = global_map
        self.config = config
        self.safety_status = PlannerSafetyStatus()

    @abstractmethod
    def plan(
        self,
        state: RobotState,
        goal: Position,
        sensor_data: SensorData,
        allow_goal_in_padding: bool = False,
    ) -> Path:
        pass
