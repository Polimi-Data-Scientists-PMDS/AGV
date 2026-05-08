import os
import sys

from config import PlanningConfig, LogConfig, LOGGER_DIR, LOGS_DIR, use_react
from task import Task

if LOGGER_DIR not in sys.path:
    sys.path.append(LOGGER_DIR)

from hardware.hardware_interface import HardwareInterface
from hardware.webots_interface import WebotsInterface
from perception.perception import Perception, SensorData
from localization.localization import Localization, Position, RobotState


from planning.path import Path
from planning.high_level.planning_interface import HighLevelPlanner
from planning.low_level.planning_interface import LowLevelPlanner

from control.control import Control, ControlCommand

from webots.dynamic_environment import DynamicEnvironment
from utils.utils import calculate_control_errors
from robot_log import RobotLog 

# from planning.grid_obstacle_avoidance import GridObstacleAvoider
# from navigation.sector_obstacle_avoidance import SectorObstacleAvoider
#from perception.vision import ObjectDetector 
# from AGV_Webots_World_and_Controllers.controllers.DefaultController.control.OLD_kinematics import KinematicsController

class AGVSimulation:
    def __init__(self):
        # Configuration & Hardware
        self.task = Task()
        self.planning_config = PlanningConfig()
        self.log_config = LogConfig()

        
        # Modules
        self.hardware:      HardwareInterface   = WebotsInterface()
        self.logger:        RobotLog            = self.__init_logger()
        self.perception:    Perception          = Perception(self.hardware)
        self.localization:  Localization        = Localization()
        self.hl_planning:   HighLevelPlanner    = Task.hl_planner_class(self.logger)
        self.ll_planning:   LowLevelPlanner     = Task.ll_planner_class(self.logger, self.hardware.lidar.get_specs())
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
                
                # ---------------------------------------------------------------
                # --- 1. PERCEPTION ---
                sensor_data: SensorData = self.perception.perceive(current_time)

                # --- 2. LOCALIZATION ---
                state: RobotState = self.localization.localize(prev_state, sensor_data)
                prev_state: RobotState = state.copy()

                # --- 3. PLANNING ---
                goal: Position = self.__get_updated_goal(current_time, state)
                hl_path: Path = self.hl_planning.plan(state, goal)
                ll_goal = hl_path.waypoints[0]
                ll_path: Path = self.ll_planning.plan(state, ll_goal, sensor_data)

                # --- 4. CONTROL ---
                command: ControlCommand = self.control.follow_path(state, ll_path)
                
                # --- 5. ACTUATION ---
                self.hardware.motors.apply_command(command)
                # ---------------------------------------------------------------


                # --- PRINT AND LOG  ---
                if self.__should_print_and_log(current_time):
                    self.__print_and_log_data(current_time, sensor_data, state, goal, ll_path, command)
                    self.last_print_time = current_time
                else: 
                    self.logger.log_realtime(sensor_data, state, goal, command, ll_path.waypoints[0] if len(ll_path.waypoints) > 0 else None) 
                # --- UPDATE LOGGGER STATE  ---
                # TODO: add `has_obstacle` to the path object
                # self.logger.update_obstacle_state(current_time, path.has_obstacle, sensor_data)
                self.logger.update_obstacle_state(current_time, False, sensor_data)
                self.logger.update_idle_state(current_time, state)
                # --- UPDATE DATABASE ---
                if self.__should_save_to_database(current_time):
                    print("5s passed, saving log...")
                    self.logger.save()
                    self.logger.save_to_database()
                    self.last_db_save = current_time
                


        finally:
            print("Controller stopped, saving log...")
            self.logger.log_event(self.hardware.get_time(), "STOP", "Controller stopped")
            self.hardware.motors.stop()
            self.logger.save()
            self.logger.save_to_database()
            print("Log saved to database successfully!")

    def __init_logger(self):
        """Initializes and starts the custom RobotLog."""
        log_file_path = os.path.join(LOGS_DIR, "robot_controller_runs.jsonl")
        logger = RobotLog(log_file_path, controller_version="v1")
        logger.start(self.hardware.get_time())
        return logger

    def __get_updated_goal(self, current_time, state):
        """Checks distance to goal and loads the next one if reached."""
        # Calculate using the state from the PREVIOUS simulation tick
        goal = Position(*self.task.goal_positions[self.goal_index])
        dist_e, heading_e = calculate_control_errors(state, goal)
        
        if dist_e < self.planning_config.goal_reached_thresh:
            self.logger.log_target_reached(
                current_time, 
                target_index=self.goal_index, 
                target=self.task.goal_positions[self.goal_index]
            )
            print("GOAL REACHED!")
            
            # Load next goal
            self.goal_index = (self.goal_index + 1) % len(self.task.goal_positions)
            goal = Position(*self.task.goal_positions[self.goal_index])
        
        return goal

    def __should_save_to_database(self, current_time):
        return current_time - self.last_db_save >= self.log_config.log_interval

    def __should_print_and_log(self, current_time):
        return current_time - self.last_print_time >= self.log_config.print_interval

    def __print_and_log_data(self, current_time, sensor_data, state, goal, path, command):
        next_point = path.waypoints[0] if len(path.waypoints) > 0 else None
        self.logger.log_realtime(sensor_data, state, goal, command, next_point)
        
        # COMMENT PRINTS TO USE DASHBOARD

        # print("="*40)
        # # status = "GOAL REACHED!" if dist_e < self.config.GOAL_REACHED_THRESH else "MOVING..."
        # # print(f"Status: {status}")
        # print(f"Time: {current_time:.2f}s\n ")
        # print("---")
        # print(f"\nState:\t\t\t  x: {state.x:.2f} m\t  y: {state.y:.2f} m\t  th: {state.theta:.2f} rad")
        # print(f"\nVel:\t\t\t  v: {state.v:.2f} m/s\t  w: {state.omega:.2f} rad/s")
        # print("---")
        # print(f"\nNext:\t\t\t  " + f"x: {next_point.x:.1f} m\t  y: {next_point.y:.1f} m" if next_point is not None else "None")
        # print(f"\nGoal:\t\t\t  x: {goal.x:.1f} m\t  y: {goal.y:.1f} m")
        # print("---")
        # print(f"\nControl command:")
        # print(f"\t\t\t  r: {command.rho:.1f} m\t  alp: {command.alpha:.2f} rad")
        # print(f"\t\t\t  v: {command.v:.1f} m/s\t  w: {command.omega:.2f} rad/s")
        # print(f"\t\t\t  w_l: {command.w_l:.1f}\t  w_r: {command.w_r:.2f}")

        # # print(f"\nRobot velocities:\n  Linear : {lin_vel:.2f} m/s\n  Angular: {ang_vel:.2f} rad/s")
        # print("="*40)

def launch_dashboard():
    import socket
    import subprocess
    import os
    import sys
    import webbrowser
    import urllib.request

    dashboard_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "web-app", "app.py"))
    
    # Check if port 8501 is in use
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        in_use = s.connect_ex(('localhost', 8501)) == 0
        
    if not in_use:
        print("Starting Streamlit Dashboard on port 8501...")
        # Streamlit automatically opens a browser tab when it first runs
        subprocess.Popen([sys.executable, "-m", "streamlit", "run", dashboard_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("Dashboard appears to be running on port 8501. Opening browser...")
        
        # Verify it's actually responding, then open the browser window
        try:
            urllib.request.urlopen("http://localhost:8501/_stcore/health", timeout=2)
            webbrowser.open("http://localhost:8501")
        except Exception:
            # Even if health check fails, open it just in case
            webbrowser.open("http://localhost:8501")

if __name__ == "__main__":
    launch_dashboard()
    app = AGVSimulation()
    app.run()
