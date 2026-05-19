import numpy as np
import cv2
import os
import heapq

from planning.planning import Path, GlobalMap
from planning.low_level.planning_interface import LowLevelPlanner
from perception.perception import SensorData
from localization.localization import RobotState, Position
from config import GridPlanningConfig, LOGS_DIR

class GridPlanner(LowLevelPlanner):
    def __init__(self, logger, lidar_specs, global_map: GlobalMap):
        super().__init__(logger, lidar_specs, global_map, GridPlanningConfig())

        # Initialize Pathfinding and Visualization
        self.pathfinder = AStarPathfinder()
        self.visualizer = LocalGridVisualizer()

        self.last_path = None
        self.last_plan_time = 0
        self.plan_interval = 0.1

        # Compatibility with Main Loop
        self.used_obstacle_ids = set()
        self.last_draw_time = 0.0

    def plan(self, state:RobotState, goal:Position, sensor_data:SensorData) -> Path:
        # Check if it's time to replan
        if not self.__should_replan(sensor_data):
            return self.last_path
        
        # --- 1. CREATE GRID ---
        raw_grid, all_obs_pixels = self.__create_raw_grid(sensor_data.pointcloud, state)

        static_walls, unknown_obstacles = self.__locate_walls(all_obs_pixels, state)
        semantic_obstacles, unclassified_dynamic_obs = self.__locate_moving_obstacles(unknown_obstacles, state, sensor_data)

        # remove lidar errors??????
        # detect moving obstacles
        # semantic_obstacles, unclassified_dynamic_obs = self.__filter_against_camera(
        #     unknown_obstacles, state, sensor_data.yolo_detections, sensor_data.camera_matrices
        # )

        grid = self.__apply_padding(raw_grid, all_obs_pixels)
        #grid = self.__create_grid(sensor_data.pointcloud, state)

        # --- 2. LOCAL GOAL ---
        center_px = self.config.grid_cells // 2
        proj_goal = self.__project_goal(state, goal)
        target_px, target_py = self.__world_to_pixel(state, proj_goal)
        # If goal is inside an obstacle, find the nearest empty spot
        if grid[target_py, target_px] is not self.config.free:
            target_px, target_py = self.__find_nearest_free(grid, target_px, target_py)
        
        # --- 3. PATH FINDING ---
        path = self.pathfinder.find_path(grid, (center_px, center_px), (target_px, target_py))
        waypoints = self.__get_waypoints(state, path, distance=0.6)

        # --- 5. VISUALIZE (Throttled to 10 FPS) ---
        if sensor_data.time - self.last_draw_time > 0.1:
            waypoints_px = [self.__world_to_pixel(state, wp) for wp in waypoints]
            self.visualizer.draw_grid(grid, state.theta, (target_px, target_py), path, waypoints_px, static_walls)
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
    
    def __locate_moving_obstacles(self, unknown_obstacles, state: RobotState, sensor_data: SensorData):
        semantic_obstacles = []       # List of (px, py, class_name)
        unclassified_dynamic_obs = [] # List of (px, py)
        
        # You will need to add lidar_height_m to your GridPlanningConfig
        z_lidar = self.config.lidar_height_m 

        for px, py in unknown_obstacles:
            # 1. Convert grid pixel back to real-world (X, Y)
            world_pos = self.__pixel_to_world(state, px, py)
            
            # 2. Project 3D World Point to 2D Camera Pixel (u, v)
            u, v = self.__project_world_to_camera(world_pos.x, world_pos.y, z_lidar, sensor_data)
            
            # 3. Check against YOLO Bounding Boxes
            detected_class = None
            if u is not None and v is not None:
                for det in sensor_data.yolo_detections:
                    # Assuming det has xmin, ymin, xmax, ymax, and class_name
                    if det.xmin <= u <= det.xmax and det.ymin <= v <= det.ymax:
                        detected_class = det.class_name
                        break
            
            # 4. Sort the obstacle based on what we found
            if detected_class:
                semantic_obstacles.append((px, py, detected_class))
            else:
                unclassified_dynamic_obs.append((px, py))

        return semantic_obstacles, unclassified_dynamic_obs

    def __project_world_to_camera(self, X_world, Y_world, Z_world, sensor_data: SensorData):
        """ Projects a 3D real-world point into the camera's 2D pixel space. """
        # Create a 4D homogeneous coordinate vector [X, Y, Z, 1]
        point_3d = np.array([X_world, Y_world, Z_world, 1.0])
        
        # Multiply by your combined Camera Projection Matrix (P = K * T)
        # P is a 3x4 matrix provided by your sensor_data
        point_2d_homogeneous = np.dot(sensor_data.camera_matrices, point_3d)
        
        # Avoid division by zero
        if point_2d_homogeneous[2] <= 0:
            return None, None # The point is behind the camera!
            
        # Normalize to get actual pixel coordinates (u, v)
        u = int(point_2d_homogeneous[0] / point_2d_homogeneous[2])
        v = int(point_2d_homogeneous[1] / point_2d_homogeneous[2])
        
        return u, v
    
    def __apply_padding(self, raw_grid, obs_pixels):
        """Takes the raw map and creates the final costmap by inflating obstacles."""
        # Create a copy so the raw_grid remains intact for future semantic ID use
        costmap = raw_grid.copy()
        
        # Draw Padding
        for px, py in obs_pixels:
            cv2.circle(costmap, (px, py), radius=self.config.padding_pixels, color=self.config.padding, thickness=-1)
            
        # Redraw Obstacles on top of the padding 
        # (This ensures the center remains 'occupied' and isn't overwritten by the padding color)
        for px, py in obs_pixels:
            cv2.circle(costmap, (px, py), radius=1, color=self.config.occupied, thickness=-1)

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
    def __init__(self, display_size=500):
        self.window_name = "Local Planner Grid"
        self.display_size = display_size
        self.config = GridPlanningConfig() # Instantiate config to access values and colors

    def draw_grid(self, grid_matrix, robot_theta, local_goal_px=None, path=None, waypoints_px=None, static_walls_px=None):
        # 1. Create an empty BGR image with the same dimensions as the grid
        h, w = grid_matrix.shape
        color_image = np.zeros((h, w, 3), dtype=np.uint8)

        # 2. Map logical grid values directly to their respective BGR colors
        color_image[grid_matrix == self.config.unknown] = self.config.unknown_color
        color_image[grid_matrix == self.config.free] = self.config.free_color
        color_image[grid_matrix == self.config.padding] = self.config.padding_color
        color_image[grid_matrix == self.config.occupied] = self.config.occupied_color

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

        # Draw Robot
        center = self.display_size // 2
        cv2.circle(display_image, (center, center), 7, (0, 0, 255), -1) 
        tip = (int(center + 35 * np.cos(robot_theta)), int(center - 35 * np.sin(robot_theta)))
        cv2.arrowedLine(display_image, (center, center), tip, (0, 0, 255), 3)

        # Save the grid image to disk so the Streamlit dashboard can access it
        os.makedirs(LOGS_DIR, exist_ok=True)
        cv2.imwrite(os.path.join(LOGS_DIR, "local_planner_grid.jpg"), display_image)