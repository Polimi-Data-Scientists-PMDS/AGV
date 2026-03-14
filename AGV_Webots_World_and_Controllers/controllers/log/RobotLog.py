import os
import json
import uuid
import mysql.connector

class RobotLog:
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.realtime_log_file_path = log_file_path.replace(".jsonl", "_realtime.jsonl") if log_file_path.endswith(".jsonl") else log_file_path + "_realtime.jsonl"
        
        # clear the realtime log file on start
        log_dir = os.path.dirname(self.realtime_log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        with open(self.realtime_log_file_path, "w", encoding="utf-8") as f:
            pass

        self.start_time = None
        self.last_time = None
        self.total_time = 0.0
        self.idle_time = 0.0
        self.obstacle_count = 0
        self.events = []
        self.angular_velocity = []
        #* self.events = [(1.0, "START", "Controller started"), (2.5, "IDLE_START", "linear_speed=0.000"), (4.0, "IDLE_END", "linear_speed=0.500"), (5.0, "OBSTACLE_ENCOUNTER", "L=0.100, C=0.050, R=0.200"), (6.5, "OBSTACLE_CLEARED", "L=0.300, C=0.400, R=0.350"), (10.0, "STOP", "Controller stopped")]
        self.is_idle = False
        self.in_obstacle_state = False

    def start(self, sim_time):
        self.start_time = sim_time
        self.last_time = sim_time
        self.log_event(sim_time, "START", "Controller started")

    def log_event(self, sim_time, event_type, details=""):
        self.events.append((sim_time, event_type, details))

    def update(self, sim_time, linear_speed, angular_speed, idle_speed_threshold=1e-3):
        if self.start_time is None:
            self.start(sim_time)
            return

        if self.last_time is None:
            self.last_time = sim_time

        delta_t = max(0.0, sim_time - self.last_time)
        self.total_time = max(0.0, sim_time - self.start_time)
        
        currently_idle = abs(linear_speed) <= idle_speed_threshold #! if abs(linear_speed) <= idle_speed_threshold then currently_idle is True, else False
        if currently_idle:
            self.idle_time += delta_t

        if currently_idle != self.is_idle:
            if currently_idle:
                self.log_event(sim_time, "IDLE_START", f"linear_speed={linear_speed:.6f}")
            else:
                self.log_event(sim_time, "IDLE_END", f"linear_speed={linear_speed:.6f}")
            self.is_idle = currently_idle

        self.last_time = sim_time
        self.angular_velocity.append(angular_speed)


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
        Reads the realtime sensor_data JSONL file and inserts it into MySQL 
        in a single robust batch operation.
        """
        if not os.path.exists(self.realtime_log_file_path):
            print(f"Realtime log file not found: {self.realtime_log_file_path}")
            return

        simulation_id = str(uuid.uuid4())
        data_tuples = []


        with open(self.realtime_log_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    data_tuples.append((
                        simulation_id,
                        data.get("time", 0.0),
                        data.get("state", {}).get("x"),
                        data.get("state", {}).get("y"),
                        data.get("state", {}).get("theta"),
                        data.get("gps", {}).get("x"),
                        data.get("gps", {}).get("y"),
                        data.get("gps_diff", {}).get("dx"),
                        data.get("gps_diff", {}).get("dy"),
                        data.get("errors", {}).get("distance"),
                        data.get("errors", {}).get("heading"),
                        data.get("wheel_velocities", {}).get("left"),
                        data.get("wheel_velocities", {}).get("right"),
                        data.get("robot_velocities", {}).get("linear"),
                        data.get("robot_velocities", {}).get("angular")
                    ))
                except (json.JSONDecodeError, TypeError):
                    continue

        if not data_tuples:
            print("No realtime log data to save to database.")
            return

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

            insert_query = """
                INSERT INTO robot_telemetry (
                    simulation_id, sim_time, state_x, state_y, state_theta,
                    gps_x, gps_y, gps_dx, gps_dy, 
                    error_distance, error_heading, 
                    wheel_vel_left, wheel_vel_right, 
                    robot_vel_linear, robot_vel_angular
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Batch insert using executemany for high performance
            cursor.executemany(insert_query, data_tuples)
            conn.commit()
            print(f"Successfully saved {len(data_tuples)} telemetry records to the database.")

        except Exception as e:
            print(f"Failed to save telemetry to database: {e}")

        finally:
            if cursor is not None:
                try: cursor.close()
                except Exception: pass
            if conn is not None and conn.is_connected():
                try: conn.close()
                except Exception: pass
