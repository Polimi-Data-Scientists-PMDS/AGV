import os
import sys

# Setup paths for RobotLog and imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "logs"))
if LOG_DIR not in sys.path:
    sys.path.append(LOG_DIR)

from config import TaskConfig, PlanningConfig, LogConfig

from hardware.hardware_interface import HardwareInterface
from hardware.webots_interface import WebotsInterface
from perception.perception import Perception, SensorData
from localization.localization import Localization, Position, RobotState
# from planning.sector_planner import SectorPlanner
from planning.planning_interface import PlanningInterface
from planning.grid_planner import GridPlanner, Path
from control.control import Control, ControlCommand

from webots.dynamic_environment import DynamicEnvironment
from utils.utils import calculate_control_errors
from logger.robot_log import RobotLog 

# from planning.grid_obstacle_avoidance import GridObstacleAvoider
# from navigation.sector_obstacle_avoidance import SectorObstacleAvoider
#from perception.vision import ObjectDetector 
# from AGV_Webots_World_and_Controllers.controllers.DefaultController.control.OLD_kinematics import KinematicsController

class AGVSimulation:
    def __init__(self):
        # Configuration & Hardware
        self.task_config = TaskConfig()
        self.planning_config = PlanningConfig()
        self.log_config = LogConfig()

        
        # Modules
        self.hardware:      HardwareInterface   = WebotsInterface()
        self.logger:        RobotLog            = self.__init_logger()
        self.perception:    Perception          = Perception(self.hardware)
        self.localization:  Localization        = Localization()
        self.planning:      PlanningInterface   = GridPlanner(self.logger, self.hardware.lidar.get_specs())
        self.control:       Control             = Control()

        # Environment
        self.environment = DynamicEnvironment(self.hardware.robot)
        
        # Initial Goal
        self.goal_index = 0

        # Timers
        self.last_print_time = 0.0
        self.last_db_save = 0.0

    def run(self):
        """The main simulation execution loop."""
        
        # Initialize variables for the first console print
        # dist_e, heading_e = self.state.calculate_errors(self.current_goal)
        # lin_vel, ang_vel = 0.0, 0.0
        
        try:
            prev_state = self.localization.initial_state()

            while self.hardware.is_alive():
                current_time = self.hardware.get_time()
                
                # --- UPDATE ENVIRONMENT ---
                self.environment.update_all(current_time)
                # --- PRINTING & DATABASE SAVING (Based on previous tick's data) ---
                if self.__should_log(current_time):
                    print("5s passed, saving log...")
                    self.logger.save()
                    self.logger.save_to_database()
                    self.last_db_save = current_time
                
                # ---------------------------------------------------------------
                # --- 1. PERCEPTION ---
                sensor_data: SensorData = self.perception.perceive()

                # --- 2. LOCALIZATION ---
                state: RobotState = self.localization.localize(prev_state, sensor_data)
                prev_state: RobotState = state.copy()

                # --- 3. PLANNING ---
                goal: Position = self.__get_updated_goal(current_time, state)
                path: Path = self.planning.plan(state, goal, sensor_data)

                # --- 4. CONTROL ---
                command: ControlCommand = self.control.follow_path(state, path)
                
                # --- 5. ACTUATION ---
                self.hardware.motors.apply_command(command)
                # ---------------------------------------------------------------


                # --- PRINT  ---
                if self.__should_print(current_time):
                    self.__print_data(current_time, sensor_data, state, goal, path, command)
                    self.last_print_time = current_time
                # --- LOG UPDATE  ---
                # obstacle_msg = f"obstacle(s) found at x={gps_x:.2f}; y={gps_y:.2f}" if has_obstacle else f"obstacle cleared at x={gps_x:.2f}; y={gps_y:.2f}"
                # self.logger.update_obstacle_state(current_time, has_obstacle, obstacle_msg)
                # self.logger.update(current_time, lin_vel, ang_vel)
                


        finally:
            print("Controller stopped, saving log...")
            self.logger.log_event(self.hardware.get_time(), "STOP", "Controller stopped")
            self.hardware.motors.stop()
            self.logger.save()
            self.logger.save_to_database()
            print("Log saved to database successfully!")

    def __init_logger(self):
        """Initializes and starts the custom RobotLog."""
        log_file_path = os.path.join(LOG_DIR, "robot_controller_runs.jsonl")
        logger = RobotLog(log_file_path, controller_version="v1")
        logger.start(self.hardware.get_time())
        return logger

    def __get_updated_goal(self, current_time, state):
        """Checks distance to goal and loads the next one if reached."""
        # Calculate using the state from the PREVIOUS simulation tick
        goal = Position(*self.task_config.goal_positions[self.goal_index])
        dist_e, heading_e = calculate_control_errors(state, goal)
        
        if dist_e < self.planning_config.goal_reached_thresh:
            self.logger.log_target_reached(
                current_time, 
                target_index=self.goal_index, 
                target=self.task_config.goal_positions[self.goal_index]
            )
            print("GOAL REACHED!")
            
            # Load next goal
            self.goal_index = (self.goal_index + 1) % len(self.task_config.goal_positions)
            goal = Position(*self.task_config.goal_positions[self.goal_index])
        
        return goal

    def __should_log(self, current_time):
        return current_time - self.last_db_save >= self.log_config.log_interval

    def __should_print(self, current_time):
        return current_time - self.last_print_time >= self.log_config.print_interval

    def __print_data(self, current_time, sensor_data, state, goal, path, command):
        next_point = path.waypoints[0] if len(path.waypoints) > 0 else None

        v_l_real, v_r_real = self.hardware.motors.get_velocities()
        gps_x, gps_y = self.hardware.gps.get_position()
        
        # sensor_data = {
        #     "time": current_time,
        #     "state": {"x": state.x, "y": state.y, "theta": state.theta},
        #     "gps": {"x": gps_x, "y": gps_y},
        #     "errors": {"distance": dist_e, "heading": heading_e},
        #     "wheel_velocities": {"left": v_l_real, "right": v_r_real},
        #     "robot_velocities": {"linear": lin_vel, "angular": ang_vel},
        #     "goal_position": {"x": self.current_goal.x, "y": self.current_goal.y}
        # }
        # self.logger.log_realtime(sensor_data)
        
        print("="*40)
        # status = "GOAL REACHED!" if dist_e < self.config.GOAL_REACHED_THRESH else "MOVING..."
        # print(f"Status: {status}")
        print(f"Time: {current_time:.2f}s\n ")
        print("---")
        print(f"\nState:\t\t\t  x: {state.x:.2f} m\t  y: {state.y:.2f} m\t  th: {state.theta:.2f} rad")
        print(f"\nVel:\t\t\t  v: {state.v:.2f} m/s\t  w: {state.omega:.2f} rad/s")
        print("---")
        print(f"\nNext:\t\t\t  " + f"x: {next_point.x:.1f} m\t  y: {next_point.y:.1f} m" if next_point is not None else "None")
        print(f"\nGoal:\t\t\t  x: {goal.x:.1f} m\t  y: {goal.y:.1f} m")
        print("---")
        print(f"\nControl command:")
        print(f"\t\t\t  r: {command.rho:.1f} m\t  alp: {command.alpha:.2f} rad")
        print(f"\t\t\t  v: {command.v:.1f} m/s\t  w: {command.omega:.2f} rad/s")
        print(f"\t\t\t  w_l: {command.w_l:.1f}\t  w_r: {command.w_r:.2f}")

        # print(f"\nRobot velocities:\n  Linear : {lin_vel:.2f} m/s\n  Angular: {ang_vel:.2f} rad/s")
        print("="*40)

    # def __print_data(self, current_time, dist_e, heading_e, lin_vel, ang_vel):
    #     v_l_real, v_r_real = self.hardware.motors.get_velocities()
    #     gps_x, gps_y = self.hardware.gps.get_position()
        
    #     sensor_data = {
    #         "time": current_time,
    #         "state": {"x": self.state.x, "y": self.state.y, "theta": self.state.theta},
    #         "gps": {"x": gps_x, "y": gps_y},
    #         "errors": {"distance": dist_e, "heading": heading_e},
    #         "wheel_velocities": {"left": v_l_real, "right": v_r_real},
    #         "robot_velocities": {"linear": lin_vel, "angular": ang_vel},
    #         "goal_position": {"x": self.current_goal.x, "y": self.current_goal.y}
    #     }
    #     self.logger.log_realtime(sensor_data)
        
    #     print("="*40)
    #     status = "GOAL REACHED!" if dist_e < self.config.GOAL_REACHED_THRESH else "MOVING..."
    #     print(f"Status: {status}")
    #     print(f"Time: {current_time:.2f}s")
    #     print(f"\nGoal:\n  x: {self.current_goal.x:.1f} m\n  y: {self.current_goal.y:.1f} m")
    #     print(f"\nState:\n  x: {self.state.x:.2f} m\n  y: {self.state.y:.2f} m\n  th: {self.state.theta:.2f} rad")
    #     print(f"\nControl errors:\n  Distance: {dist_e:.1f} m\n  Heading: {heading_e:.2f} rad")
    #     print(f"\nRobot velocities:\n  Linear : {lin_vel:.2f} m/s\n  Angular: {ang_vel:.2f} rad/s")
    #     print("="*40)


if __name__ == "__main__":
    app = AGVSimulation()
    app.run()