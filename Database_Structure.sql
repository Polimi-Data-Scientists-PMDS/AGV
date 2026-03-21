CREATE TABLE Simulations (
  id INTEGER PRIMARY KEY,
  controller_version VARCHAR(64) NOT NULL,
  total_sim_time TIME NOT NULL,
  obstacle_count INTEGER NOT NULL,
  total_idle_time TIME NOT NULL,
  event_count INTEGER NOT NULL
);

CREATE TABLE Events (
  sim_id INTEGER,
  sim_time TIME,
  e_type ENUM('START', 'STOP', 'IDLE_START','IDLE_END','OBSTACLE_ENCOUNTER','OBSTACLE_CLEARED','REACHED_TARGET') NOT NULL,
  details VARCHAR(128) NOT NULL,
  PRIMARY KEY (sim_id, sim_time),
  FOREIGN KEY (sim_id) REFERENCES Simulations(id)
);

CREATE TABLE EventTelemetry (
  id INTEGER AUTO_INCREMENT PRIMARY KEY,
  sim_id INTEGER NOT NULL,
  event_time TIME NOT NULL,
  state_x DOUBLE NOT NULL,
  state_y DOUBLE NOT NULL,
  state_theta DOUBLE NOT NULL,
  gps_x DOUBLE NOT NULL,
  gps_y DOUBLE NOT NULL,
  gps_dx DOUBLE NOT NULL,
  gps_dy DOUBLE NOT NULL,
  error_distance DOUBLE NOT NULL,
  error_heading DOUBLE NOT NULL,
  wheel_vel_left DOUBLE NOT NULL,
  wheel_vel_right DOUBLE NOT NULL,
  robot_vel_linear DOUBLE NOT NULL,
  robot_vel_angular DOUBLE NOT NULL,
  FOREIGN KEY (sim_id) REFERENCES Simulations(id),
  FOREIGN KEY (sim_id, event_time) REFERENCES Events(sim_id, sim_time)
);