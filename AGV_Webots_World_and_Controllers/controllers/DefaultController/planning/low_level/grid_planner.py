import numpy as np
import cv2
import os
import heapq
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Tuple

from planning.planning import Path, GlobalMap
from planning.low_level.planning_interface import LowLevelPlanner, PlannerSafetyStatus
from perception.perception import SensorData
from localization.localization import RobotState, Position
from config import GridPlanningConfig, LOGS_DIR, PhysicalConfig, ObstacleTrackingConfig

# Single shared instance of the tracking tunables — edit values in config.py.
TRACK_CFG = ObstacleTrackingConfig()


# =============================================================================
# CLUSTER / TRACK DATA STRUCTURES
# =============================================================================
@dataclass
class Cluster:
    """A connected group of LiDAR hits representing one physical object.
    Coordinates are stored in BOTH pixel (local grid) and world frames so the
    tracker can persist world-frame state across robot motion."""
    centroid_px: Tuple[int, int]            # (cx, cy) in local grid pixels
    centroid_world: Tuple[float, float]     # (x, y) in world meters
    radius_px: float                        # bounding radius in pixels
    radius_m: float                         # bounding radius in meters
    point_pixels: List[Tuple[int, int]]     # all member pixels (for lethal-core drawing)


@dataclass
class Track:
    """A persistent tracked obstacle.

    Velocity is computed from a position HISTORY (oldest -> newest) rather than
    a single-frame delta + EMA. With ~10 frames at 10 Hz we average over ~1 s
    of motion, which gives a heading that is stable enough to display and to
    base decisions on. LiDAR jitter cancels out across the window.

    LiDAR provides geometry; YOLO OPTIONALLY refines `class_name`.
    """
    id: int
    x: float                                # latest world position
    y: float
    radius_m: float = 0.3                   # current cluster footprint
    class_name: str = "unknown"
    class_confidence: float = 0.0           # stickiness of YOLO label
    hits: int = 1                           # # of frames matched
    unseen: int = 0                         # # of consecutive frames unmatched
    age: int = 0                            # total frames since spawn
    last_heading: float = 0.0               # last known direction (kept even when the obstacle pauses)
    last_moving_time: Optional[float] = None
    last_point_pixels: List[Tuple[int, int]] = field(default_factory=list)
    # (x, y, time) — most recent at the back. Capped so we don't grow forever.
    history: Deque[Tuple[float, float, float]] = field(
        default_factory=lambda: deque(maxlen=TRACK_CFG.history_len)
    )

    # --- Derived velocity / heading ---
    # We compute these on demand from the history window rather than storing
    # them, so they're always consistent with the current history.
    def _baseline_velocity(self) -> Tuple[float, float]:
        """Simple time-averaged velocity: distance traveled / time elapsed
        between the OLDEST and NEWEST position in the history window (~2 s).
        Averaging over the whole window smooths out frame-to-frame LiDAR
        jitter without any fancy math."""
        if len(self.history) < TRACK_CFG.velocity_min_samples:
            return 0.0, 0.0
        x0, y0, t0 = self.history[0]
        x1, y1, t1 = self.history[-1]
        dt = t1 - t0
        if dt < TRACK_CFG.velocity_min_baseline_s:
            return 0.0, 0.0
        return (x1 - x0) / dt, (y1 - y0) / dt

    @property
    def vx(self) -> float:
        return self._baseline_velocity()[0]

    @property
    def vy(self) -> float:
        return self._baseline_velocity()[1]

    @property
    def speed(self) -> float:
        vx, vy = self._baseline_velocity()
        return float(np.hypot(vx, vy))

    @property
    def heading(self) -> float:
        # Heading is meaningful only when the object is clearly moving;
        # at near-zero speed, atan2 picks up pure noise direction.
        vx, vy = self._baseline_velocity()
        if np.hypot(vx, vy) < TRACK_CFG.heading_min_speed:
            return 0.0
        return float(np.arctan2(vy, vx))

    @property
    def confirmed(self) -> bool:
        # Confirmed once we've seen the object enough to trust geometry.
        return (self.hits >= TRACK_CFG.confirm_frames
                and self.age >= TRACK_CFG.confirm_frames)

    def is_moving_or_recent(self, current_time: float) -> bool:
        if not self.confirmed:
            return False
        if self.speed > TRACK_CFG.moving_speed_thresh:
            return True
        return (
            self.last_moving_time is not None
            and current_time - self.last_moving_time
            <= TRACK_CFG.recently_moving_retention_s
        )


def build_safety_status(
    tracks: List[Track],
    state: RobotState,
    current_time: float,
    robot_radius_m: float,
) -> PlannerSafetyStatus:
    confirmed_clearances = []
    moving_clearances = []
    for track in tracks:
        if not track.confirmed:
            continue
        dx = track.x - state.x
        dy = track.y - state.y
        forward_distance = dx * np.cos(state.theta) + dy * np.sin(state.theta)
        if forward_distance <= 0.0:
            continue

        center_distance = float(np.hypot(dx, dy))
        clearance = max(0.0, center_distance - track.radius_m - robot_radius_m)
        confirmed_clearances.append(clearance)
        if track.is_moving_or_recent(current_time):
            moving_clearances.append(clearance)

    return PlannerSafetyStatus(
        nearest_moving_clearance_m=(
            min(moving_clearances) if moving_clearances else None
        ),
        nearest_confirmed_clearance_m=(
            min(confirmed_clearances) if confirmed_clearances else None
        ),
    )


