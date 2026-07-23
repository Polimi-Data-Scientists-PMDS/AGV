import os
import sys

from config import LOGS_DIR, LogConfig, LOGGER_DIR, PlanningConfig, WorldConfig
from task import GoalConfigurationError, Task

if LOGGER_DIR not in sys.path:
    sys.path.append(LOGGER_DIR)

from control.control import Control, ControlCommand, MovingObstacleSafetyLimiter
from hardware.hardware_interface import HardwareInterface
from hardware.webots_interface import WebotsInterface
from localization.localization import Localization, Position, RobotState
from perception.perception import Perception, SensorData
from planning.high_level.planning_interface import HighLevelPlanner
from planning.low_level.planning_interface import LowLevelPlanner
from planning.planning import GlobalMap, Path
from robot_identity import parse_robot_unit_id
from robot_log import RobotLog
from utils.utils import calculate_control_errors


class AGVSimulation:
    def __init__(self):
        # Webots must exist before the unit-specific task, logger, or image writers.
        self.hardware: HardwareInterface = WebotsInterface()
        self.unit_id = parse_robot_unit_id(self.hardware.get_robot_name())
        self.operational = False
        self.task = None
        self.logger = None

        if self.unit_id is None:
            self._refuse_to_run(
                f"invalid robot name {self.hardware.get_robot_name()!r}; "
                "expected PIONEER_3_<number>"
            )
            return

        try:
            self.task = Task(self.unit_id)
        except GoalConfigurationError as exc:
            self._refuse_to_run(str(exc))
            return

        self.planning_config = PlanningConfig()
        self.log_config = LogConfig()
        self.global_map = GlobalMap(WorldConfig.fixed_obstacles)

        self.logger = RobotLog(self.log_config.server_url, self.unit_id)
        if not self.logger.start(self.hardware.get_time()):
            self._refuse_to_run("logging service startup failed")
            return

        self.perception: Perception = Perception(self.hardware, self.unit_id)
        self.localization: Localization = Localization()
        self.hl_planning: HighLevelPlanner = Task.hl_planner_class(self.logger, self.global_map)
        self.ll_planning: LowLevelPlanner = Task.ll_planner_class(
            self.logger,
            self.hardware.lidar.get_specs(),
            self.global_map,
            self.unit_id,
        )
        self.control: Control = Control()
        self.safety_limiter = MovingObstacleSafetyLimiter()

        self.goal_index = 0
        self.last_db_save = 0.0
        self.operational = True

    def _refuse_to_run(self, reason):
        print(f"Controller refusing to move: {reason}")
        self.hardware.motors.stop()

    def run(self):
        """Run one independent robot controller process."""
        if not self.operational:
            return

        # Start every run from a clean state: clear any stale emergency-stop
        # flag left on disk by a previous run, so a leftover file cannot hold
        # the vehicle stopped indefinitely.
        self.__clear_emergency_stop()

        try:
            prev_state = self.localization.initial_state(
                self.hardware.gps.get_initial_position(),
                self.hardware.inertial_unit.get_yaw(),
            )
            while self.hardware.is_alive():
                current_time = self.hardware.get_time()

                # Exactly one validated task snapshot is used throughout this cycle.
                self.goal_index = self.task.refresh(self.goal_index)

                sensor_data: SensorData = self.perception.perceive(current_time)
                state: RobotState = self.localization.localize(prev_state, sensor_data)
                prev_state = state.copy()

                goal: Position = self.__get_updated_goal(current_time, state)
                hl_path: Path = self.hl_planning.plan(state, goal)
                ll_goal = hl_path.waypoints[0]
                is_final_goal = (
                    abs(ll_goal.x - goal.x) < 1e-9
                    and abs(ll_goal.y - goal.y) < 1e-9
                )
                ll_path: Path = self.ll_planning.plan(
                    state,
                    ll_goal,
                    sensor_data,
                    allow_goal_in_padding=is_final_goal,
                )
                command: ControlCommand = self.control.follow_path(state, ll_path)
                command = self.safety_limiter.limit(
                    command, self.ll_planning.safety_status, current_time
                )
                if self.__emergency_stop_is_active():
                    command = ControlCommand(
                        command.rho,
                        command.alpha,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                    )

                self.hardware.motors.apply_command(command)

                next_point = ll_path.waypoints[0] if ll_path.waypoints else None
                self.logger.capture_telemetry(
                    current_time,
                    sensor_data,
                    state,
                    goal,
                    command,
                    next_point,
                )
                self.logger.update_obstacle_state(
                    current_time,
                    self.ll_planning.safety_status.has_moving_obstacle,
                    sensor_data,
                )
                self.logger.update_idle_state(current_time, state)

                if self.__should_flush(current_time):
                    print(f"Unit {self.unit_id}: saving logging batch...")
                    self.logger.flush()
                    self.last_db_save = current_time
        finally:
            print(f"Unit {self.unit_id}: controller stopped, flushing logging data...")
            self.hardware.motors.stop()
            try:
                self.logger.stop(self.hardware.get_time())
            finally:
                self.logger.clear_realtime()

    def __get_updated_goal(self, current_time, state):
        goal = Position(*self.task.get_goal(self.goal_index))
        dist_e, _ = calculate_control_errors(state, goal)

        if dist_e < self.planning_config.goal_reached_thresh:
            self.logger.log_target_reached(
                current_time,
                target_index=self.goal_index,
                target=self.task.get_goal(self.goal_index),
            )
            print(f"Unit {self.unit_id}: goal reached")
            self.goal_index = (self.goal_index + 1) % self.task.num_goals()
            goal = Position(*self.task.get_goal(self.goal_index))
        return goal

    def __should_flush(self, current_time):
        return current_time - self.last_db_save >= self.log_config.log_interval

    @staticmethod
    def __emergency_stop_is_active():
        return os.path.isfile(os.path.join(LOGS_DIR, "emergency_stop.flag"))

    @staticmethod
    def __clear_emergency_stop():
        try:
            os.remove(os.path.join(LOGS_DIR, "emergency_stop.flag"))
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    AGVSimulation().run()
