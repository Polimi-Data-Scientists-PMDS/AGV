import argparse
import datetime
import decimal
import json
import math
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import mysql.connector


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_READ_LIMIT = 200
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_LOGS_DIR = os.path.join(PROJECT_ROOT, "logging", "logs")
READ_FILTER_NAMES = frozenset({"unit_id", "sim_id"})
ALLOWED_EVENT_TYPES = frozenset(
    {
        "START",
        "STOP",
        "IDLE_START",
        "IDLE_END",
        "OBSTACLE_ENCOUNTER",
        "OBSTACLE_CLEARED",
        "REACHED_TARGET",
        "UNEXPECTED_BEHAVIOR",
    }
)
TELEMETRY_FLOAT_FIELDS = (
    "state_x",
    "state_y",
    "state_theta",
    "gps_x",
    "gps_y",
    "error_distance",
    "error_heading",
    "current_vel_linear",
    "current_vel_angular",
    "target_vel_linear",
    "target_vel_angular",
)


class PayloadValidationError(ValueError):
    pass


class PersistenceError(RuntimeError):
    pass


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _require_numeric_unit_id(value):
    if not isinstance(value, str) or not value.isdigit():
        raise PayloadValidationError("unit_id must be a numeric string")
    return str(int(value))


def validate_start_payload(payload):
    if not isinstance(payload, dict):
        raise PayloadValidationError("request body must be an object")
    return _require_numeric_unit_id(payload.get("unit_id"))


def validate_read_query(query):
    if not isinstance(query, dict):
        raise PayloadValidationError("query parameters must be a mapping")

    unknown_names = sorted(set(query) - READ_FILTER_NAMES)
    if unknown_names:
        joined_names = ", ".join(unknown_names)
        raise PayloadValidationError(f"unknown query parameter(s): {joined_names}")

    normalized = {"unit_id": None, "sim_id": None}
    for name in READ_FILTER_NAMES:
        values = query.get(name)
        if values is None:
            continue
        if not isinstance(values, list) or len(values) != 1:
            raise PayloadValidationError(f"{name} must appear exactly once")

        value = values[0]
        if name == "unit_id":
            normalized[name] = _require_numeric_unit_id(value)
        elif not isinstance(value, str) or not value.isdigit() or int(value) <= 0:
            raise PayloadValidationError("sim_id must be a positive integer")
        else:
            normalized[name] = int(value)

    return normalized


def validate_empty_query(query):
    if not isinstance(query, dict):
        raise PayloadValidationError("query parameters must be a mapping")
    if query:
        names = ", ".join(sorted(query))
        raise PayloadValidationError(f"query parameter(s) are not allowed: {names}")


def _event_identity(record, time_field):
    return (
        record["sim_id"],
        seconds_to_mysql_time(record[time_field]),
        record["e_type"],
    )


