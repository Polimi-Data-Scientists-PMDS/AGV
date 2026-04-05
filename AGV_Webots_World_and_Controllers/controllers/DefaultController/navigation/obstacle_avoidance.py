# navigation/obstacle_avoidance.py
import numpy as np

class ObstacleAvoider:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        
        # State tracking from your original code
        self.used_obstacle_ids = set()
        self.used_space_ids = set()
        self.previous_scan = None
        self.locked_obstacle = None
        self.locked_space = None
        self.is_escaping = False

    def obstacle_avoidance(self, pointcloud, dist_e, heading_e, current_time, state, goal_position, fov, max_range):
        def get_obstacle_id():
            for i in range(1, NUM_SECTORS):
                if i not in self.used_obstacle_ids:
                    self.used_obstacle_ids.add(i)
                    return i
            return None

        def get_space_id():
            for i in range(-1, -NUM_SECTORS, -1):
                if i not in self.used_space_ids:
                    self.used_space_ids.add(i)
                    return i
            return None
        
        # --- 0. COLLISION DETECTION ---
        if pointcloud and min(x[1] for x in pointcloud) < self.config.COLLISION_DISTANCE:
            print(f"COLLISION DETECTED")
            self.logger.log_unexpected_behavior(current_time, "Collision detected, stopping.")
            return 0.0, 0.0

        # --- 1. SETUP ---
        NUM_SECTORS = 32
        PADDING = 4
        sector_width = fov / NUM_SECTORS
        unnamed_sectors = ['f'] * NUM_SECTORS # f is free, o is obstacle
        obstacle_found = False

        # --- 2. MAP LIDAR ---
        for angle, dist in pointcloud:
            if dist < self.config.SAFE_DISTANCE and (dist_e >= self.config.SAFE_DISTANCE or dist < dist_e):
                sector_id = int((angle + fov/2) / sector_width) % NUM_SECTORS
                if 0 <= sector_id < NUM_SECTORS:
                    unnamed_sectors[sector_id] = 'o'
                    obstacle_found = True
                    for p in range(1, PADDING + 1):
                        if sector_id - p >= 0:
                            unnamed_sectors[sector_id - p] = 'o'
                        if sector_id + p < NUM_SECTORS:
                            unnamed_sectors[sector_id + p] = 'o'
        
        if not obstacle_found:
            self.used_obstacle_ids.clear()
            self.used_space_ids.clear()
            self.previous_scan = None
            self.locked_obstacle = None
            self.locked_space = None
            return dist_e, heading_e

        # --- 3. ASSIGN IDS TO THE SECTORS ---
        sectors = unnamed_sectors.copy()
        if self.previous_scan is None:
            prev_id = None
            prev_was_obstacle = None
            for i, s in enumerate(unnamed_sectors):
                if s == 'o': 
                    if not prev_was_obstacle or i == 0:
                        prev_id = get_obstacle_id()
                    sectors[i] = prev_id
                    prev_was_obstacle = True
                else: 
                    if prev_was_obstacle or i == 0:
                        prev_id = get_space_id()
                    sectors[i] = prev_id
                    prev_was_obstacle = False
        else:
            # 1 assign ids to this sector of the same position
            for i in range(NUM_SECTORS):
                is_old_obstacle = self.previous_scan[i] > 0
                is_new_obstacle = unnamed_sectors[i] == 'o'
                if is_old_obstacle and is_new_obstacle:
                    sectors[i] = self.previous_scan[i]
                elif not is_old_obstacle and not is_new_obstacle:
                    sectors[i] = self.previous_scan[i]
            
            # 2 forward id propagation
            prev_id = None
            is_prev_obstacle = None
            for i in range(NUM_SECTORS):
                has_id = sectors[i] not in ['f', 'o']
                if has_id:
                    prev_id = sectors[i]
                    is_prev_obstacle = unnamed_sectors[i] == 'o'
                else:
                    if unnamed_sectors[i] == 'o' and is_prev_obstacle:
                        sectors[i] = prev_id
                    elif unnamed_sectors[i] == 'f' and is_prev_obstacle is False:
                        sectors[i] = prev_id
            
            # 3 backward id propagation
            next_id = None
            is_next_obstacle = None
            for i in range(NUM_SECTORS-1, -1, -1):
                has_id = sectors[i] not in ['f', 'o']
                if has_id:
                    next_id = sectors[i]
                    is_next_obstacle = unnamed_sectors[i] == 'o'
                else:
                    if unnamed_sectors[i] == 'o' and is_next_obstacle:
                        sectors[i] = next_id
                    elif unnamed_sectors[i] == 'f' and is_next_obstacle is False:
                        sectors[i] = next_id
            
            # 4 new id assignment 
            prev_id = None
            prev_was_obstacle = None
            for i in range(NUM_SECTORS):
                has_id = sectors[i] not in ['f', 'o']
                is_obstacle = unnamed_sectors[i] == 'o'
                if not has_id:
                    if is_obstacle:
                        if not prev_was_obstacle or i == 0:
                            sectors[i] = get_obstacle_id()
                            prev_id = sectors[i]
                        else:
                            sectors[i] = prev_id
                    else:
                        if prev_was_obstacle or i == 0:
                            sectors[i] = get_space_id()
                            prev_id = sectors[i]
                        else:
                            sectors[i] = prev_id
                prev_was_obstacle = is_obstacle
            
            # 5 propagation of similar types
            prec_type = None
            prec_id = None
            for i in range(NUM_SECTORS):
                curr_type = unnamed_sectors[i]
                if (curr_type == prec_type):
                    sectors[i] = prec_id
                else:
                    prec_id = sectors[i]
                prec_type = unnamed_sectors[i]

            # 6 final check
            for i in range(NUM_SECTORS):
                obstacle_ok = unnamed_sectors[i] == 'o' and sectors[i] > 0
                free_ok = unnamed_sectors[i] == 'f' and sectors[i] < 0
                if not (obstacle_ok or free_ok):
                    raise Exception(f"OBSTACLE AVOIDANCE: ID assignments failed on {i}: {unnamed_sectors} {sectors}")

        if 0 in sectors or None in sectors:
            raise Exception("OBSTACLE AVOIDANCE -- Missing a sector assignment!")
            
        self.previous_scan = sectors.copy()

        # CLEAN USED OBSTACLES BUFFER
        self.used_obstacle_ids.clear()
        self.used_space_ids.clear()
        for s in sectors:
            if s > 0:
                self.used_obstacle_ids.add(s)
            else:
                self.used_space_ids.add(s)

        # --- 4. CHOOSE DIRECTION ---
        # We find where we WANT to go before we look at locks or obstacles
        original_sector_index = None
        min_original_error = float('inf')
        for i in range(NUM_SECTORS):
            sector_angle = fov/2 - (i + 0.5) * sector_width 
            error = abs(np.arctan2(np.sin(sector_angle - heading_e), np.cos(sector_angle - heading_e)))
            if error < min_original_error:
                min_original_error = error
                original_sector_index = i

        # This is what stops the "Ghost Locking" on moving obstacles
        if sectors[original_sector_index] < 0:
            self.locked_obstacle = None
            self.locked_space = None

        if self.locked_obstacle not in sectors or self.locked_space not in sectors:
            self.locked_obstacle = None
            self.locked_space = None

        if self.is_escaping:
            visual_map = " ".join(str(s) for s in sectors)
            print(f"COMPLETE RADAR: [{visual_map}] | LOCKED ON: {self.locked_space} & {self.locked_obstacle}")

            free_space_id = next((x for x in sectors if x < 0), None)
            if free_space_id is not None: 
                self.locked_space = free_space_id
                self.is_escaping = False
            else:
                return self.config.CONTROL_VISION_DISTANCE, -2

        original_sector_index = None
        min_original_error = float('inf')
        best_sector_index = None
        best_sector_angle = None
        min_free_error = float('inf')
        
        for i in range(NUM_SECTORS):
            sector_angle = fov/2 - (i + 0.5) * sector_width 
            error = abs(np.arctan2(np.sin(sector_angle - heading_e), np.cos(sector_angle - heading_e)))
            
            if error < min_original_error:
                min_original_error = error
                original_sector_index = i

            lock_ok = self.locked_space is None or self.locked_space == sectors[i]
            if sectors[i] < 0 and lock_ok: 
                if error < min_free_error:
                    min_free_error = error
                    best_sector_index = i
                    best_sector_angle = sector_angle

        if best_sector_index is None: 
            print("NO PATH - ESCAPE")
            self.is_escaping = True
            self.locked_obstacle = sectors[0]
            return self.config.CONTROL_VISION_DISTANCE, -2 
        
        elif original_sector_index != best_sector_index: 
            self.locked_obstacle = sectors[original_sector_index]
            self.locked_space = sectors[best_sector_index]
        else:
            self.locked_obstacle = None
            self.locked_space = None

        visual_map = ""
        for i, s in enumerate(sectors):
            char = '.' if s < 0 else str(s)
            if i == original_sector_index: char = 'X'
            if i == best_sector_index: char = 'O'
            if i == original_sector_index and i == best_sector_index: char = '*'
            visual_map += char + " "

        print(f"COMPLETE RADAR: [{visual_map}] | Steering: {best_sector_angle:.2f} | LOCKED ON: {self.locked_space} & {self.locked_obstacle}")
        print(f"POSITION: {state}")
        print(f"GOAL: {goal_position}")

        # --- 5. EXECUTION ---
        final_steering_angle = heading_e if original_sector_index == best_sector_index else best_sector_angle
        speed_factor = max(0.2, np.cos(final_steering_angle))

        return dist_e * speed_factor, final_steering_angle