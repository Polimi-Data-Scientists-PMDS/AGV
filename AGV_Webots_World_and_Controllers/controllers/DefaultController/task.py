from dataclasses import dataclass

from planning.high_level.planning_interface import HighLevelPlanner
from planning.high_level.visgraph_planner import VisGraphPlanner

from planning.low_level.planning_interface import LowLevelPlanner
from planning.low_level.grid_planner import GridPlanner
from planning.low_level.sector_planner import SectorPlanner

from config import WorldConfig

@dataclass(frozen=True)
class Task:
    hl_planner_class: type[HighLevelPlanner] = VisGraphPlanner
    ll_planner_class: type[LowLevelPlanner] = GridPlanner

    goal_positions = [
        # WorldConfig.goals["PICKUP_07"],          # Pickup point 7
        # WorldConfig.goals["CHARGING_STATION"],   # Charging station
        WorldConfig.goals["DROPOFF_01"],         # Dropoff point 01
        WorldConfig.goals["PICKUP_03"],          # Pickup point 3
        WorldConfig.goals["PICKUP_04"],          # Pickup point 4
        WorldConfig.goals["CHARGING_STATION"],   # Charging station
        WorldConfig.goals["PICKUP_01"],          # Pickup point 1
        WorldConfig.goals["DROPOFF_01"],         # Dropoff point 01
        WorldConfig.goals["PICKUP_02"],          # Pickup point 2
        WorldConfig.goals["PICKUP_05"],          # Pickup point 5
        WorldConfig.goals["PICKUP_06"],          # Pickup point 6
        WorldConfig.goals["DROPOFF_01"],         # Dropoff point 01
        WorldConfig.goals["PICKUP_07"],          # Pickup point 7
        WorldConfig.goals["CHARGING_STATION"],   # Charging station
    ]