def validate_save_payload(payload):
    if not isinstance(payload, dict):
        raise PayloadValidationError("request body must be an object")
    unit_id = _require_numeric_unit_id(payload.get("unit_id"))
    sim_id = payload.get("sim_id")
    if not _is_int(sim_id) or sim_id <= 0:
        raise PayloadValidationError("sim_id must be a positive integer")

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise PayloadValidationError("summary must be an object")
    for field in ("total_sim_time", "total_idle_time"):
        if not _is_number(summary.get(field)) or summary[field] < 0:
            raise PayloadValidationError(f"summary.{field} must be a nonnegative finite number")
    for field in ("obstacle_count", "event_count"):
        if not _is_int(summary.get(field)) or summary[field] < 0:
            raise PayloadValidationError(f"summary.{field} must be a nonnegative integer")

    events = payload.get("events")
    telemetry = payload.get("event_telemetry")
    if not isinstance(events, list) or not isinstance(telemetry, list):
        raise PayloadValidationError("events and event_telemetry must be arrays")

    event_identities = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise PayloadValidationError(f"events[{index}] must be an object")
        if event.get("sim_id") != sim_id:
            raise PayloadValidationError(f"events[{index}].sim_id does not match sim_id")
        if not _is_number(event.get("sim_time")) or event["sim_time"] < 0:
            raise PayloadValidationError(f"events[{index}].sim_time is invalid")
        if event.get("e_type") not in ALLOWED_EVENT_TYPES:
            raise PayloadValidationError(f"events[{index}].e_type is invalid")
        details = event.get("details")
        if not isinstance(details, str) or len(details) > 128:
            raise PayloadValidationError(f"events[{index}].details must be at most 128 characters")
        event_identities.append(_event_identity(event, "sim_time"))

    telemetry_identities = []
    for index, record in enumerate(telemetry):
        if not isinstance(record, dict):
            raise PayloadValidationError(f"event_telemetry[{index}] must be an object")
        if record.get("sim_id") != sim_id:
            raise PayloadValidationError(
                f"event_telemetry[{index}].sim_id does not match sim_id"
            )
        if not _is_number(record.get("event_time")) or record["event_time"] < 0:
            raise PayloadValidationError(f"event_telemetry[{index}].event_time is invalid")
        if record.get("e_type") not in ALLOWED_EVENT_TYPES:
            raise PayloadValidationError(f"event_telemetry[{index}].e_type is invalid")
        for field in TELEMETRY_FLOAT_FIELDS:
            if not _is_number(record.get(field)):
                raise PayloadValidationError(
                    f"event_telemetry[{index}].{field} must be a finite number"
                )
        for field in ("next_point_x", "next_point_y"):
            value = record.get(field)
            if value is not None and not _is_number(value):
                raise PayloadValidationError(
                    f"event_telemetry[{index}].{field} must be null or a finite number"
                )
        telemetry_identities.append(_event_identity(record, "event_time"))

    if len(set(event_identities)) != len(event_identities):
        raise PayloadValidationError("events contains duplicate identities")
    if len(set(telemetry_identities)) != len(telemetry_identities):
        raise PayloadValidationError("event_telemetry contains duplicate identities")
    if set(event_identities) != set(telemetry_identities):
        raise PayloadValidationError("events and event_telemetry identities must match")

    return {
        "unit_id": unit_id,
        "sim_id": sim_id,
        "summary": summary,
        "events": events,
        "event_telemetry": telemetry,
    }


