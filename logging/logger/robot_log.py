import json
import time
import urllib.error
import urllib.request


DEFAULT_SERVER_URL = "http://127.0.0.1:8080"


class RobotLog:
    """Controller-side event collector and HTTP persistence client."""

    def __init__(self, server_url=DEFAULT_SERVER_URL, unit_id="unknown", request_fn=None, sleep_fn=None):
        self.server_url = server_url.rstrip("/")
        self.unit_id = str(unit_id)
        self._request_fn = request_fn
        self._sleep = sleep_fn or time.sleep

        self.sim_id = None
        self.start_time = None
        self.last_time = None
        self.total_time = 0.0
        self.idle_time = 0.0
        self.obstacle_count = 0
        self.event_count = 0
        self.events = []
        self.event_telemetry = []
        self.failed_events = []
        self.failed_event_telemetry = []
        self.latest_telemetry = self._empty_telemetry()
        self.is_idle = False
        self.in_obstacle_state = False
        self._stopped = False

    @staticmethod
    def _empty_telemetry():
        return {
            "state_x": 0.0,
            "state_y": 0.0,
            "state_theta": 0.0,
            "gps_x": 0.0,
            "gps_y": 0.0,
            "error_distance": 0.0,
            "error_heading": 0.0,
            "current_vel_linear": 0.0,
            "current_vel_angular": 0.0,
            "target_vel_linear": 0.0,
            "target_vel_angular": 0.0,
            "next_point_x": None,
            "next_point_y": None,
        }

    def _post(self, endpoint, payload):
        if self._request_fn is not None:
            try:
                return self._request_fn(endpoint, payload)
            except Exception as exc:
                print(f"[RobotLog {self.unit_id}] Request to {endpoint} failed: {exc}")
                return None

        request = urllib.request.Request(
            f"{self.server_url}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            print(f"[RobotLog {self.unit_id}] Request to {endpoint} failed: {exc}")
            return None

    @staticmethod
    def _successful(response):
        return isinstance(response, dict) and response.get("status") == "success"

    def start(self, sim_time, attempts=10, retry_delay=1.0):
        if self.sim_id is not None:
            return True

        for attempt in range(attempts):
            response = self._post("/start", {"unit_id": self.unit_id})
            sim_id = response.get("sim_id") if self._successful(response) else None
            if isinstance(sim_id, int) and not isinstance(sim_id, bool) and sim_id > 0:
                self.sim_id = sim_id
                self.start_time = sim_time
                self.last_time = sim_time
                self.log_event(sim_time, "START", "Controller started")
                return True
            if attempt + 1 < attempts:
                self._sleep(retry_delay)

        print(
            f"[RobotLog {self.unit_id}] Logging service unavailable after "
            f"{attempts} start attempts."
        )
        return False

    def capture_telemetry(self, sensor_data, state, goal, command, next_point=None):
        """Keep the latest controller telemetry in memory for the next event."""
        self.latest_telemetry = {
            "state_x": state.x,
            "state_y": state.y,
            "state_theta": state.theta,
            "gps_x": sensor_data.gps[0],
            "gps_y": sensor_data.gps[1],
            "error_distance": command.rho,
            "error_heading": command.alpha,
            "current_vel_linear": state.v,
            "current_vel_angular": state.omega,
            "target_vel_linear": command.v,
            "target_vel_angular": command.omega,
            "next_point_x": next_point.x if next_point is not None else None,
            "next_point_y": next_point.y if next_point is not None else None,
        }

    def log_event(self, sim_time, event_type, details):
        if self.sim_id is None:
            return
        event = {
            "sim_id": self.sim_id,
            "sim_time": sim_time,
            "e_type": event_type,
            "details": details,
        }
        telemetry = {
            "sim_id": self.sim_id,
            "event_time": sim_time,
            "e_type": event_type,
            **self.latest_telemetry,
        }
        self.events.append(event)
        self.event_telemetry.append(telemetry)
        self.event_count += 1

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
        gps_x, gps_y = sensor_data.gps
        if has_obstacle:
            details = f"obstacle(s) found at x={gps_x:.2f}; y={gps_y:.2f}"
        else:
            details = f"obstacle cleared at x={gps_x:.2f}; y={gps_y:.2f}"

        if has_obstacle and not self.in_obstacle_state:
            self.obstacle_count += 1
            self.log_event(sim_time, "OBSTACLE_ENCOUNTER", details)
        elif not has_obstacle and self.in_obstacle_state:
            self.log_event(sim_time, "OBSTACLE_CLEARED", details)
        self.in_obstacle_state = has_obstacle

    def update_idle_state(self, current_time, state, idle_speed_threshold=1e-3):
        if self.start_time is None:
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
                details = f"linear_speed={state.v:.6f}, angular_speed={state.omega:.2f}"
                self.log_event(current_time, "IDLE_START", details)
            else:
                details = f"linear_speed={state.v:.6f}, angular_speed={state.omega:.2f}"
                self.log_event(current_time, "IDLE_END", details)
            self.is_idle = currently_idle
        self.last_time = current_time

    def _summary(self):
        return {
            "total_sim_time": self.total_time,
            "obstacle_count": self.obstacle_count,
            "total_idle_time": self.idle_time,
            "event_count": self.event_count,
        }

    def _send_batch(self, events, event_telemetry):
        if self.sim_id is None:
            return False
        response = self._post(
            "/save",
            {
                "unit_id": self.unit_id,
                "sim_id": self.sim_id,
                "summary": self._summary(),
                "events": events,
                "event_telemetry": event_telemetry,
            },
        )
        return self._successful(response)

    def flush(self):
        """Persist failed records first, preserving event order across retries."""
        if self.failed_events or self.failed_event_telemetry:
            if not self._send_batch(self.failed_events, self.failed_event_telemetry):
                self.failed_events.extend(self.events)
                self.failed_event_telemetry.extend(self.event_telemetry)
                self.events.clear()
                self.event_telemetry.clear()
                return False
            self.failed_events.clear()
            self.failed_event_telemetry.clear()
            if not self.events and not self.event_telemetry:
                return True

        current_events = list(self.events)
        current_telemetry = list(self.event_telemetry)
        if self._send_batch(current_events, current_telemetry):
            del self.events[: len(current_events)]
            del self.event_telemetry[: len(current_telemetry)]
            return True

        self.failed_events.extend(current_events)
        self.failed_event_telemetry.extend(current_telemetry)
        del self.events[: len(current_events)]
        del self.event_telemetry[: len(current_telemetry)]
        return False

    def stop(self, sim_time, attempts=10, retry_delay=1.0):
        if not self._stopped:
            self.log_event(sim_time, "STOP", "Controller stopped")
            self._stopped = True

        for attempt in range(attempts):
            if self.flush():
                return True
            if attempt + 1 < attempts:
                self._sleep(retry_delay)

        unsaved_events = len(self.failed_events) + len(self.events)
        unsaved_telemetry = len(self.failed_event_telemetry) + len(self.event_telemetry)
        print(
            f"[RobotLog {self.unit_id}] Shutdown left {unsaved_events} events and "
            f"{unsaved_telemetry} telemetry records unsaved."
        )
        return False
