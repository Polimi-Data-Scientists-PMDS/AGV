import os
import json
import mysql.connector

class RobotLog:
    def __init__(self, log_file_path, controller_version="unknown"):
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

        # Ensure the realtime panel file exists before the first START event is logged.
        # It is read by log_event() even before the first sensor frame is available.
        with open(self.realtime_panel, "w", encoding="utf-8") as f:
            f.write("{}\n")

        self.controller_version = controller_version
        self.start_time = None
        self.last_time = None
        self.total_time = 0.0
        self.idle_time = 0.0
        self.obstacle_count = 0
        self.event_count = 0
        self.events = []
        self.event_telemetry = []
        self.is_idle = False
        self.in_obstacle_state = False

        # Replace credentials/db with env variables or standard defaults as necessary
        self.db_host = os.getenv("DB_HOST", "127.0.0.1")
        self.db_port = int(os.getenv("DB_PORT", 3306))
        self.db_user = os.getenv("DB_USER", "root")
        self.db_password = os.getenv("DB_PASSWORD", "agv_pass") # Updated to match your docker container
        self.db_name = os.getenv("DB_NAME", "agv_data")
        self.sim_id = self._next_local_sim_id()

        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name
            )
            cursor = conn.cursor()

            # Setup database simulations
            insert_query_simulations = """
                    INSERT INTO Simulations (
                        controller_version, total_sim_time, obstacle_count, total_idle_time, event_count
                    ) VALUES (%s, %s, %s, %s, %s)
                """
            cursor.execute(insert_query_simulations, (
                    self.controller_version,
                    self._seconds_to_mysql_time(0.0),
                    self.obstacle_count,
                    self._seconds_to_mysql_time(0.0),
                    self.event_count
                ))
            conn.commit()
            print("Successfully saved simulation summary to the database.")
            
            self.sim_id = cursor.lastrowid
            print(f"Saved sim_id={self.sim_id}")

        except Exception as e:
            print(f"Failed to initialize database entry for simulation: {e}")
        finally:
            if cursor is not None:
                try: cursor.close()
                except Exception: pass
            if conn is not None and conn.is_connected():
                try: conn.close()
                except Exception: pass


        # Write the initial simulation line to the dashboard JSONL.
        self._update_simulation()

    # Dashboard JSONL helpers (mirror of MySQL data for real-time dashboard display)

    @property
    def _jsonl_dir(self):
        return os.path.dirname(self.log_file_path) or "."

    def _next_local_sim_id(self):
        #Use negative ids when MySQL does not create a simulation row.
        path = os.path.join(self._jsonl_dir, "simulations.jsonl")
        ids = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        sim_id = json.loads(line).get("id")
                        if isinstance(sim_id, int):
                            ids.append(sim_id)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        negative_ids = [sim_id for sim_id in ids if sim_id < 0]
        return min(negative_ids, default=0) - 1

    def _update_simulation(self):
    
        #Overwrites the line for the current sim_id in simulations.jsonl.
        #If no line exists yet for this sim_id (first call from __init__),
        #a new line is appended. All previous simulation lines are preserved.
        (
            total_sim_time,
            obstacle_count,
            total_idle_time,
            event_count,
            sim_id,
        ) = (
            self._seconds_to_mysql_time(self.total_time),
            self.obstacle_count,
            self._seconds_to_mysql_time(self.idle_time),
            self.event_count,
            self.sim_id
        )
        
        record = {
            "id": sim_id,
            "total_sim_time": total_sim_time,
            "obstacle_count": obstacle_count,
            "total_idle_time": total_idle_time,
            "event_count": event_count,
        }
        path = os.path.join(self._jsonl_dir, "simulations.jsonl")
        os.makedirs(self._jsonl_dir, exist_ok=True)

        existing = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = [json.loads(line) for line in f if line.strip()]
        except FileNotFoundError:
            pass

        replaced = False
        for i, row in enumerate(existing):
            if row.get("id") == sim_id:
                existing[i] = record
                replaced = True
                break
        if not replaced:
            existing.append(record)

        with open(path, "w", encoding="utf-8") as f:
            for row in existing:
                f.write(json.dumps(row) + "\n")

    def _append_event(self):
        #Appends pending event lines to events.jsonl when data is saved.
        if not self.events:
            return

        path = os.path.join(self._jsonl_dir, "events.jsonl")
        os.makedirs(self._jsonl_dir, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            for sim_id, sim_time, event_type, details in self.events:
                record = {
                    "sim_id": sim_id,
                    "sim_time": self._seconds_to_mysql_time(sim_time),
                    "e_type": event_type,
                    "details": details,
                }
                f.write(json.dumps(record) + "\n")

    def _append_telemetry(self):
        #Appends pending telemetry lines to event_telemetry.jsonl when data is saved.
        if not self.event_telemetry:
            return

        path = os.path.join(self._jsonl_dir, "event_telemetry.jsonl")
        os.makedirs(self._jsonl_dir, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            for (
                sim_id, event_time, event_type,
                state_x, state_y, state_theta,
                gps_x, gps_y,
                error_distance, error_heading,
                current_vel_linear, current_vel_angular,
                target_vel_linear, target_vel_angular,
                next_point_x, next_point_y,
            ) in self.event_telemetry:
                record = {
                    "sim_id": sim_id,
                    "event_time": self._seconds_to_mysql_time(event_time),
                    "e_type": event_type,
                    "state_x": state_x, "state_y": state_y, "state_theta": state_theta,
                    "gps_x": gps_x, "gps_y": gps_y,
                    "error_distance": error_distance, "error_heading": error_heading,
                    "current_vel_linear": current_vel_linear, "current_vel_angular": current_vel_angular,
                    "target_vel_linear": target_vel_linear, "target_vel_angular": target_vel_angular,
                    "next_point_x": next_point_x, "next_point_y": next_point_y,
                }
                f.write(json.dumps(record) + "\n")

    @staticmethod
    def _seconds_to_mysql_time(seconds):
        total_microseconds = max(0, int(round(seconds * 1_000_000)))
        hours, remainder = divmod(total_microseconds, 3_600_000_000)
        minutes, remainder = divmod(remainder, 60_000_000)
        secs, micros = divmod(remainder, 1_000_000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{micros:06d}"

    def start(self, sim_time):
        self.start_time = sim_time
        self.last_time = sim_time
        self.log_event(sim_time, "START", "Controller started")

    def log_realtime(self, sensor_data, state, goal, command, next_point=None):
        data = {
            "time": sensor_data.time,
            "state": {"x": state.x, "y": state.y, "theta": state.theta},
            "gps": {"x": sensor_data.gps[0], "y": sensor_data.gps[1]},
            "errors": {"distance": command.rho, "heading": command.alpha},
            "current_velocities": {"linear": state.v, "angular": state.omega},
            "target_velocities": {"linear": command.v, "angular": command.omega},
            "goal_position": {"x": goal.x, "y": goal.y},
            "next_point": {"x": next_point.x, "y": next_point.y} if next_point else None
        }

        with open(self.realtime_log_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")
        with open(self.realtime_panel, "w", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")
    
    def log_event(self, sim_time, event_type, details):
        self.events.append((self.sim_id, sim_time, event_type, details))
        self.event_count += 1
        try:
            with open(self.realtime_panel, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"Warning: Realtime panel unavailable/corrupt at sim_time={sim_time}. Logging event telemetry with default values.")
            data = {}

        x = (
            self.sim_id,
            sim_time,
            event_type,
            data.get("state", {}).get("x", 0.0),
            data.get("state", {}).get("y", 0.0),
            data.get("state", {}).get("theta", 0.0),
            data.get("gps", {}).get("x", 0.0),
            data.get("gps", {}).get("y", 0.0),
            data.get("errors", {}).get("distance", 0.0),
            data.get("errors", {}).get("heading", 0.0),
            data.get("current_velocities", {}).get("linear", 0.0),
            data.get("current_velocities", {}).get("angular", 0.0),
            data.get("target_velocities", {}).get("linear", 0.0),
            data.get("target_velocities", {}).get("angular", 0.0),
            data.get("next_point", {}).get("x") if data.get("next_point") else None,
            data.get("next_point", {}).get("y") if data.get("next_point") else None,
        )

        self.event_telemetry.append(x)

    def log_target_reached(self, sim_time, target_index=None, target=None):
        details = "target reached"
        if target_index is not None:
            details += f", index={target_index}"
        if target is not None and len(target) == 2:
            details += f", x={target[0]:.3f}, y={target[1]:.3f}"
        self.log_event(sim_time, "REACHED_TARGET", details)

    def log_unexpected_behavior(self, sim_time, description):
        self.log_event(sim_time, "UNEXPECTED_BEHAVIOR", description)

    def update_obstacle_state(self, sim_time, has_obstacle, sensor_data):
        gps_x = sensor_data.gps[0]
        gps_y = sensor_data.gps[1]
        obstacle_msg = f"obstacle(s) found at x={gps_x:.2f}; y={gps_y:.2f}" if has_obstacle else f"obstacle cleared at x={gps_x:.2f}; y={gps_y:.2f}"
        if has_obstacle and not self.in_obstacle_state:
            self.obstacle_count += 1
            self.log_event(sim_time, "OBSTACLE_ENCOUNTER", obstacle_msg)
        elif not has_obstacle and self.in_obstacle_state:
            self.log_event(sim_time, "OBSTACLE_CLEARED", obstacle_msg)

        self.in_obstacle_state = has_obstacle

    def update_idle_state(self, current_time, state, idle_speed_threshold=1e-3):
        if self.start_time is None:   
            self.start(current_time)
            return
        
        if self.last_time is None:
            self.last_time = current_time

        delta_t = max(0.0, current_time - self.last_time)
        self.total_time = max(0.0, current_time - self.start_time)

        currently_idle = abs(state.v) <= idle_speed_threshold
        if currently_idle:
            self.idle_time += delta_t

        if currently_idle != self.is_idle:
            if currently_idle:
                self.log_event(current_time, "IDLE_START", f"linear_speed={state.v:.6f}, angular_speed={state.omega:.2f}")
            else:
                self.log_event(current_time, "IDLE_END", f"linear_speed={state.v:.6f}, angular_speed={state.omega:.2f}")
            self.is_idle = currently_idle

        self.last_time = current_time

    # TODO: remove this method after database integration is verified working, as we will be saving directly to the database instead of a JSONL file
    def save(self):
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        for sim_id, sim_time, event_type, details in self.events:
            events_dict = {
                "controller_version": self.controller_version,
                "obstacle_count": self.obstacle_count,
                "event": [
                    {
                        "sim_id": sim_id,
                        "sim_time": sim_time,
                        "event_type": event_type,
                        "details": details,
                    }
                ],
            }
            with open(self.log_file_path, "a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(events_dict) + "\n")
        
        print(f"Saved {len(self.events)} events to {self.log_file_path}")

    def save_to_database(self):
        """
        Updates the simulation summary and batch-saves in-memory events
        and event telemetry records to MySQL.
        Also overwrites the current simulation line in simulations.jsonl
        so the dashboard always reflects the latest state.
        """
        self._update_simulation()
        self._append_event()
        self._append_telemetry()

        conn = None
        cursor = None
        v = "simulation summary"
        try:
            conn = mysql.connector.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name
            )
            cursor = conn.cursor()
            
            update_query_simulations = """
                UPDATE Simulations 
                SET total_sim_time = %s, obstacle_count = %s, total_idle_time = %s, event_count = %s
                WHERE id = %s
            """

            insert_query_events = """
                INSERT INTO Events (
                    sim_id, sim_time, e_type, details
                ) VALUES (%s, %s, %s, %s)
            """

            db_events = [
                (sim_id, self._seconds_to_mysql_time(sim_time), event_type, details)
                for sim_id, sim_time, event_type, details in self.events
            ]

            insert_query_events_telemetry = """
                INSERT INTO EventTelemetry (
                    sim_id, event_time, e_type, 
                    state_x, state_y, state_theta,
                    gps_x, gps_y, 
                    error_distance, error_heading,
                    current_vel_linear, current_vel_angular,
                    target_vel_linear, target_vel_angular,
                    next_point_x, next_point_y
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            db_event_telemetry = [
                (
                    sim_id, self._seconds_to_mysql_time(event_time), event_type,
                    state_x, state_y, state_theta,
                    gps_x, gps_y,
                    error_distance, error_heading,
                    current_vel_linear, current_vel_angular,
                    target_vel_linear, target_vel_angular,
                    next_point_x, next_point_y
                )
                for (
                    sim_id, event_time, event_type,
                    state_x, state_y, state_theta,
                    gps_x, gps_y,
                    error_distance, error_heading,
                    current_vel_linear, current_vel_angular,
                    target_vel_linear, target_vel_angular,
                    next_point_x, next_point_y
                )
                in self.event_telemetry
            ]

            cursor.execute(update_query_simulations, (
                self._seconds_to_mysql_time(self.total_time),
                self.obstacle_count,
                self._seconds_to_mysql_time(self.idle_time),
                self.event_count,
                self.sim_id
            ))
            
            conn.commit()
            print("Successfully saved simulation summary to the database.")

            v = "events"

            # Batch insert using executemany for high performance
            cursor.executemany(insert_query_events, db_events)
            conn.commit()
            print(f"Successfully saved {len(self.events)} event records to the database.")
            self.events = []
            print("Cleared events after saving to database.")

            v="event telemetry"

            # Batch insert using executemany for high performance
            cursor.executemany(insert_query_events_telemetry, db_event_telemetry)
            conn.commit()
            print(f"Successfully saved {len(self.event_telemetry)} event telemetry records to the database.")
            self.event_telemetry = []
            print("Cleared event telemetry after saving to database.")

            v = ""

        except Exception as e:
            print(f"Failed to save {v} to database: {e}")

        finally:
            if cursor is not None:
                try: cursor.close()
                except Exception: pass
            if conn is not None and conn.is_connected():
                try: conn.close()
                except Exception: pass
            if v == "events" or v == "simulation summary":
                self.events = []
                print("Cleared events after saving to jsonl file.")
                self.event_telemetry = []
                print("Cleared event telemetry after saving to jsonl file.")
            if v == "event telemetry":
                self.event_telemetry = []
                print("Cleared event telemetry after saving to jsonl file.")