def seconds_to_mysql_time(seconds):
    total_microseconds = max(0, int(round(seconds * 1_000_000)))
    hours, remainder = divmod(total_microseconds, 3_600_000_000)
    minutes, remainder = divmod(remainder, 60_000_000)
    secs, micros = divmod(remainder, 1_000_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{micros:06d}"


class PersistenceService:
    """Serialized owner of the MySQL connection and dashboard mirrors."""

    def __init__(self, connection_factory=None, logs_dir=DEFAULT_LOGS_DIR):
        self.connection_factory = connection_factory or self._connect_from_environment
        self.logs_dir = os.fspath(logs_dir)
        self.lock = threading.Lock()
        self.connection = None

    @staticmethod
    def _connect_from_environment():
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "agv_pass"),
            database=os.getenv("DB_NAME", "agv_data"),
        )

    def _get_connection(self):
        if self.connection is not None:
            try:
                self.connection.ping(reconnect=True, attempts=1, delay=0)
                return self.connection
            except Exception:
                try:
                    self.connection.close()
                except Exception:
                    pass
                self.connection = None
        self.connection = self.connection_factory()
        return self.connection

    @staticmethod
    def _fetch_rows(connection, query, parameters):
        cursor = connection.cursor()
        try:
            cursor.execute(query, tuple(parameters))
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def _read_simulations_from_connection(
        self, connection, unit_id=None, sim_id=None, limit=DEFAULT_READ_LIMIT
    ):
        clauses = []
        parameters = []
        if unit_id is not None:
            clauses.append("unit_id = %s")
            parameters.append(unit_id)
        if sim_id is not None:
            clauses.append("id = %s")
            parameters.append(sim_id)

        where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_clause = " LIMIT %s" if limit is not None else ""
        if limit is not None:
            parameters.append(limit)
        query = f"""
            SELECT id, unit_id, total_sim_time, obstacle_count, total_idle_time, event_count
            FROM Simulations{where_clause}
            ORDER BY id DESC{limit_clause}
        """
        rows = self._fetch_rows(connection, query, parameters)
        rows.reverse()
        return rows

    def read_simulations(self, unit_id=None, sim_id=None, limit=DEFAULT_READ_LIMIT):
        with self.lock:
            connection = None
            try:
                connection = self._get_connection()
                return self._read_simulations_from_connection(
                    connection, unit_id, sim_id, limit
                )
            except Exception as exc:
                raise PersistenceError(f"failed to read simulations: {exc}") from exc
            finally:
                if connection is not None:
                    self._rollback(connection)

    def _read_simulation_options_from_connection(self, connection):
        rows = self._fetch_rows(
            connection,
            """
            SELECT id, unit_id
            FROM Simulations
            ORDER BY id DESC
            """,
            (),
        )
        options_by_unit = {}
        for row in rows:
            unit_id = _require_numeric_unit_id(row["unit_id"])
            sim_id = row["id"]
            if not _is_int(sim_id) or sim_id <= 0:
                raise PersistenceError("simulation option id must be a positive integer")
            options_by_unit.setdefault(unit_id, []).append(sim_id)

        return [
            {"unit_id": unit_id, "sim_ids": sim_ids}
            for unit_id, sim_ids in sorted(
                options_by_unit.items(), key=lambda option: int(option[0])
            )
        ]

    def read_simulation_options(self):
        with self.lock:
            connection = None
            try:
                connection = self._get_connection()
                return self._read_simulation_options_from_connection(connection)
            except Exception as exc:
                raise PersistenceError(
                    f"failed to read simulation options: {exc}"
                ) from exc
            finally:
                if connection is not None:
                    self._rollback(connection)

    def _read_events_from_connection(
        self, connection, unit_id=None, sim_id=None, limit=DEFAULT_READ_LIMIT
    ):
        clauses = []
        parameters = []
        if unit_id is not None:
            clauses.append("s.unit_id = %s")
            parameters.append(unit_id)
        if sim_id is not None:
            clauses.append("e.sim_id = %s")
            parameters.append(sim_id)

        where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_clause = " LIMIT %s" if limit is not None else ""
        if limit is not None:
            parameters.append(limit)
        query = f"""
            SELECT s.unit_id, e.sim_id, e.sim_time, e.e_type, e.details
            FROM Events AS e
            JOIN Simulations AS s ON s.id = e.sim_id{where_clause}
            ORDER BY e.sim_id DESC, e.sim_time DESC, e.e_type DESC{limit_clause}
        """
        rows = self._fetch_rows(connection, query, parameters)
        rows.reverse()
        return rows

    def read_events(self, unit_id=None, sim_id=None, limit=DEFAULT_READ_LIMIT):
        with self.lock:
            connection = None
            try:
                connection = self._get_connection()
                return self._read_events_from_connection(
                    connection, unit_id, sim_id, limit
                )
            except Exception as exc:
                raise PersistenceError(f"failed to read events: {exc}") from exc
            finally:
                if connection is not None:
                    self._rollback(connection)

    def _read_event_telemetry_from_connection(
        self, connection, unit_id=None, sim_id=None, limit=DEFAULT_READ_LIMIT
    ):
        clauses = []
        parameters = []
        if unit_id is not None:
            clauses.append("s.unit_id = %s")
            parameters.append(unit_id)
        if sim_id is not None:
            clauses.append("t.sim_id = %s")
            parameters.append(sim_id)

        where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_clause = " LIMIT %s" if limit is not None else ""
        if limit is not None:
            parameters.append(limit)
        query = f"""
            SELECT s.unit_id, t.sim_id, t.event_time, t.e_type,
                   t.state_x, t.state_y, t.state_theta, t.gps_x, t.gps_y,
                   t.error_distance, t.error_heading,
                   t.current_vel_linear, t.current_vel_angular,
                   t.target_vel_linear, t.target_vel_angular,
                   t.next_point_x, t.next_point_y
            FROM EventTelemetry AS t
            JOIN Simulations AS s ON s.id = t.sim_id{where_clause}
            ORDER BY t.sim_id DESC, t.event_time DESC, t.e_type DESC{limit_clause}
        """
        rows = self._fetch_rows(connection, query, parameters)
        rows.reverse()
        return rows

    def read_event_telemetry(self, unit_id=None, sim_id=None, limit=DEFAULT_READ_LIMIT):
        with self.lock:
            connection = None
            try:
                connection = self._get_connection()
                return self._read_event_telemetry_from_connection(
                    connection, unit_id, sim_id, limit
                )
            except Exception as exc:
                raise PersistenceError(f"failed to read event telemetry: {exc}") from exc
            finally:
                if connection is not None:
                    self._rollback(connection)

    def read_database_snapshot(self, unit_id=None, sim_id=None):
        with self.lock:
            connection = None
            try:
                connection = self._get_connection()
                connection.start_transaction(consistent_snapshot=True, readonly=True)
                simulations = self._read_simulations_from_connection(
                    connection, unit_id, sim_id, DEFAULT_READ_LIMIT
                )
                events = self._read_events_from_connection(
                    connection, unit_id, sim_id, DEFAULT_READ_LIMIT
                )
                telemetry = self._read_event_telemetry_from_connection(
                    connection, unit_id, sim_id, DEFAULT_READ_LIMIT
                )
                return {
                    "simulations": simulations,
                    "events": events,
                    "telemetry": telemetry,
                }
            except Exception as exc:
                raise PersistenceError(f"failed to read database snapshot: {exc}") from exc
            finally:
                if connection is not None:
                    self._rollback(connection)

    def start_simulation(self, unit_id):
        with self.lock:
            connection = self._get_connection()
            cursor = None
            try:
                cursor = connection.cursor()
                cursor.execute(
                    """
                    INSERT INTO Simulations (
                        unit_id, total_sim_time, obstacle_count, total_idle_time, event_count
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (unit_id, seconds_to_mysql_time(0), 0, seconds_to_mysql_time(0), 0),
                )
                sim_id = cursor.lastrowid
                connection.commit()
            except Exception as exc:
                self._rollback(connection)
                raise PersistenceError(f"failed to create simulation: {exc}") from exc
            finally:
                if cursor is not None:
                    cursor.close()

            self._best_effort_rebuild()
            return sim_id

    def save(self, payload):
        with self.lock:
            connection = self._get_connection()
            cursor = None
            try:
                connection.start_transaction()
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT unit_id FROM Simulations WHERE id = %s FOR UPDATE",
                    (payload["sim_id"],),
                )
                row = cursor.fetchone()
                if row is None or str(row[0]) != payload["unit_id"]:
                    raise PayloadValidationError("sim_id is not owned by unit_id")

                summary = payload["summary"]
                cursor.execute(
                    """
                    UPDATE Simulations
                    SET total_sim_time = %s, obstacle_count = %s,
                        total_idle_time = %s, event_count = %s
                    WHERE id = %s
                    """,
                    (
                        seconds_to_mysql_time(summary["total_sim_time"]),
                        summary["obstacle_count"],
                        seconds_to_mysql_time(summary["total_idle_time"]),
                        summary["event_count"],
                        payload["sim_id"],
                    ),
                )

                if payload["events"]:
                    cursor.executemany(
                        """
                        INSERT INTO Events (sim_id, sim_time, e_type, details)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE sim_id = VALUES(sim_id)
                        """,
                        [
                            (
                                event["sim_id"],
                                seconds_to_mysql_time(event["sim_time"]),
                                event["e_type"],
                                event["details"],
                            )
                            for event in payload["events"]
                        ],
                    )

                if payload["event_telemetry"]:
                    cursor.executemany(
                        """
                        INSERT INTO EventTelemetry (
                            sim_id, event_time, e_type, state_x, state_y, state_theta,
                            gps_x, gps_y, error_distance, error_heading,
                            current_vel_linear, current_vel_angular,
                            target_vel_linear, target_vel_angular,
                            next_point_x, next_point_y
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE sim_id = VALUES(sim_id)
                        """,
                        [self._telemetry_values(record) for record in payload["event_telemetry"]],
                    )
                connection.commit()
            except PayloadValidationError:
                self._rollback(connection)
                raise
            except Exception as exc:
                self._rollback(connection)
                raise PersistenceError(f"failed to save batch: {exc}") from exc
            finally:
                if cursor is not None:
                    cursor.close()

            self._best_effort_rebuild()

    @staticmethod
    def _telemetry_values(record):
        return (
            record["sim_id"],
            seconds_to_mysql_time(record["event_time"]),
            record["e_type"],
            *(record[field] for field in TELEMETRY_FLOAT_FIELDS),
            record["next_point_x"],
            record["next_point_y"],
        )

    @staticmethod
    def _rollback(connection):
        try:
            connection.rollback()
        except Exception:
            pass

    def _best_effort_rebuild(self):
        try:
            self.rebuild_jsonl()
        except Exception as exc:
            print(f"Logging service JSONL rebuild failed after database commit: {exc}")

    def rebuild_jsonl(self):
        os.makedirs(self.logs_dir, exist_ok=True)
        connection = self._get_connection()
        queries = (
            (
                "simulations.jsonl",
                """
                SELECT id, unit_id, total_sim_time, obstacle_count, total_idle_time, event_count
                FROM Simulations ORDER BY id
                """,
            ),
            (
                "events.jsonl",
                """
                SELECT sim_id, sim_time, e_type, details
                FROM Events ORDER BY sim_id, sim_time, e_type
                """,
            ),
            (
                "event_telemetry.jsonl",
                """
                SELECT sim_id, event_time, e_type, state_x, state_y, state_theta,
                       gps_x, gps_y, error_distance, error_heading,
                       current_vel_linear, current_vel_angular,
                       target_vel_linear, target_vel_angular,
                       next_point_x, next_point_y
                FROM EventTelemetry ORDER BY sim_id, event_time, e_type
                """,
            ),
        )
        try:
            for filename, query in queries:
                cursor = connection.cursor()
                try:
                    cursor.execute(query)
                    columns = [description[0] for description in cursor.description]
                    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                finally:
                    cursor.close()
                self._write_jsonl_atomic(filename, rows)
        finally:
            # End the consistent read snapshot before the next save starts a transaction.
            self._rollback(connection)

    def _write_jsonl_atomic(self, filename, rows):
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.logs_dir, prefix=f".{filename}.", delete=False
            ) as temporary_file:
                temporary_path = temporary_file.name
                for row in rows:
                    temporary_file.write(json.dumps(row, default=self._json_default, sort_keys=True))
                    temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, os.path.join(self.logs_dir, filename))
        except Exception:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass
            raise

    @staticmethod
    def _json_default(value):
        if isinstance(value, datetime.timedelta):
            return seconds_to_mysql_time(value.total_seconds())
        if isinstance(value, (datetime.time, datetime.date, datetime.datetime)):
            return value.isoformat()
        if isinstance(value, decimal.Decimal):
            return float(value)
        raise TypeError(f"cannot serialize {type(value).__name__}")


class LoggingRequestHandler(BaseHTTPRequestHandler):
    service = None

    def do_GET(self):
        parsed_url = urlsplit(self.path)
        try:
            if parsed_url.path == "/health" and not parsed_url.query:
                self._send_json(200, {"status": "success"})
            elif parsed_url.path == "/simulation-options":
                validate_empty_query(parse_qs(parsed_url.query, keep_blank_values=True))
                options = self.service.read_simulation_options()
                self._send_json(200, {"units": options}, no_store=True)
            elif parsed_url.path == "/simulations":
                filters = validate_read_query(
                    parse_qs(parsed_url.query, keep_blank_values=True)
                )
                rows = self.service.read_simulations(**filters)
                self._send_json(200, rows, no_store=True)
            elif parsed_url.path == "/events":
                filters = validate_read_query(
                    parse_qs(parsed_url.query, keep_blank_values=True)
                )
                rows = self.service.read_events(**filters)
                self._send_json(200, rows, no_store=True)
            elif parsed_url.path == "/event-telemetry":
                filters = validate_read_query(
                    parse_qs(parsed_url.query, keep_blank_values=True)
                )
                rows = self.service.read_event_telemetry(**filters)
                self._send_json(200, rows, no_store=True)
            elif parsed_url.path == "/database-snapshot":
                filters = validate_read_query(
                    parse_qs(parsed_url.query, keep_blank_values=True)
                )
                snapshot = self.service.read_database_snapshot(**filters)
                self._send_json(200, snapshot, no_store=True)
            else:
                self._send_json(404, {"status": "error", "message": "not found"})
        except PayloadValidationError as exc:
            self._send_json(400, {"status": "error", "message": str(exc)})
        except PersistenceError as exc:
            self._send_json(500, {"status": "error", "message": str(exc)})
        except Exception as exc:
            self._send_json(500, {"status": "error", "message": f"unexpected error: {exc}"})

    def do_POST(self):
        try:
            payload = self._read_json()
            if self.path == "/start":
                unit_id = validate_start_payload(payload)
                sim_id = self.service.start_simulation(unit_id)
                self._send_json(200, {"status": "success", "sim_id": sim_id})
            elif self.path == "/save":
                validated = validate_save_payload(payload)
                self.service.save(validated)
                self._send_json(200, {"status": "success"})
            else:
                self._send_json(404, {"status": "error", "message": "not found"})
        except PayloadValidationError as exc:
            self._send_json(400, {"status": "error", "message": str(exc)})
        except PersistenceError as exc:
            self._send_json(500, {"status": "error", "message": str(exc)})
        except Exception as exc:
            self._send_json(500, {"status": "error", "message": f"unexpected error: {exc}"})

    def _read_json(self):
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0]
        if content_type != "application/json":
            raise PayloadValidationError("Content-Type must be application/json")
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise PayloadValidationError("Content-Length is invalid") from exc
        if content_length <= 0 or content_length > 10_000_000:
            raise PayloadValidationError("request body length is invalid")
        try:
            return json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PayloadValidationError("request body is not valid JSON") from exc

    def _send_json(self, status_code, payload, no_store=False):
        body = json.dumps(payload, default=PersistenceService._json_default).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        if no_store:
            self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string, *args):
        print(f"Logging service: {format_string % args}")


def create_server(host=DEFAULT_HOST, port=DEFAULT_PORT, service=None):
    configured_service = service or PersistenceService()

    class ConfiguredHandler(LoggingRequestHandler):
        pass

    ConfiguredHandler.service = configured_service
    return ThreadingHTTPServer((host, port), ConfiguredHandler)


def main():
    parser = argparse.ArgumentParser(description="AGV MySQL logging service")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--logs-dir", default=DEFAULT_LOGS_DIR)
    args = parser.parse_args()

    service = PersistenceService(logs_dir=args.logs_dir)
    server = create_server(args.host, args.port, service)
    print(f"Logging service listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
