from dataclasses import dataclass
import json

from planning.high_level.planning_interface import HighLevelPlanner
from planning.high_level.visgraph_planner import VisGraphPlanner

from planning.low_level.planning_interface import LowLevelPlanner
from planning.low_level.grid_planner import GridPlanner
from planning.low_level.sector_planner import SectorPlanner

from config import WorldConfig
import os

DEFAULT_CONTROLLER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(DEFAULT_CONTROLLER_DIR, "..", "..", ".."))
CONFIG_PATH = os.path.join(DEFAULT_CONTROLLER_DIR, "config.json")
GOALS_CONFIG_PATH = os.path.join(PROJECT_ROOT, "web-app", "src", "goals.config.json")

def _load_json_config(config_path):
    with open(config_path, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)
    return config

def _load_goals_config():
    if os.path.exists(GOALS_CONFIG_PATH):
        return _load_json_config(GOALS_CONFIG_PATH)
    return _load_json_config(CONFIG_PATH)

def _load_goal_positions():
    config = _load_goals_config()
    return tuple(tuple(goal["coordinates"]) for goal in config["Goals"])

@dataclass(frozen=True)
class Task:
    hl_planner_class: type[HighLevelPlanner] = VisGraphPlanner
    ll_planner_class: type[LowLevelPlanner] = GridPlanner

    def get_goal(self, index: int) -> tuple[float, float]:
        return _load_goal_positions()[index]
    
    def num_goals(self) -> int:
        return len(_load_goal_positions())
