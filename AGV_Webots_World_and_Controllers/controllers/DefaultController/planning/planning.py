from config import PlanningConfig
import numpy as np
import cv2

class Path:
    def __init__(self, waypoints):
        self.waypoints = waypoints  # [(x,y), ...]

class GlobalMap:
    def __init__(self, raw_obstacles):
        self.config = PlanningConfig()

         # 1. Store the raw polygon data (For High-Level Planner)
        self.raw_obstacles = raw_obstacles
        
        # 2. Pre-calculate grid dimensions to avoid doing it on every lookup
        self.width_px = int(self.config.world_width / self.config.global_map_res)
        self.height_px = int(self.config.world_height / self.config.global_map_res)
        
        # Assume world origin (0,0) is in the center of the grid
        self.origin_x_px = self.width_px // 2
        self.origin_y_px = self.height_px // 2
        
        # 3. Build the Occupancy Grid (For Low-Level Planner)
        self.grid = self._build_rasterized_grid()
        
    def _build_rasterized_grid(self):
        # cv2 requires uint8 arrays for drawing
        temp_grid = np.zeros((self.height_px, self.width_px), dtype=np.uint8)
        
        for cx, cy, w, h in self.raw_obstacles:
            # Convert metric center coordinates to pixel coordinates
            px = int(self.origin_x_px + (cx / self.config.global_map_res))
            py = int(self.origin_y_px - (cy / self.config.global_map_res))
            
            # Convert metric width/height to pixel dimensions
            w_px = int(w / self.config.global_map_res)
            h_px = int(h / self.config.global_map_res)
            
            top_left = (px - w_px // 2, py - h_px // 2)
            bottom_right = (px + w_px // 2, py + h_px // 2)
            
            # Draw a filled rectangle (1 = occupied)
            cv2.rectangle(temp_grid, top_left, bottom_right, color=1, thickness=-1)
            
        # Convert back to a boolean mask for faster lookups (True = Occupied)
        return temp_grid == 1

    def get_obstacles(self):
        """High-Level planner calls this to build its nodes/edges."""
        return self.raw_obstacles
        
    def is_occupied(self, x_meters, y_meters):
        """Low-Level planner calls this for Map Differencing."""
        px = int(self.origin_x_px + (x_meters / self.config.global_map_res))
        py = int(self.origin_y_px - (y_meters / self.config.global_map_res))
        
        # Boundary Check: If the LiDAR sees outside our known map, treat as NOT a known wall
        if not (0 <= px < self.width_px and 0 <= py < self.height_px):
            return False 
            
        # Calculate patch size based on tolerance
        patch_px = int(self.config.tolerance_m / self.config.global_map_res)
        
        # Define the bounding box for the patch, clamping to grid edges
        min_x = max(0, px - patch_px)
        max_x = min(self.width_px, px + patch_px + 1)
        min_y = max(0, py - patch_px)
        max_y = min(self.height_px, py + patch_px + 1)
        
        # Return True if ANY pixel within the tolerance patch is a wall
        return np.any(self.grid[min_y:max_y, min_x:max_x])

    def visualize(self, save_path=None):
        """Quickly displays or saves the rasterized global map for debugging."""
        # Convert boolean grid (True/False) to an image (255=White/Wall, 0=Black/Free)
        display_img = (self.grid * 255).astype(np.uint8)
        
        # If the map is small (e.g., 400x400 pixels), you might want to scale it up to see it better
        display_img = cv2.resize(display_img, (800, 800), interpolation=cv2.INTER_NEAREST)

        if save_path:
            import os
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            cv2.imwrite(save_path, display_img)
            print(f"[GlobalMap] Saved visualization to {save_path}")
        else:
            cv2.imshow("Global Grid Map Debug", display_img)
            print("[GlobalMap] Press any key on the window to close...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()