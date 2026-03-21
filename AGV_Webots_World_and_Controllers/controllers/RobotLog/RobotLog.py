import os
import json
import random
import mysql.connector

class RobotLog:
    def __init__(self, log_file_path, controller_version):
        # TODO: remove self.log_file_path once the database is verified working
        self.log_file_path = log_file_path
        self.realtime_log_file_path = log_file_path.replace(".jsonl", "_realtime.jsonl") if log_file_path.endswith(".jsonl") else log_file_path + "_realtime.jsonl"
        self.realtime_panel = log_file_path.replace(".jsonl", "_realtime_panel.jsonl") if log_file_path.endswith(".jsonl") else log_file_path + "_realtime_panel.jsonl"
        
        # clear the realtime log file on start
        log_dir = os.path.dirname(self.realtime_log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        with open(self.realtime_log_file_path, "w", encoding="utf-8") as f:
            pass

        self.sim_id = random.randint(1, 1000000)
        self.controller_version = controller_version
        self.start_time = None
        self.last_time = None
        self.total_time = 0.0
        self.idle_time = 0.0
        self.obstacle_count = 0
        self.event_count = 0
        self.events = []
        # self.events = [(1.0, "START", "Controller started"), (2.5, "IDLE_START", "linear_speed=0.000"), 
        # (4.0, "IDLE_END", "linear_speed=0.500"), (5.0, "OBSTACLE_ENCOUNTER", "L=0.100, C=0.050, R=0.200"), 
        # (6.5, "OBSTACLE_CLEARED", "L=0.300, C=0.400, R=0.350"), (10.0, "STOP", "Controller stopped")]
        self.event_telemetry = []
        self.is_idle = False
        self.in_obstacle_state = False

    def start(self, sim_time):
        self.start_time = sim_time
        self.last_time = sim_time
        self.log_event(sim_time, "START", "Controller started")

    def log_event(self, sim_time, event_type, details):
        self.events.append((self.sim_id, sim_time, event_type, details))
        self.event_count += 1
        with open(self.realtime_log_file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                x = (
                    self.sim_id,
                    sim_time,
                    data.get("state", {}).get("x", 0.0),
                    data.get("state", {}).get("y", 0.0),
                    data.get("state", {}).get("theta", 0.0),
                    data.get("gps", {}).get("x", 0.0),
                    data.get("gps", {}).get("y", 0.0),
                    data.get("gps_diff", {}).get("dx", 0.0),
                    data.get("gps_diff", {}).get("dy", 0.0),
                    data.get("errors", {}).get("distance", 0.0),
                    data.get("errors", {}).get("heading", 0.0),
                    data.get("wheel_velocities", {}).get("left", 0.0),
                    data.get("wheel_velocities", {}).get("right", 0.0),
                    data.get("robot_velocities", {}).get("linear", 0.0),
                    data.get("robot_velocities", {}).get("angular", 0.0),
                )
            except json.JSONDecodeError:
                x = (self.sim_id, sim_time, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0, -1.0, 0.0, 0.0, 0.0, 0.0)
    
        self.event_telemetry.append(x)
        
    def log_target_reached(self, sim_time, target_index=None, target=None):
        details = "target reached"
        if target_index is not None:
            details += f", index={target_index}"
        if target is not None and len(target) == 2:
            details += f", x={target[0]:.3f}, y={target[1]:.3f}"
        self.log_event(sim_time, "REACHED_TARGET", details)

    def update(self, sim_time, linear_speed, angular_speed, idle_speed_threshold=1e-3):
        if self.start_time is None:   
            self.start(sim_time)
            return

        if self.last_time is None:
            self.last_time = sim_time

        delta_t = max(0.0, sim_time - self.last_time)
        self.total_time = max(0.0, sim_time - self.start_time)
        
        currently_idle = abs(linear_speed) <= idle_speed_threshold 
        #! if abs(linear_speed) <= idle_speed_threshold then currently_idle is True, else False
        if currently_idle:
            self.idle_time += delta_t

        if currently_idle != self.is_idle:
            if currently_idle:
                self.log_event(sim_time, "IDLE_START", f"linear_speed={linear_speed:.6f}, anglular_speed={angular_speed:.2f}")
            else:
                self.log_event(sim_time, "IDLE_END", f"linear_speed={linear_speed:.6f}, anglular_speed={angular_speed:.2f}")
            self.is_idle = currently_idle

        self.last_time = sim_time

    def update_obstacle_state(self, sim_time, has_obstacle, details=""):
        if has_obstacle and not self.in_obstacle_state:
            self.obstacle_count += 1
            self.log_event(sim_time, "OBSTACLE_ENCOUNTER", details)
        elif not has_obstacle and self.in_obstacle_state:
            self.log_event(sim_time, "OBSTACLE_CLEARED", details)

        self.in_obstacle_state = has_obstacle

    def log_realtime(self, sensor_data):
        with open(self.realtime_log_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(sensor_data) + "\n")
        with open(self.realtime_panel, "w", encoding="utf-8") as f:
            f.write(json.dumps(sensor_data) + "\n")

    # TODO: remove this method after datbase integration is verified working, as we will be saving directly to the database instead of a JSONL file
    def save(self):
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        run_payload = {
            "started_at": self.start_time,
            "ended_at": self.last_time,
            "total_time": self.total_time,
            "idle_time": self.idle_time,
            "obstacle_count": self.obstacle_count,
            "events": [
                {
                    "sim_time": sim_time,
                    "event_type": event_type,
                    "details": details,
                }
                for sim_time, event_type, details in self.events
            ],
        }

        with open(self.log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(run_payload) + "\n")

    def save_to_database(self):
        """
        Reads the robot_controller_runs JSONL file and inserts it into MySQL 
        in a single robust batch operation.
        """

        # Replace credentials/db with env variables or standard defaults as necessary
        db_host = os.getenv("DB_HOST", "127.0.0.1")
        db_port = int(os.getenv("DB_PORT", 3306))
        db_user = os.getenv("DB_USER", "root")
        db_password = os.getenv("DB_PASSWORD", "agv_pass") # Updated to match your docker container
        db_name = os.getenv("DB_NAME", "robot_db")

        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name
            )
            cursor = conn.cursor()

            insert_query_events = """
                INSERT INTO Events (
                    sim_id, sim_time, e_type, details
                ) VALUES (%s, %s, %s, %s)
            """

            insert_query_simulations = """
                INSERT INTO Simulations (
                    id, total_sim_time, obstacle_count, total_idle_time, event_count
                ) VALUES (%s, %s, %s, %s)
            """

            insert_query_events_telemetry = """
                INSERT INTO Simulations (
                    id, sim_id, event_time, state_x, state_y, state_theta, 
                    gps_x, gps_y, gps_dx, gps_dy, error_distance, error_heading,
                    wheel_vel_left, wheel_vel_right, robot_vel_linear, robot_vel_angular
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            # Batch insert using executemany for high performance
            cursor.executemany(insert_query_events, self.events)
            conn.commit()
            print(f"Successfully saved {len(self.events)} event records to the database.")

            cursor.execute(insert_query_simulations, (
                self.sim_id,
                self.controller_version,
                self.total_time,
                self.obstacle_count,
                self.idle_time,
                self.event_count
            ))
            conn.commit()
            print("Successfully saved simulation summary to the database.")

            cursor.executemany(insert_query_events_telemetry, self.event_telemetry)
            conn.commit()
            print(f"Successfully saved {len(self.event_telemetry)} event telemetry records to the database.")

        except Exception as e:
            print(f"Failed to save events to database: {e}")

        finally:
            if cursor is not None:
                try: cursor.close()
                except Exception: pass
            if conn is not None and conn.is_connected():
                try: conn.close()
                except Exception: pass
