export type RobotData = {
  time: number;
  state: { x: number; y: number; theta: number };
  gps: { x: number; y: number };
  errors: { distance: number; heading: number };
  current_velocities: { linear: number; angular: number };
  target_velocities: { linear: number; angular: number };
  goal_position: { x: number; y: number };
  next_point: { x: number; y: number } | null;
};
