import os
import sys

# Setup paths for RobotLog and imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "logs"))
if LOG_DIR not in sys.path:
    sys.path.append(LOG_DIR)

from config import RobotConfig, GOAL_POSITIONS
from core.state import State, Position
from hardware.webots_interface import WebotsInterface
from webots.moving_walls import MovingWalls
from navigation.obstacle_avoidance import ObstacleAvoider
from control.kinematics import KinematicsController
from logger.robot_log import RobotLog 

class AGVSimulation:
    def __init__(self):
        # Configuration & Hardware
        self.config = RobotConfig()
        self.hardware = WebotsInterface(self.config)
        self.logger = self._init_logger()
        
        # Modules
        self.kinematics = KinematicsController(self.config)
        self.avoider = ObstacleAvoider(self.config, self.logger)
        self.state = State(0, 0, 0)
        
        # Initial Goal
        self.goal_index = 0
        self.current_goal = Position(*GOAL_POSITIONS[self.goal_index])
        
        # Environment
        self.moving_wall_1 = MovingWalls(self.hardware.timestep, self.hardware.robot, "_1")
        self.moving_wall_2 = MovingWalls(self.hardware.timestep, self.hardware.robot, "_2")
        
        # Timers
        self.last_print_time = 0.0
        self.last_db_save = 0.0

    def _init_logger(self):
        """Initializes and starts the custom RobotLog."""
        log_file_path = os.path.join(LOG_DIR, "robot_controller_runs.jsonl")
        logger = RobotLog(log_file_path, controller_version="v1")
        logger.start(self.hardware.get_time())
        return logger

    def check_goal_reached(self, current_time):
        """Checks distance to goal and loads the next one if reached."""
        # Calculate using the state from the PREVIOUS simulation tick
        dist_e, heading_e = self.state.calculate_errors(self.current_goal)
        
        if dist_e < self.config.GOAL_REACHED_THRESH:
            self.logger.log_target_reached(
                current_time, 
                target_index=self.goal_index, 
                target=GOAL_POSITIONS[self.goal_index]
            )
            print("GOAL REACHED!")
            
            # Load next goal
            self.goal_index = (self.goal_index + 1) % len(GOAL_POSITIONS)
            self.current_goal = Position(*GOAL_POSITIONS[self.goal_index])

    def run(self):
        """The main simulation execution loop."""
        
        # Initialize variables for the first console print
        dist_e, heading_e = self.state.calculate_errors(self.current_goal)
        lin_vel, ang_vel = 0.0, 0.0
        
        try:
            while self.hardware.is_alive():
                current_time = self.hardware.get_time()
                
                # --- 0. UPDATE ENVIRONMENT ---
                self.moving_wall_1.move_wall(current_time, 3, 0.1, 'y')
                self.moving_wall_2.move_wall(current_time, 5, 0.1, 'x')
                
                # --- 1. PRINTING & DATABASE SAVING (Based on previous tick's data) ---
                if current_time - self.last_db_save >= self.config.LOG_INTERVAL_SEC:
                    print("5s passed, saving log...")
                    self.logger.save()
                    self.logger.save_to_database()
                    self.last_db_save = current_time

                if current_time - self.last_print_time >= self.config.PRINT_INTERVAL_SEC:
                    v_l_real, v_r_real = self.hardware.get_wheel_velocity()
                    gps_x, gps_y = self.hardware.get_gps()
                    
                    sensor_data = {
                        "time": current_time,
                        "state": {"x": self.state.x, "y": self.state.y, "theta": self.state.theta},
                        "gps": {"x": gps_x, "y": gps_y},
                        "errors": {"distance": dist_e, "heading": heading_e},
                        "wheel_velocities": {"left": v_l_real, "right": v_r_real},
                        "robot_velocities": {"linear": lin_vel, "angular": ang_vel},
                        "goal_position": {"x": self.current_goal.x, "y": self.current_goal.y}
                    }
                    self.logger.log_realtime(sensor_data)
                    
                    print("="*40)
                    status = "GOAL REACHED!" if dist_e < self.config.GOAL_REACHED_THRESH else "MOVING..."
                    print(f"Status: {status}")
                    print(f"Time: {current_time:.2f}s")
                    print(f"\nGoal:\n  x: {self.current_goal.x:.1f} m\n  y: {self.current_goal.y:.1f} m")
                    print(f"\nState:\n  x: {self.state.x:.2f} m\n  y: {self.state.y:.2f} m\n  th: {self.state.theta:.2f} rad")
                    print(f"\nControl errors:\n  Distance: {dist_e:.1f} m\n  Heading: {heading_e:.2f} rad")
                    print(f"\nRobot velocities:\n  Linear : {lin_vel:.2f} m/s\n  Angular: {ang_vel:.2f} rad/s")
                    print("="*40)
                    
                    self.last_print_time = current_time

                # --- 2. CHECK GOAL ---
                # Checks goal BEFORE updating state (1-tick delay)
                self.check_goal_reached(current_time)
                
                # --- 3. SENSE & UPDATE STATE ---
                dL, dR = self.hardware.get_odometry()
                dS, dTheta = self.kinematics.calculate_odometry(dL, dR)
                self.state.update_with_odometry(dS, dTheta)
                
                gps_x, gps_y = self.hardware.get_gps()
                self.state.fuse_with_gps(gps_x, gps_y)
                
                # --- 4. CALCULATE NEW ERRORS ---
                dist_e, heading_e = self.state.calculate_errors(self.current_goal)
                dist_e = min(self.config.CONTROL_VISION_DISTANCE, dist_e) # Cap distance
                
                # --- 5. OBSTACLE AVOIDANCE ---
                pointcloud = self.hardware.read_lidar()
                fov, max_range = self.hardware.get_lidar_specs()
                
                safe_dist_e, safe_heading_e = self.avoider.obstacle_avoidance(
                    pointcloud, dist_e, heading_e, current_time, self.state, self.current_goal, fov, max_range
                )
                has_obstacle = len(self.avoider.used_obstacle_ids) > 0
                
                # --- 6. ACT (KINEMATICS) ---
                lin_vel, ang_vel = self.kinematics.calculate_velocity(safe_dist_e, safe_heading_e)
                w_l, w_r = self.kinematics.get_wheel_velocities(lin_vel, ang_vel)
                
                self.hardware.apply_wheel_velocities(w_l, w_r)
                
                # --- 7. LOG UPDATE ---
                obstacle_msg = f"obstacle(s) found at x={gps_x:.2f}; y={gps_y:.2f}" if has_obstacle else f"obstacle cleared at x={gps_x:.2f}; y={gps_y:.2f}"
                self.logger.update_obstacle_state(current_time, has_obstacle, obstacle_msg)
                self.logger.update(current_time, lin_vel, ang_vel)

        finally:
            print("Controller stopped, saving log...")
            self.logger.log_event(self.hardware.get_time(), "STOP", "Controller stopped")
            self.hardware.stop_motors()
            self.logger.save()
            self.logger.save_to_database()
            print("Log saved to database successfully!")


if __name__ == "__main__":
    app = AGVSimulation()
    app.run()