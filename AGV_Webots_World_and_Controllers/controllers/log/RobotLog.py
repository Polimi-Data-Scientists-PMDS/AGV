import os
import json

class RobotLog:
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.start_time = None
        self.last_time = None
        self.total_time = 0.0
        self.idle_time = 0.0
        self.obstacle_count = 0
        self.events = []
        #* self.events = [(1.0, "START", "Controller started"), (2.5, "IDLE_START", "linear_speed=0.000"), (4.0, "IDLE_END", "linear_speed=0.500"), (5.0, "OBSTACLE_ENCOUNTER", "L=0.100, C=0.050, R=0.200"), (6.5, "OBSTACLE_CLEARED", "L=0.300, C=0.400, R=0.350"), (10.0, "STOP", "Controller stopped")]
        self.is_idle = False
        self.in_obstacle_state = False

    def start(self, sim_time):
        self.start_time = sim_time
        self.last_time = sim_time
        self.log_event(sim_time, "START", "Controller started")

    def log_event(self, sim_time, event_type, details=""):
        self.events.append((sim_time, event_type, details))

    def update(self, sim_time, linear_speed, idle_speed_threshold=1e-3):
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

    def update_obstacle_state(self, sim_time, has_obstacle, details=""):
        if has_obstacle and not self.in_obstacle_state:
            self.obstacle_count += 1
            self.log_event(sim_time, "OBSTACLE_ENCOUNTER", details)
        elif not has_obstacle and self.in_obstacle_state:
            self.log_event(sim_time, "OBSTACLE_CLEARED", details)

        self.in_obstacle_state = has_obstacle

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