def is_target_cell_allowed(cell_value, config, allow_goal_in_padding: bool) -> bool:
    return (
        cell_value == config.free
        or (allow_goal_in_padding and cell_value == config.padding)
    )


class GridPlanner(LowLevelPlanner):
    def __init__(self, logger, lidar_specs, global_map: GlobalMap, unit_id):
        super().__init__(logger, lidar_specs, global_map, GridPlanningConfig())
        self.physical_config = PhysicalConfig()

        # Initialize Pathfinding and Visualization
        self.pathfinder = AStarPathfinder()
        self.visualizer = LocalGridVisualizer(unit_id)

        self.last_path = None
        self.last_plan_time = 0
        self.plan_interval = 0.1

        # Compatibility with Main Loop
        self.used_obstacle_ids = set()
        self.last_draw_time = 0.0

        # --- Perception pipeline: cluster -> track -> (optional) label -> pad ---
        # All tunables live in ObstacleTrackingConfig (config.py).
        self.cluster_extractor = ClusterExtractor(
            grid_res_m=self.config.grid_res,
            dilation_px=TRACK_CFG.cluster_dilation_px,
            min_pixels=TRACK_CFG.cluster_min_pixels,
            max_radius_m=TRACK_CFG.cluster_max_radius_m,
        )
        self.tracker = ObstacleTracker(
            assoc_gate_m=TRACK_CFG.assoc_gate_m,
            max_unseen_frames=TRACK_CFG.max_unseen_frames,
            min_dt=TRACK_CFG.min_frame_dt,
        )
        self.yolo_labeler = YoloLabeler(
            self.physical_config,
            project_world_to_camera_fn=self.__project_world_to_camera,
            label_stickiness=TRACK_CFG.label_stickiness,
        )
        self.last_track_time = 0.0

    def plan(
        self,
        state: RobotState,
        goal: Position,
        sensor_data: SensorData,
        allow_goal_in_padding: bool = False,
    ) -> Path:
        # Check if it's time to replan
        if not self.__should_replan(sensor_data):
            return self.last_path
    
        # --- 1. CREATE GRID ---
        raw_grid, all_obs_pixels = self.__create_raw_grid(sensor_data.pointcloud, state)
        static_walls, unknown_obstacles = self.__locate_walls(all_obs_pixels, state)

        # --- 2. OBSTACLE TRACKING ---
        tracks = self.__process_tracking(unknown_obstacles, state, sensor_data)
        self.__update_safety_status(tracks, state, sensor_data.time)

        # --- 3. APPLY PADDING ---
        grid = self.__apply_padding(raw_grid, static_walls, tracks, state)
        
        # --- 4. LOCAL GOAL ---
        center_px = self.config.grid_cells // 2
        proj_goal = self.__project_goal(state, goal)
        target_px, target_py = self.__world_to_pixel(state, proj_goal)
        # The final task goal may be placed inside conservative WALL padding,
        # but never inside padding generated by a tracked obstacle/peer robot.
        goal_padding_allowed = allow_goal_in_padding
        if allow_goal_in_padding and tracks:
            dynamic_grid = np.full_like(raw_grid, self.config.free)
            dynamic_grid = self.__apply_padding(dynamic_grid, [], tracks, state)
            goal_padding_allowed = (
                dynamic_grid[target_py, target_px] == self.config.free
            )

        # Padding remains costly but traversable; lethal occupied cells never are.
        if not is_target_cell_allowed(
            grid[target_py, target_px], self.config, goal_padding_allowed
        ):
            target_px, target_py = self.__find_nearest_free(grid, target_px, target_py)
        
        # --- 5. PATH FINDING ---
        path = self.pathfinder.find_path(grid, (center_px, center_px), (target_px, target_py))
        waypoints = self.__get_waypoints(state, path, distance=0.6)

        # --- VISUALIZE (Throttled to 10 FPS) ---
        if sensor_data.time - self.last_draw_time > 0.1:
            waypoints_px = [self.__world_to_pixel(state, wp) for wp in waypoints]
            # Convert tracks into a draw-friendly tuple list in the LOCAL grid frame.
            tracks_for_viz = []
            for t in tracks:
                tx_px, ty_px = self.__world_to_pixel(state, Position(t.x, t.y))
                # Pass member pixels so the visualizer can paint the WHOLE
                # cluster in the class color instead of just the centroid.
                tracks_for_viz.append((
                    tx_px, ty_px, t.class_name, t.last_heading, t.speed,
                    t.confirmed, t.last_point_pixels,
                ))
            self.visualizer.draw_grid(
                grid,
                state.theta,
                (target_px, target_py),
                path,
                waypoints_px,
                static_walls,
                semantic_obs=tracks_for_viz,
            )
            self.last_draw_time = sensor_data.time

        final_path = Path(waypoints)
        self.last_path = final_path
        
        return final_path
    
    def __should_replan(self, sensor_data:SensorData):
        should = sensor_data.time - self.last_plan_time > self.plan_interval or self.last_path is None
        if should:
            self.last_plan_time = sensor_data.time
        return should
    
    def __create_raw_grid(self, pointcloud, state:RobotState):
        """Creates the base map with only Free, Unknown, and Occupied spaces."""
        raw_grid = np.full((self.config.grid_cells, self.config.grid_cells), self.config.unknown, dtype=np.uint8)
        center = self.config.grid_cells // 2
        raw_grid[center, center] = self.config.free

        free_pixels, obs_pixels = self.__extract_grid_coordinates(pointcloud, state)
    
        # Raytrace free space
        for px, py in free_pixels:
            cv2.line(raw_grid, (center, center), (px, py), color=self.config.free, thickness=1)
            
        # Draw Obstacles (Raw hits)
        for px, py in obs_pixels:
            cv2.circle(raw_grid, (px, py), radius=1, color=self.config.occupied, thickness=-1)

        return raw_grid, obs_pixels

    def __locate_walls(self, all_obs_pixels, state: RobotState):
        static_walls = []
        unknown_obstacles = []

        for px, py in all_obs_pixels:
            # 1. Convert local grid pixel back to real-world coordinates
            # (Your grid is already world-aligned, so this function is perfect)
            world_pos = self.__pixel_to_world(state, px, py)
            
            # 2. Ask the global map if there is a known wall at this coordinate
            if self.global_map.is_occupied(world_pos.x, world_pos.y):
                static_walls.append((px, py))
            else:
                unknown_obstacles.append((px, py))

        return static_walls, unknown_obstacles
    
    def __process_tracking(self, unknown_obstacles, state: RobotState, sensor_data: SensorData):
        """LiDAR-first obstacle tracking pipeline.

        1. Cluster raw LiDAR hits into objects (geometry only — no YOLO needed).
        2. Update persistent tracks with EMA-smoothed velocity.
        3. (Optional) Augment track class labels via YOLO when the track lies
           inside the camera frustum AND a detection overlaps its projection.

        Returns:
            tracks: List[Track] — every active track, static OR moving. The
                    padding stage decides circular vs directional based on speed.
        """
        # 1. CLUSTER raw obstacle pixels into objects.
        clusters = self.cluster_extractor.extract(
            unknown_obstacles, state, self.__pixel_to_world, self.config.grid_cells
        )

        # 2. TRACK clusters across frames. The tracker keeps its own time
        # bookkeeping (each track stores a history of timestamped positions),
        # so all we pass is the wall-clock time of this frame.
        tracks = self.tracker.update(clusters, sensor_data.time)

        # 3. LABEL with YOLO where available (sticky, optional augmentation).
        #    If YOLO is disabled or the track is outside the FOV, class stays "unknown".
        if sensor_data.detections:
            self.yolo_labeler.label(tracks, state, sensor_data.detections)

        return tracks

    def __update_safety_status(
        self, tracks: List[Track], state: RobotState, current_time: float
    ) -> None:
        self.safety_status = build_safety_status(
            tracks,
            state,
            current_time,
            self.physical_config.footprint_radius,
        )
    
    def __project_world_to_camera(self, X_world, Y_world, Z_world, state: RobotState):
        """ Projects a 3D real-world point into the camera's 2D pixel space using pure math. """
        
        # 1. Get vector from robot to point in the global world frame
        dx_world = X_world - state.x
        dy_world = Y_world - state.y
        
        # 2. Rotate to Robot-centric coordinates (x_forward, y_left)
        x_forward = dx_world * np.cos(-state.theta) - dy_world * np.sin(-state.theta)
        y_left = dx_world * np.sin(-state.theta) + dy_world * np.cos(-state.theta)

        # If the point is physically behind the camera lens, it's impossible to see
        if x_forward <= 0.1:
            return None, None
            
        # 3. Camera Specs (from Webots .wbt file, via PhysicalConfig)
        fov = self.physical_config.camera_fov            # radians
        width = self.physical_config.camera_width_px     # pixels
        height = self.physical_config.camera_height_px   # pixels
        cam_z = self.physical_config.camera_height       # meters (mount height)
        
        # 4. Convert to Standard Camera Frame (Z forward, X right, Y down)
        Z_cam = x_forward
        X_cam = -y_left  
        Y_cam = cam_z - Z_world  # How far the LiDAR hit is below the camera lens
        
        # 5. Pinhole Projection Math (Calculate Focal Length in pixels)
        focal_length = (width / 2.0) / np.tan(fov / 2.0)
        
        u = int((width / 2.0) + focal_length * (X_cam / Z_cam))
        v = int((height / 2.0) + focal_length * (Y_cam / Z_cam))
        
        # 6. Check if the final pixel lands inside the physical 640x480 screen bounds
        if 0 <= u < width and 0 <= v < height:
            return u, v
        else:
            return None, None
        
    def __apply_padding(self, raw_grid, static_walls, tracks: List["Track"], state: RobotState):
        """Build the costmap by inflating obstacles, USING velocity for shape.

        Tracked obstacles are padded on their ACTUAL SHAPE: every LiDAR hit
        pixel is inflated by a fixed margin (obstacle_padding_m in config).
        The pad therefore scales with the real size of the object, while the
        margin itself stays constant frame to frame. MOVING tracks get the
        same shape stamped again at their predicted position
        (position + velocity * prediction_lookahead_s), so the pad only ever
        grows in the direction of motion.

        Pipeline:
          - WALLS  : tight base_pad circle (geometry is known and stable).
          - TRACKS : shape inflated by fixed margin; + predicted-position
                     copy if moving.
          - CORES  : actual LiDAR hit pixels stamped as OCCUPIED on top.
        """
        costmap = raw_grid.copy()
        base_pad = self.config.padding_pixels
        m_to_px = 1.0 / self.config.grid_res

        # 1. STATIC WALLS — tight pad.
        for px, py in static_walls:
            cv2.circle(costmap, (px, py), radius=base_pad,
                       color=self.config.padding, thickness=-1)

        # 2. TRACKED OBSTACLES — pad the object's ACTUAL SHAPE.
        # Every LiDAR hit pixel of the track is inflated by a FIXED margin
        # (obstacle_padding_m), so the pad follows the real footprint of the
        # object: a forklift gets a bigger pad than a person simply because
        # it occupies more pixels. The margin itself is constant -> stable.
        track_pad_px = int(TRACK_CFG.obstacle_padding_m * m_to_px)
        for t in tracks:
            for px, py in t.last_point_pixels:
                cv2.circle(costmap, (px, py), radius=track_pad_px,
                           color=self.config.padding, thickness=-1)

            # Directional growth: if the obstacle is moving, stamp the SAME
            # shape again at its predicted position (position + velocity *
            # prediction_lookahead_s). The planner then avoids the spot the
            # obstacle is heading to.
            if t.confirmed and t.speed > TRACK_CFG.moving_speed_thresh:
                tx_px, ty_px = self.__world_to_pixel(state, Position(t.x, t.y))
                fpx, fpy = self.__world_to_pixel(state, Position(
                    t.x + t.vx * TRACK_CFG.prediction_lookahead_s,
                    t.y + t.vy * TRACK_CFG.prediction_lookahead_s,
                ))
                dx, dy = fpx - tx_px, fpy - ty_px
                for px, py in t.last_point_pixels:
                    cv2.circle(costmap, (px + dx, py + dy),
                               radius=track_pad_px,
                               color=self.config.padding, thickness=-1)

        # 3. LETHAL CORES — stamp each hit as a small disk (radius=1, i.e. 3x3)
        #    so adjacent beams MERGE into a continuous arc, matching the
        #    "rounded and full" look of the raw grid. Single-pixel stamps
        #    leave visual gaps between sparse LiDAR returns.
        for px, py in static_walls:
            cv2.circle(costmap, (px, py), radius=1,
                       color=self.config.occupied, thickness=-1)
        for t in tracks:
            for px, py in t.last_point_pixels:
                if 0 <= px < self.config.grid_cells and 0 <= py < self.config.grid_cells:
                    cv2.circle(costmap, (px, py), radius=1,
                               color=self.config.occupied, thickness=-1)

        return costmap
    

    
    def __extract_grid_coordinates(self, pointcloud, state:RobotState):
        free_pixels, obs_pixels = [], []
        max_r = (self.config.grid_cells * self.config.grid_res) / 2.0
        center = self.config.grid_cells // 2

        # If a point jumps by more than this amount (in meters) 
        # from BOTH of its neighbors, it's a ghost.
  
        num_points = len(pointcloud)

        for i in range(num_points):
            angle, distance = pointcloud[i]

            # 1. SPIKE FILTER LOGIC
            if not np.isinf(distance):
                # Get the distance of the beam to the left and right (wrapping around the circle)
                prev_dist = pointcloud[i - 1][1]
                next_dist = pointcloud[(i + 1) % num_points][1]

                # If the neighbors are inf, we treat them as far away
                prev_dist = prev_dist if not np.isinf(prev_dist) else max_r
                next_dist = next_dist if not np.isinf(next_dist) else max_r

                # If this beam is totally isolated in distance, it's noise! Skip it.
                if abs(distance - prev_dist) > self.config.noise_tolerance and abs(distance - next_dist) > self.config.noise_tolerance:
                    continue # Drops the error, doesn't add it to the map

            # 2. STANDARD EXTRACTION LOGIC
            is_obs = not (np.isinf(distance) or distance >= max_r)
            draw_d = max_r * 1.5 if not is_obs else distance
            
            global_angle = state.theta - angle 
            px = int(center + (draw_d * np.cos(global_angle) / self.config.grid_res))
            py = int(center - (draw_d * np.sin(global_angle) / self.config.grid_res))
            
            free_pixels.append((px, py))
            if is_obs and 0 <= px < self.config.grid_cells and 0 <= py < self.config.grid_cells:
                obs_pixels.append((px, py))

        return free_pixels, obs_pixels

    def __project_goal(self, state:RobotState, goal:Position) -> Position:
        dx = goal.x - state.x
        dy = goal.y - state.y
        dist = np.hypot(dx, dy)

        # Il raggio massimo della nostra "bolla" di visione (es. 4 metri)
        limit = self.config.vision_distance / 2

        # Se il goal è già dentro il nostro campo visivo, non serve proiettarlo
        if dist <= limit:
            return goal

        # Se è fuori, calcoliamo il punto sul bordo del cerchio nella direzione del goal
        scale = limit / dist
        proj_x = state.x + dx * scale
        proj_y = state.y + dy * scale

        return Position(proj_x, proj_y)

    def __world_to_pixel(self, state: RobotState, pos: Position):
        # 1. Get raw distance in meters in world frame
        dx = pos.x - state.x
        dy = pos.y - state.y
        
        # 2. Map directly to pixels relative to the center
        # center + (meters / resolution)
        center = self.config.grid_cells // 2
        g_px = int(center + (dx / self.config.grid_res))
        g_py = int(center - (dy / self.config.grid_res)) # Minus because pixel Y grows downwards
        
        # 3. Clamp to grid bounds to prevent array index errors
        return max(0, min(self.config.grid_cells - 1, g_px)), max(0, min(self.config.grid_cells - 1, g_py))
    
    
    def __pixel_to_world(self, state: RobotState, px, py) -> Position:
        # 1. Get the meter offset from the robot (grid center)
        # dx is positive to the right (East)
        # dy is positive UP (North), so we subtract pixel Y from center
        dx_meters = (px - self.config.grid_cells // 2) * self.config.grid_res
        dy_meters = -(py - self.config.grid_cells // 2) * self.config.grid_res 

        # 2. Add these offsets directly to the robot's world position
        # (No rotation matrix needed because the grid is already world-aligned!)
        x_w = state.x + dx_meters
        y_w = state.y + dy_meters

        return Position(x_w, y_w)

    def __find_nearest_free(self, grid, px, py):
        """ 
        Searches along the circumference of the vision circle to find 
         the nearest non-blocked point.
        """
        center = self.config.grid_cells // 2
        
        # 1. Calculate the current radius and angle of the blocked goal
        dx = px - center
        dy = center - py  # Pixel Y is inverted
        radius = np.hypot(dx, dy)
        start_angle = np.arctan2(dy, dx)

        # 2. Sweep outward in angle (left and right)
        # We check up to 180 degrees in both directions
        step_deg = 2 
        for angle_offset in range(0, 180, step_deg):
            for direction in [1, -1]:
                # Calculate new test angle
                test_angle = start_angle + direction * np.radians(angle_offset)
                
                # Convert back to pixel coordinates at the SAME radius
                tx = int(center + radius * np.cos(test_angle))
                ty = int(center - radius * np.sin(test_angle))

                # 3. Validation
                if 0 <= tx < self.config.grid_cells and 0 <= ty < self.config.grid_cells:
                    if grid[ty, tx] in {self.config.free, self.config.unknown}:
                        return tx, ty

        # Fallback: if the entire circumference is blocked, 
        # only then search inwards using the old spiral
        return self.__spiral_fallback(grid, px, py)

    def __spiral_fallback(self, grid, px, py):
        """ The original square search as a last resort. """
        for r in range(1, 15):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    nx, ny = px + dx, py + dy
                    if 0 <= nx < self.config.grid_cells and 0 <= ny < self.config.grid_cells:
                        if grid[ny, nx] in {self.config.free, self.config.unknown}:
                            return nx, ny
        return self.config.grid_cells // 2, self.config.grid_cells // 2
    
    def __get_waypoints(self, state, path, distance):
        if not path or len(path) < 2:
            return []

        waypoints = []

        # --- start point ---
        px0, py0 = path[0]
        prev = self.__pixel_to_world(state, px0, py0)

        accumulated = 0.0

        for px, py in path[1:]:
            curr = self.__pixel_to_world(state, px, py)

            dx = curr.x - prev.x
            dy = curr.y - prev.y
            segment_length = np.hypot(dx, dy)

            while accumulated + segment_length >= distance:
                remaining = distance - accumulated
                t = remaining / segment_length

                # --- interpolate EXACT waypoint ---
                new_x = prev.x + t * dx
                new_y = prev.y + t * dy
                new_point = Position(new_x, new_y)

                waypoints.append(new_point)

                # move "prev" to this new waypoint
                prev = new_point

                # recompute remaining segment
                dx = curr.x - prev.x
                dy = curr.y - prev.y
                segment_length = np.hypot(dx, dy)

                accumulated = 0.0

            accumulated += segment_length
            prev = curr

        # --- ensure goal included ---
        last_px, last_py = path[-1]
        last = self.__pixel_to_world(state, last_px, last_py)

        if not waypoints or (np.hypot(last.x - waypoints[-1].x, last.y - waypoints[-1].y) > 1e-6):
            waypoints.append(last)

        return waypoints


class ClusterExtractor:
    """Groups individual LiDAR hits into coherent objects.

    Why: feeding raw pixels to a tracker creates one fragile micro-track per
    beam. Real obstacles are ~5-30 connected hits depending on range and size.
    We rasterize the hits on a small mask, close 1-px gaps with dilation, and
    extract connected components. Each component is one Cluster with a
    centroid (in both pixel and world frames) and a bounding radius.
    """

    def __init__(self, grid_res_m: float, dilation_px: int = 1,
                 min_pixels: int = 2, max_radius_m: float = 2.5):
        self.grid_res_m = grid_res_m
        self.dilation_px = max(0, int(dilation_px))
        self.min_pixels = max(1, int(min_pixels))
        self.max_radius_m = float(max_radius_m)

    def extract(self, unknown_pixels, state: RobotState,
                pixel_to_world_fn, grid_cells: int) -> List[Cluster]:
        if not unknown_pixels:
            return []

        # 1. Rasterize all unknown obstacle hits onto a binary mask.
        mask = np.zeros((grid_cells, grid_cells), dtype=np.uint8)
        for px, py in unknown_pixels:
            if 0 <= px < grid_cells and 0 <= py < grid_cells:
                mask[py, px] = 255

        # 2. Dilate slightly so neighbouring hits join into one component.
        #    This is what separates "a single forklift" from "12 ghost objects".
        if self.dilation_px > 0:
            k = 2 * self.dilation_px + 1
            kernel = np.ones((k, k), dtype=np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)

        # 3. Extract connected components.
        num_labels, labels = cv2.connectedComponents(mask)
        if num_labels <= 1:
            return []

        # 4. For each component, build a Cluster object. We restrict member
        #    pixels to the ORIGINAL unknown_pixels (not the dilated mask),
        #    so the lethal-core drawing later is faithful to real hits.
        pixel_set = set(unknown_pixels)
        clusters: List[Cluster] = []
        for label in range(1, num_labels):
            ys, xs = np.where(labels == label)
            if len(xs) == 0:
                continue

            cx = int(np.mean(xs))
            cy = int(np.mean(ys))

            # Bounding radius in pixels (max distance from centroid).
            dx = xs - cx
            dy = ys - cy
            r_px = float(np.sqrt(np.max(dx * dx + dy * dy)))
            r_m = r_px * self.grid_res_m

            # Reject things that look like long wall segments — those should
            # have been pre-filtered, but in case the global map misses them,
            # we skip clusters that are too elongated/large to be a real object.
            if r_m > self.max_radius_m:
                continue

            member_pixels = [(int(x), int(y)) for x, y in zip(xs, ys)
                             if (int(x), int(y)) in pixel_set]
            if len(member_pixels) < self.min_pixels:
                continue

            world_pos = pixel_to_world_fn(state, cx, cy)
            clusters.append(Cluster(
                centroid_px=(cx, cy),
                centroid_world=(world_pos.x, world_pos.y),
                radius_px=r_px,
                radius_m=r_m,
                point_pixels=member_pixels,
            ))
        return clusters


class ObstacleTracker:
    """Persistent obstacle tracker operating on CLUSTERS (not raw pixels).

    Velocity is derived from a POSITION HISTORY (deque per track), not a
    single-frame delta. We compute speed/heading as (newest - oldest) / dt
    across the whole history window — typically ~1 s. That long baseline kills
    LiDAR jitter so the heading stays stable, instead of swinging every frame.

    Workflow per frame:
      1. PREDICT  : project every existing track forward by its current
                    velocity * dt (used only for association).
      2. ASSOCIATE: greedily match clusters to predicted track positions using a
                    distance gate.
      3. UPDATE   : matched tracks append a new (x, y, t) sample to history.
      4. SPAWN    : unmatched clusters spawn new tracks (unconfirmed).
      5. AGE OUT  : unmatched tracks coast briefly, then are deleted after
                    max_unseen_frames frames without a match.
    """

    def __init__(self, assoc_gate_m: float = 1.0,
                 max_unseen_frames: int = 8,
                 min_dt: float = 0.02):
        self.assoc_gate_m = float(assoc_gate_m)
        self.max_unseen_frames = int(max_unseen_frames)
        self.min_dt = float(min_dt)
        self.tracks: List[Track] = []
        self.next_id = 0
        self._last_time: Optional[float] = None

    def update(self, clusters: List[Cluster], current_time: float) -> List[Track]:
        # Compute frame dt (used only for prediction & coasting).
        if self._last_time is None:
            dt = self.min_dt
        else:
            dt = max(self.min_dt, current_time - self._last_time)
        self._last_time = current_time

        # --- 1. PREDICT ---
        predicted = []
        for t in self.tracks:
            predicted.append((t.x + t.vx * dt, t.y + t.vy * dt))

        # --- 2. ASSOCIATE (greedy nearest-neighbour with gating) ---
        unmatched_clusters = list(range(len(clusters)))
        matched_track_idxs = set()
        assignments: List[Tuple[int, int]] = []  # (track_idx, cluster_idx)

        if predicted and clusters:
            tx = np.array([p[0] for p in predicted])
            ty = np.array([p[1] for p in predicted])
            cx = np.array([c.centroid_world[0] for c in clusters])
            cy = np.array([c.centroid_world[1] for c in clusters])
            dx = tx[:, None] - cx[None, :]
            dy = ty[:, None] - cy[None, :]
            d = np.hypot(dx, dy)  # shape (n_tracks, n_clusters)

            d_work = d.copy()
            while d_work.size > 0:
                idx = np.argmin(d_work)
                ti, ci = np.unravel_index(idx, d_work.shape)
                if d_work[ti, ci] > self.assoc_gate_m:
                    break
                assignments.append((int(ti), int(ci)))
                matched_track_idxs.add(int(ti))
                d_work[ti, :] = np.inf
                d_work[:, ci] = np.inf
                if int(ci) in unmatched_clusters:
                    unmatched_clusters.remove(int(ci))

        # --- 3. UPDATE matched tracks: push a fresh history sample ---
        for ti, ci in assignments:
            cluster = clusters[ci]
            t = self.tracks[ti]
            new_x, new_y = cluster.centroid_world
            t.x = new_x
            t.y = new_y
            t.radius_m = cluster.radius_m
            t.last_point_pixels = cluster.point_pixels
            t.history.append((new_x, new_y, current_time))
            t.hits += 1
            t.unseen = 0
            t.age += 1
            # Remember the direction whenever the obstacle is actually moving,
            # so the arrow keeps pointing the right way even when it pauses
            # (the sim obstacles stop briefly at each end of their route).
            vx, vy = t.vx, t.vy
            if np.hypot(vx, vy) > TRACK_CFG.heading_min_speed:
                t.last_heading = float(np.arctan2(vy, vx))
            if t.confirmed and t.speed > TRACK_CFG.moving_speed_thresh:
                t.last_moving_time = current_time

        # --- 4. SPAWN new tracks ---
        for ci in unmatched_clusters:
            c = clusters[ci]
            new_track = Track(
                id=self.next_id,
                x=c.centroid_world[0],
                y=c.centroid_world[1],
                radius_m=c.radius_m,
                last_point_pixels=c.point_pixels,
            )
            new_track.history.append(
                (c.centroid_world[0], c.centroid_world[1], current_time)
            )
            self.tracks.append(new_track)
            self.next_id += 1

        # --- 5. AGE OUT unmatched tracks ---
        survivors: List[Track] = []
        for i, t in enumerate(self.tracks):
            if i in matched_track_idxs:
                survivors.append(t)
                continue
            # Coast: keep moving on inferred velocity for a few frames so a
            # briefly-occluded obstacle isn't immediately forgotten. We do
            # NOT append to history (that would make the long-baseline
            # velocity drift). Just bump unseen / age.
            t.x += t.vx * dt
            t.y += t.vy * dt
            t.unseen += 1
            t.age += 1
            if t.unseen <= self.max_unseen_frames:
                survivors.append(t)
        self.tracks = survivors

        return self.tracks


class YoloLabeler:
    """OPTIONAL augmentation: refines a track's `class_name` using YOLO.

    Design notes:
      - LiDAR tracking works WITHOUT this; YOLO only refines labels.
      - We project the track centroid into camera pixels (front-only FOV).
        If the projection lands inside any detection bbox, that's a "match".
      - `label_stickiness` controls how strongly we trust the existing label.
        A high value (~0.85) means a single bad YOLO frame won't overwrite a
        well-established label. This matters because in-sim YOLO is noisy.
      - If the centroid projects outside the FOV (camera is front-only, LiDAR
        is 360), the track keeps its previous label. This is the "LiDAR-only
        baseline" path — tracking continues, only labels age.
    """

    def __init__(self, physical_config: PhysicalConfig,
                 project_world_to_camera_fn,
                 label_stickiness: float = 0.85):
        self.cfg = physical_config
        self.project = project_world_to_camera_fn
        self.stickiness = float(label_stickiness)

    def label(self, tracks: List[Track], state: RobotState, detections) -> None:
        if not detections:
            return
        for t in tracks:
            u, v = self.project(t.x, t.y, self.cfg.lidar_height, state)
            if u is None or v is None:
                continue  # Outside camera FOV — leave label as-is (LiDAR-only).

            for det in detections:
                if det.xmin <= u <= det.xmax and det.ymin <= v <= det.ymax:
                    # Each match contributes ~(1 - stickiness) of evidence.
                    if t.class_name == det.class_name:
                        t.class_confidence = min(
                            1.0, t.class_confidence + (1 - self.stickiness)
                        )
                    elif t.class_confidence < 0.5:
                        # Only let YOLO REPLACE a label if the old one wasn't sticky yet.
                        t.class_name = det.class_name
                        t.class_confidence = 1 - self.stickiness
                    else:
                        # Decay the old label slightly — disagreement.
                        t.class_confidence *= self.stickiness
                    break



# --- HELPER CLASSES (Place these in the same file or import them) ---
class AStarPathfinder:
    def __init__(self):
        self.config = GridPlanningConfig()

    def find_path(self, grid, start, goal):
        neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        close_set, came_from = set(), {}
        gscore = {start: 0}
        fscore = {start: self.__heuristic(start, goal)}
        oheap = []
        heapq.heappush(oheap, (fscore[start], start))

        while oheap:
            current = heapq.heappop(oheap)[1]
            if current == goal:
                return self.__reconstruct_path(came_from, current)
            close_set.add(current)
            for i, j in neighbors:
                neighbor = current[0] + i, current[1] + j
                if not (0 <= neighbor[0] < self.config.grid_cells and 0 <= neighbor[1] < self.config.grid_cells): continue
                cell_value = grid[neighbor[1], neighbor[0]]
                if cell_value == self.config.occupied: continue # OCCUPIED
                
                move_cost = np.sqrt(i**2 + j**2)
                if cell_value == self.config.padding: move_cost += self.config.padding_cost # PADDING
                elif cell_value == self.config.unknown: move_cost += self.config.unknown_cost  # UNKNOWN

                tentative_g = gscore[current] + move_cost
                if neighbor in close_set and tentative_g >= gscore.get(neighbor, float('inf')): continue
                if tentative_g < gscore.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    gscore[neighbor] = tentative_g
                    fscore[neighbor] = tentative_g + self.__heuristic(neighbor, goal) * self.config.heuristic_weight
                    heapq.heappush(oheap, (fscore[neighbor], neighbor))
        return []

    def __heuristic(self, a, b):
        return np.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)

    def __reconstruct_path(self, came_from, current):
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        return path[::-1]

class LocalGridVisualizer:
    def __init__(self, unit_id, display_size=500):
        self.window_name = "Local Planner Grid"
        self.display_size = display_size
        self.unit_id = str(unit_id)
        self.config = GridPlanningConfig() # Instantiate config to access values and colors

    def draw_grid(self, grid_matrix, robot_theta, local_goal_px=None, path=None, waypoints_px=None, static_walls_px=None, semantic_obs=None):
        # 1. Create an empty BGR image with the same dimensions as the grid
        h, w = grid_matrix.shape
        color_image = np.zeros((h, w, 3), dtype=np.uint8)

        # 2. Map logical grid values directly to their respective BGR colors
        color_image[grid_matrix == self.config.unknown] = self.config.unknown_color
        color_image[grid_matrix == self.config.free] = self.config.free_color
        color_image[grid_matrix == self.config.padding] = self.config.padding_color
        color_image[grid_matrix == self.config.occupied] = self.config.occupied_color

        # 1. Paint Static Walls (Orange)
        if static_walls_px:
            for wx, wy in static_walls_px:
                if 0 <= wx < w and 0 <= wy < h:
                    cv2.circle(color_image, (wx, wy), radius=1, color=self.config.walls_color, thickness=-1)

        # 2. Paint Tracked Obstacles. We paint:
        #    - every CLUSTER MEMBER PIXEL in the class color (so the obstacle
        #      reads as a solid colored shape — same look as raw LiDAR hits
        #      but tinted by class / confidence);
        #    - a velocity ARROW, drawn at the local-grid scale, only when the
        #      track is confirmed AND moving fast enough that the heading is
        #      meaningful (otherwise the arrow would flicker).
        # We defer drawing arrows to AFTER the resize, so they look like the
        # robot's red arrow (clean and crisp at display resolution).
        arrows_to_draw = []   # list of ((grid_px, grid_py), heading, speed, color)
        if semantic_obs:
            for entry in semantic_obs:
                # Accept the older 5/6-tuples too (backward compat).
                if len(entry) == 7:
                    px, py, obj_class, heading, speed, confirmed, member_pixels = entry
                elif len(entry) == 6:
                    px, py, obj_class, heading, speed, confirmed = entry
                    member_pixels = []
                else:
                    px, py, obj_class, heading, speed = entry
                    confirmed = True
                    member_pixels = []

                if not (0 <= px < w and 0 <= py < h):
                    continue

                # Color by class (colors defined in ObstacleTrackingConfig).
                color = TRACK_CFG.unknown_track_color
                if obj_class == "person":
                    color = TRACK_CFG.person_color
                elif obj_class == "forklift":
                    color = TRACK_CFG.forklift_color
                # Dim unconfirmed tracks so the operator can tell at a glance
                # which ones are trusted.
                if not confirmed:
                    color = tuple(c // 2 for c in color)

                # Paint every member pixel of the cluster.
                for mpx, mpy in member_pixels:
                    if 0 <= mpx < w and 0 <= mpy < h:
                        color_image[mpy, mpx] = color
                # Centroid marker so the track identity is also clear.
                cv2.circle(color_image, (px, py), radius=1, color=color, thickness=-1)

                # Queue a velocity arrow for EVERY confirmed track. The heading
                # is the last KNOWN direction, so the arrow stays visible even
                # while the obstacle briefly pauses or the estimate settles.
                if confirmed:
                    arrows_to_draw.append(((px, py), heading, speed, color))


        if static_walls_px:
            for wx, wy in static_walls_px:
                if 0 <= wx < w and 0 <= wy < h:
                    cv2.circle(color_image, (wx, wy), radius=1, color=self.config.walls_color, thickness=-1)

        # 3. Resize the mapped color image to the display size
        display_image = cv2.resize(color_image, (self.display_size, self.display_size), interpolation=cv2.INTER_NEAREST)
        
        # Calculate scale for drawing paths and points
        scale = self.display_size / grid_matrix.shape[0]

        def to_screen(px_coords):
            return (int(px_coords[0] * scale + scale / 2), int(px_coords[1] * scale + scale / 2))

        # --- Draw Overlays ---
        if path and len(path) > 1:
            for i in range(len(path) - 1):
                cv2.line(display_image, to_screen(path[i]), to_screen(path[i+1]), (255, 0, 0), 2)

        if local_goal_px:
            cv2.circle(display_image, to_screen(local_goal_px), 8, (0, 255, 0), -1)
        if waypoints_px:
            for wp in waypoints_px:
                cv2.circle(display_image, to_screen(wp), 5, (0, 255, 255), -1)

        # Per-track PREDICTIVE velocity arrows. The tip points to where the
        # obstacle will be `lookahead_s` from now if it keeps current speed and
        # heading. Length on screen = predicted_distance_in_meters * (pixels
        # per meter), so the arrow's geometric length DIRECTLY encodes both
        # direction and speed. Drawn at display resolution so it looks clean
        # like the robot's red arrow.
        lookahead_s = TRACK_CFG.arrow_lookahead_s
        # Display pixels per world meter. scale = display_size / grid_cells,
        # grid_res = meters per grid cell, so px_per_m = scale / grid_res.
        px_per_m = scale / self.config.grid_res
        # Cap arrow length so a very fast track doesn't span the whole panel.
        max_arrow_len = int(self.display_size * TRACK_CFG.arrow_max_len_frac)

        for (gx, gy), heading, speed, color in arrows_to_draw:
            sx = int(gx * scale + scale / 2)
            sy = int(gy * scale + scale / 2)

            # Predicted travel in meters over the lookahead.
            dist_m = speed * lookahead_s
            arrow_len = min(max_arrow_len, dist_m * px_per_m)
            # Floor at a visible minimum so slow-but-confirmed motion is
            # still legible.
            arrow_len = max(float(TRACK_CFG.arrow_min_len_px), arrow_len)

            tx = int(sx + arrow_len * np.cos(heading))
            ty = int(sy - arrow_len * np.sin(heading))  # screen Y inverted

            # One fixed color for all velocity arrows (see config) so they
            # can't be confused with cluster pixels or the robot's red arrow.
            cv2.arrowedLine(display_image, (sx, sy), (tx, ty),
                            TRACK_CFG.arrow_color, 3, tipLength=0.25)

        # Draw Robot
        center = self.display_size // 2
        cv2.circle(display_image, (center, center), 7, (0, 0, 255), -1)
        tip = (int(center + 35 * np.cos(robot_theta)), int(center - 35 * np.sin(robot_theta)))
        cv2.arrowedLine(display_image, (center, center), tip, (0, 0, 255), 3)

        # Save the grid image to disk so the React/Vite web app can access it.
        os.makedirs(LOGS_DIR, exist_ok=True)
        cv2.imwrite(
            os.path.join(LOGS_DIR, f"local_planner_grid_{self.unit_id}.jpg"),
            display_image,
        )
