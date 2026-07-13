import json
import math
import os
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from planning.high_level.planning_interface import HighLevelPlanner
from planning.high_level.visgraph_planner import VisGraphPlanner
from planning.low_level.grid_planner import GridPlanner
from planning.low_level.planning_interface import LowLevelPlanner


DEFAULT_CONTROLLER_DIR = os.path.dirname(os.path.abspath(__file__))
GOALS_CONFIG_PATH = os.path.join(DEFAULT_CONTROLLER_DIR, "goals.config.json")


class GoalConfigurationError(ValueError):
    """Raised when the controller-owned goal configuration is unusable."""


@dataclass(frozen=True)
class GoalSnapshot:
    goals: Mapping[str, tuple[float, float]]
    route: tuple[str, ...]


def _is_finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _load_snapshot(config_path: str, unit_id: str) -> GoalSnapshot:
    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise GoalConfigurationError(f"cannot read {config_path}: {exc}") from exc

    if not isinstance(config, dict):
        raise GoalConfigurationError("the top-level configuration must be an object")

    raw_goals = config.get("Goals")
    raw_routes = config.get("RobotRoutes")
    if not isinstance(raw_goals, list) or not raw_goals:
        raise GoalConfigurationError("Goals must be a nonempty array")
    if not isinstance(raw_routes, dict):
        raise GoalConfigurationError("RobotRoutes must be an object")

    goals = {}
    for index, raw_goal in enumerate(raw_goals):
        if not isinstance(raw_goal, dict):
            raise GoalConfigurationError(f"Goals[{index}] must be an object")
        name = raw_goal.get("name")
        coordinates = raw_goal.get("coordinates")
        if not isinstance(name, str) or not name:
            raise GoalConfigurationError(f"Goals[{index}].name must be a nonempty string")
        if name in goals:
            raise GoalConfigurationError(f"goal name {name!r} is duplicated")
        if (
            not isinstance(coordinates, list)
            or len(coordinates) != 2
            or not all(_is_finite_number(value) for value in coordinates)
        ):
            raise GoalConfigurationError(
                f"goal {name!r} coordinates must contain exactly two finite numbers"
            )
        goals[name] = (float(coordinates[0]), float(coordinates[1]))

    for route_unit_id, raw_route in raw_routes.items():
        if not isinstance(route_unit_id, str) or not route_unit_id.isdigit():
            raise GoalConfigurationError("RobotRoutes keys must be numeric strings")
        if not isinstance(raw_route, list) or not raw_route:
            raise GoalConfigurationError(f"route for unit {route_unit_id} must be nonempty")
        for goal_name in raw_route:
            if not isinstance(goal_name, str) or goal_name not in goals:
                raise GoalConfigurationError(
                    f"route for unit {route_unit_id} references unknown goal {goal_name!r}"
                )

    raw_route = raw_routes.get(unit_id)
    if raw_route is None:
        raise GoalConfigurationError(f"no route is configured for unit {unit_id}")

    return GoalSnapshot(MappingProxyType(goals), tuple(raw_route))


class Task:
    hl_planner_class: type[HighLevelPlanner] = VisGraphPlanner
    ll_planner_class: type[LowLevelPlanner] = GridPlanner

    def __init__(self, unit_id, config_path=GOALS_CONFIG_PATH):
        normalized_unit_id = str(unit_id)
        if not normalized_unit_id.isdigit():
            raise GoalConfigurationError("unit_id must be numeric")
        self.unit_id = str(int(normalized_unit_id))
        self.config_path = os.fspath(config_path)
        self._snapshot = _load_snapshot(self.config_path, self.unit_id)

    def refresh(self, goal_index: int) -> int:
        """Load one cycle snapshot, retaining the numeric route position."""
        try:
            snapshot = _load_snapshot(self.config_path, self.unit_id)
        except GoalConfigurationError as exc:
            print(
                f"WARNING: Ignoring invalid goal configuration for unit "
                f"{self.unit_id}: {exc}"
            )
            return goal_index % len(self._snapshot.route)

        self._snapshot = snapshot
        return goal_index % len(snapshot.route)

    def get_goal(self, index: int) -> tuple[float, float]:
        goal_name = self._snapshot.route[index]
        return self._snapshot.goals[goal_name]

    def get_goal_name(self, index: int) -> str:
        return self._snapshot.route[index]

    def num_goals(self) -> int:
        return len(self._snapshot.route)
