CREATE TABLE Simulations (
  id INTEGER AUTO_INCREMENT PRIMARY KEY,
  unit_id VARCHAR(64) NOT NULL,
  total_sim_time TIME(6) NOT NULL,
  obstacle_count INTEGER NOT NULL,
  total_idle_time TIME(6) NOT NULL,
  event_count INTEGER NOT NULL
);

CREATE TABLE Events (
  sim_id INTEGER,
  sim_time TIME(6),
  e_type ENUM('START', 'STOP', 'IDLE_START','IDLE_END','OBSTACLE_ENCOUNTER','OBSTACLE_CLEARED','REACHED_TARGET', 'UNEXPECTED_BEHAVIOR') NOT NULL,
  details VARCHAR(128) NOT NULL,
  PRIMARY KEY (sim_id, sim_time, e_type),
  FOREIGN KEY (sim_id) REFERENCES Simulations(id)
);

CREATE TABLE EventTelemetry (
  id INTEGER AUTO_INCREMENT PRIMARY KEY,
  sim_id INTEGER NOT NULL,
  event_time TIME(6) NOT NULL,
  e_type ENUM('START', 'STOP', 'IDLE_START','IDLE_END','OBSTACLE_ENCOUNTER','OBSTACLE_CLEARED','REACHED_TARGET', 'UNEXPECTED_BEHAVIOR') NOT NULL,
  state_x DOUBLE NOT NULL,
  state_y DOUBLE NOT NULL,
  state_theta DOUBLE NOT NULL,
  gps_x DOUBLE NOT NULL,
  gps_y DOUBLE NOT NULL,
  error_distance DOUBLE NOT NULL,
  error_heading DOUBLE NOT NULL,
  current_vel_linear DOUBLE NOT NULL,
  current_vel_angular DOUBLE NOT NULL,
  target_vel_linear DOUBLE NOT NULL,
  target_vel_angular DOUBLE NOT NULL,
  next_point_x DOUBLE,
  next_point_y DOUBLE,
  UNIQUE (sim_id, event_time, e_type),
  FOREIGN KEY (sim_id) REFERENCES Simulations(id),
  FOREIGN KEY (sim_id, event_time, e_type) REFERENCES Events(sim_id, sim_time, e_type)
);
