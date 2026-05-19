import numpy as np
import heapq
import cv2

from planning.planning import Path, GlobalMap
from planning.high_level.planning_interface import HighLevelPlanner
from perception.perception import SensorData
from localization.localization import RobotState, Position
from config import VisGraphPlanningConfig, WorldConfig

class VisGraphPlanner(HighLevelPlanner):
    def __init__(self, logger, global_map: GlobalMap):
        super().__init__(logger, global_map)

        self.config = VisGraphPlanningConfig()
        self.raw_obstacles = self.global_map.get_obstacles()

        # 1. Static Map Data: List of inflated polygons (4 corners each)
        self.inflated_obstacles = self._prepare_obstacles(self.raw_obstacles)
        
        # 2. The Graph Nodes: All corners of all inflated obstacles
        self.static_nodes = self._extract_all_corners()
        
        # 3. The Static Visibility Matrix: Pre-calculates connections
        print("[VisGraph] Building static visibility graph... (This may take a second)")
        self.static_edges = self._build_static_visibility_graph()
        print(f"[VisGraph] Done! Found {len(self.static_nodes)} nodes.")

        # 4. Global Map Visualizer
        self.visualizer = GlobalVisVisualizer()
        self.last_path = None
        self.last_goal = None

    def plan(self, state: RobotState, goal: Position) -> Path:
        start_pos = Position(state.x, state.y)
        
        # If goal hasn't changed significantly, keep the old path
        if self.last_path and self.last_goal and \
           np.hypot(goal.x - self.last_goal.x, goal.y - self.last_goal.y) < self.config.change_goal_thresh:
            
            # Remove waypoints the robot has already reached
            while len(self.last_path.waypoints) > 1:
                next_wp = self.last_path.waypoints[0]
                dist_to_wp = np.hypot(start_pos.x - next_wp.x, start_pos.y - next_wp.y)
                
                # If the robot is within 0.5 meters of the waypoint, pop it!
                if dist_to_wp < 0.5: 
                    self.last_path.waypoints.pop(0)
                else:
                    break # Stop checking once we find the active waypoint
            
            #self.visualizer.draw(self.raw_obstacles, self.inflated_obstacles, 
            #                     self.static_nodes, self.static_edges, state, goal, self.last_path)
            return self.last_path
        
        # 1. Direct line of sight shortcut
        if self._is_visible(start_pos, goal):
            final_path = Path([goal])
            self._update_cache(final_path, goal, state)
            return final_path

        # 2. Find which static nodes are visible from Start and Goal
        start_visible, goal_visible = [], []
        for i, node in enumerate(self.static_nodes):
            if self._is_visible(start_pos, node): start_visible.append(i)
            if self._is_visible(goal, node): goal_visible.append(i)

        # Start Fallback
        if not start_visible and self.static_nodes:
            # Sort indices by distance to start_pos FIRST
            sorted_start_indices = sorted(range(len(self.static_nodes)), 
                                          key=lambda i: np.hypot(start_pos.x - self.static_nodes[i].x, 
                                                                 start_pos.y - self.static_nodes[i].y))
            for idx in sorted_start_indices:
                if self._is_raw_visible(start_pos, self.static_nodes[idx]):
                    start_visible.append(idx)
                    break # Stop doing heavy math once we find the closest valid node!

        # Goal Fallback
        if not goal_visible and self.static_nodes:
            # Sort indices by distance to goal FIRST
            sorted_goal_indices = sorted(range(len(self.static_nodes)), 
                                         key=lambda i: np.hypot(goal.x - self.static_nodes[i].x, 
                                                                goal.y - self.static_nodes[i].y))
            for idx in sorted_goal_indices:
                if self._is_raw_visible(goal, self.static_nodes[idx]):
                    goal_visible.append(idx)
                    break # Short-circuit!

        # 3. Run A* on the augmented graph
        path_indices = self._run_astar(start_visible, goal_visible, start_pos, goal)
        
        if not path_indices:
            print("[VisGraph] WARNING: No Global Path Found!")
            failed_path = Path([start_pos])
            # Force the visualizer to draw so you can see the problem!
            self._update_cache(failed_path, goal, state)
            return failed_path

        # 4. Construct final path
        full_path = []
        for idx in path_indices:
            full_path.append(self.static_nodes[idx])
        full_path.append(goal)

        final_path = Path(full_path)
        self._update_cache(final_path, goal, state)
        return final_path

    def _update_cache(self, path, goal, state):
        self.last_path = path
        self.last_goal = goal
        #self.visualizer.draw(self.raw_obstacles, self.inflated_obstacles, 
        #                     self.static_nodes, self.static_edges, state, goal, path)

    # --- Helper Methods for Initialization ---

    def _prepare_obstacles(self, raw_obstacles):
        inflated = []
        inf = self.config.inflation
        for cx, cy, w, h in raw_obstacles:
            iw, ih = w + 2 * inf, h + 2 * inf
            corners = [
                Position(cx - iw/2, cy + ih/2), # Top-Left
                Position(cx + iw/2, cy + ih/2), # Top-Right
                Position(cx + iw/2, cy - ih/2), # Bottom-Right
                Position(cx - iw/2, cy - ih/2)  # Bottom-Left
            ]
            inflated.append(corners)
        return inflated

    def _extract_all_corners(self):
        nodes = []
        for obs in self.inflated_obstacles:
            nodes.extend(obs)
        return nodes

    def _build_static_visibility_graph(self):
        graph = {i: [] for i in range(len(self.static_nodes))}
        for i in range(len(self.static_nodes)):
            for j in range(i + 1, len(self.static_nodes)):
                if self._is_visible(self.static_nodes[i], self.static_nodes[j]):
                    graph[i].append(j)
                    graph[j].append(i)
        return graph

    # --- Geometry Helpers ---

    def _is_visible(self, p1: Position, p2: Position) -> bool:
        mid_x, mid_y = (p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0
        
        for i, (cx, cy, w, h) in enumerate(self.raw_obstacles):
            iw, ih = w + 2 * self.config.inflation, h + 2 * self.config.inflation
            
            # 1. Prevent diagonals: check if midpoint is strictly inside an obstacle
            # We deflate by 0.01 to avoid floating point issues on edges
            if (cx - iw/2 + 0.01) < mid_x < (cx + iw/2 - 0.01) and \
               (cy - ih/2 + 0.01) < mid_y < (cy + ih/2 - 0.01):
                return False

            # 2. Prevent edge crossing: check segment vs 4 edges of the inflated obstacle
            corners = self.inflated_obstacles[i]
            for j in range(4):
                v1, v2 = corners[j], corners[(j + 1) % 4]
                if self._intersect(p1, p2, v1, v2):
                    return False
        return True
    
    def _is_raw_visible(self, p1: Position, p2: Position) -> bool:
        mid_x, mid_y = (p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0
        
        for cx, cy, w, h in self.raw_obstacles:
            # 1. Prevent diagonals through the raw obstacle
            if (cx - w/2 + 0.01) < mid_x < (cx + w/2 - 0.01) and \
               (cy - h/2 + 0.01) < mid_y < (cy + h/2 - 0.01):
                return False

            # 2. Prevent edge crossing against the RAW obstacle corners
            raw_corners = [
                Position(cx - w/2, cy + h/2), # Top-Left
                Position(cx + w/2, cy + h/2), # Top-Right
                Position(cx + w/2, cy - h/2), # Bottom-Right
                Position(cx - w/2, cy - h/2)  # Bottom-Left
            ]
            for j in range(4):
                v1, v2 = raw_corners[j], raw_corners[(j + 1) % 4]
                if self._intersect(p1, p2, v1, v2):
                    return False
        return True

    def _intersect(self, a, b, c, d):
        def ccw(A, B, C):
            return (C.y - A.y) * (B.x - A.x) > (B.y - A.y) * (C.x - A.x)
        
        # If segments share an endpoint, they don't improperly intersect
        if a == c or a == d or b == c or b == d:
            return False
            
        return ccw(a,c,d) != ccw(b,c,d) and ccw(a,b,c) != ccw(a,b,d)

    # --- A* Search ---

    def _run_astar(self, start_neighbors, goal_neighbors, start_pos, goal_pos):
        q = []
        for n in start_neighbors:
            g = np.hypot(start_pos.x - self.static_nodes[n].x, start_pos.y - self.static_nodes[n].y)
            h = np.hypot(goal_pos.x - self.static_nodes[n].x, goal_pos.y - self.static_nodes[n].y)
            heapq.heappush(q, (g + h, g, n, [n]))
            
        visited = set()
        while q:
            f, g, curr, path = heapq.heappop(q)
            if curr in visited: continue
            visited.add(curr)
            
            if curr in goal_neighbors:
                return path
                
            for nxt in self.static_edges[curr]:
                if nxt not in visited:
                    edge_cost = np.hypot(self.static_nodes[curr].x - self.static_nodes[nxt].x, 
                                         self.static_nodes[curr].y - self.static_nodes[nxt].y)
                    new_g = g + edge_cost
                    h = np.hypot(goal_pos.x - self.static_nodes[nxt].x, goal_pos.y - self.static_nodes[nxt].y)
                    heapq.heappush(q, (new_g + h, new_g, nxt, path + [nxt]))
        return None

# --- Custom Global Visualizer ---
class GlobalVisVisualizer:
    def __init__(self, width=800, height=400):
        self.window_name = "High-Level Visibility Graph"
        self.W, self.H = width, height
        self.min_x, self.max_x = -36, 36
        self.min_y, self.max_y = -12, 12
        self.scale_x = self.W / (self.max_x - self.min_x)
        self.scale_y = self.H / (self.max_y - self.min_y)

    def to_screen(self, x, y):
        sx = int((x - self.min_x) * self.scale_x)
        sy = int((self.max_y - y) * self.scale_y)
        return sx, sy

    def draw(self, raw_obs, inflated_obs, nodes, edges, state, goal, path):
        img = np.ones((self.H, self.W, 3), dtype=np.uint8) * 255

        # 1. Draw Inflated Obstacles (Light Gray)
        for obs in inflated_obs:
            pts = np.array([self.to_screen(p.x, p.y) for p in obs], np.int32)
            cv2.fillPoly(img, [pts], (220, 220, 220))
            cv2.polylines(img, [pts], True, (180, 180, 180), 1)

        # 2. Draw Raw Obstacles (Dark Gray)
        for cx, cy, w, h in raw_obs:
            pts = np.array([
                self.to_screen(cx-w/2, cy+h/2), self.to_screen(cx+w/2, cy+h/2),
                self.to_screen(cx+w/2, cy-h/2), self.to_screen(cx-w/2, cy-h/2)
            ], np.int32)
            cv2.fillPoly(img, [pts], (100, 100, 100))

        # 3. Draw Graph Edges (Faint Blue lines)
        for i, neighbors in edges.items():
            p1 = self.to_screen(nodes[i].x, nodes[i].y)
            for j in neighbors:
                if i < j: # Only draw each edge once
                    p2 = self.to_screen(nodes[j].x, nodes[j].y)
                    cv2.line(img, p1, p2, (255, 230, 200), 1)

        # 4. Draw Path (Thick Purple)
        if path and len(path.waypoints) > 1:
            pts = np.array([self.to_screen(p.x, p.y) for p in path.waypoints], np.int32)
            cv2.polylines(img, [pts], False, (128, 0, 128), 3)

        # 5. Draw Robot and Goal
        rx, ry = self.to_screen(state.x, state.y)
        gx, gy = self.to_screen(goal.x, goal.y)
        cv2.circle(img, (gx, gy), 6, (0, 200, 0), -1) # Green Goal
        cv2.circle(img, (rx, ry), 6, (0, 0, 255), -1) # Red Robot

        cv2.imshow(self.window_name, img)
        cv2.waitKey(1)