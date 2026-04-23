# navigation/obstacle_avoidance.py
import numpy as np

class LidarObstacleAvoider:
    def __init__(self, config, logger, lidar_specs):
        self.config = config
        self.logger = logger
        self.fov = lidar_specs[0]

        # State tracking from your original code
        self.used_obstacle_ids = set()
        self.used_space_ids = set()
        self.previous_scan = None
        self.locked_obstacle = None
        self.locked_space = None
        self.is_escaping_dead_end = False

    def obstacle_avoidance(self, pointcloud, current_state, goal, current_time):
        # CALCULATE CONTROL ERRORS
        dist_e, heading_e = current_state.calculate_errors(goal)
        dist_e = min(self.config.CONTROL_VISION_DISTANCE, dist_e) # Cap distance

        # --- 0. COLLISION DETECTION ---
        if pointcloud and min(x[1] for x in pointcloud) < self.config.COLLISION_DISTANCE:
            print(f"COLLISION DETECTED")
            self.logger.log_unexpected_behavior(current_time, "Collision detected, stopping.")
            return 0.0, 0.0

        # --- 1. SETUP ---
        self.sector_width = self.fov / self.config.NUM_SECTORS

        # --- 2. MAP LIDAR ---
        unnamed_sectors = self.__calculate_sectors(pointcloud, dist_e)
        
        if not 'obs' in unnamed_sectors:
            self.used_obstacle_ids.clear()
            self.used_space_ids.clear()
            self.previous_scan = None
            self.locked_obstacle = None
            self.locked_space = None
            return dist_e, heading_e

        # --- 3. ASSIGN IDS TO THE SECTORS ---
        sectors = self.__assign_ids(unnamed_sectors)
        self.previous_scan = sectors.copy()


        # --- 4. CHOOSE DIRECTION ---
        # UNLOCK CHECK
        lock_valid = self.locked_obstacle is not None and self.locked_space is not None
        no_more_obstacle_lock = self.locked_obstacle not in sectors
        no_more_free_lock = self.locked_space not in sectors
        if lock_valid and (no_more_obstacle_lock or no_more_free_lock): # if either of the two locked objects are missing
            self.locked_obstacle = None
            self.locked_space = None

        # ESCAPING DEAD END
        if self.is_escaping_dead_end:
            if self.config.PRINT_OBSTACLE_AVOIDANCE:
                self.__visualize_map(sectors)
            
            # divide the sectors in two sides -> if the free spot is in the correct side then unlock
            half = self.config.NUM_SECTORS//2
            split_sectors = [sectors[:half], sectors[half:]]
            free_space_id = next((x for x in split_sectors[self.escaping_side] if x < 0), None)
            if free_space_id is not None: 
                self.locked_space = free_space_id
                self.is_escaping_dead_end = False
            else:
                return 0, self.escape_sign*2

        # CALCULATE FINAL DIRECTION
        ideal_direction_idx, actual_direction_idx = self.__choose_direction(sectors, heading_e)

    
        # DEAD END
        if actual_direction_idx is None: 
            print("NO PATH FOUND - SWITCH TO ESCAPE MODE")
            if self.config.PRINT_OBSTACLE_AVOIDANCE:
                self.__visualize_map(sectors, ideal_direction_idx, actual_direction_idx)

            self.is_escaping_dead_end = True
            self.escaping_side = 0 if ideal_direction_idx < self.config.NUM_SECTORS//2 else 1
            self.escape_sign = 1 if self.escaping_side == 0 else -1
            self.locked_obstacle = sectors[0]
            print(f"ESCAPING: {self.escaping_side} ")
            return  0, self.escape_sign*2 
        
        # CANNOT FOLLOW IDEAL DIRECTION
        elif ideal_direction_idx != actual_direction_idx: 
            # IF IDEAL DIRECTION IS FREE -> FOLLOW THAT AND RELEASE LOCK
            if sectors[ideal_direction_idx] < 0: # used for moving obstacles
                self.locked_obstacle = None
                self.locked_space = None
                actual_direction_idx = ideal_direction_idx
            else:
                # LOCK ON THAT OBJECT
                self.locked_obstacle = sectors[ideal_direction_idx]
                self.locked_space = sectors[actual_direction_idx]
            
        # UNLOCK
        else:
            self.locked_obstacle = None
            self.locked_space = None

        # VISUALIZATIONS
        if self.config.PRINT_OBSTACLE_AVOIDANCE:
            self.__visualize_map(sectors, ideal_direction_idx, actual_direction_idx)


        # --- 5. EXECUTION ---
        actual_direction_angle = self.__calculate_sector_angle(actual_direction_idx)
        final_steering_angle = heading_e if ideal_direction_idx == actual_direction_idx else actual_direction_angle
        speed_factor = max(0.2, np.cos(final_steering_angle))

        return dist_e * speed_factor, final_steering_angle
    

    def __get_new_obstacle_id(self):
        for i in range(1, self.config.NUM_SECTORS):
            if i not in self.used_obstacle_ids:
                self.used_obstacle_ids.add(i)
                return i
        return None

    def __get_new_space_id(self):
        for i in range(-1, -self.config.NUM_SECTORS, -1):
            if i not in self.used_space_ids:
                self.used_space_ids.add(i)
                return i
        return None
    
    def __calculate_sectors(self, pointcloud, dist_e):
        unnamed_sectors = ['free'] * self.config.NUM_SECTORS
        for angle, dist in pointcloud:
            if dist < self.config.SAFE_DISTANCE and (dist_e >= self.config.SAFE_DISTANCE or dist < dist_e):
                sector_id = int((angle + self.fov/2) / self.sector_width) % self.config.NUM_SECTORS
                if 0 <= sector_id < self.config.NUM_SECTORS:
                    unnamed_sectors[sector_id] = 'obs'
                    for p in range(1, self.config.PADDING + 1):
                        if sector_id - p >= 0:
                            unnamed_sectors[sector_id - p] = 'obs'
                        if sector_id + p < self.config.NUM_SECTORS:
                            unnamed_sectors[sector_id + p] = 'obs'
        return unnamed_sectors
    
    def __assign_ids(self, unnamed_sectors):
        sectors = unnamed_sectors.copy()
        if self.previous_scan is None:
            # no prev scan -> assign new ids to all
            prev_id = None
            prev_was_obstacle = None
            for i, s in enumerate(unnamed_sectors):
                if s == 'obs': 
                    if not prev_was_obstacle or i == 0:
                        prev_id = self.__get_new_obstacle_id()
                    sectors[i] = prev_id
                    prev_was_obstacle = True
                else: 
                    if prev_was_obstacle or i == 0:
                        prev_id = self.__get_new_space_id()
                    sectors[i] = prev_id
                    prev_was_obstacle = False
        else:
            # 1 assign ids to this sector of the same position
            for i in range(self.config.NUM_SECTORS):
                is_old_obstacle = self.previous_scan[i] > 0
                is_new_obstacle = unnamed_sectors[i] == 'obs'
                if is_old_obstacle and is_new_obstacle:
                    sectors[i] = self.previous_scan[i]
                elif not is_old_obstacle and not is_new_obstacle:
                    sectors[i] = self.previous_scan[i]
            
            # 2 forward id propagation
            prev_id = None
            is_prev_obstacle = None
            for i in range(self.config.NUM_SECTORS):
                has_id = sectors[i] not in ['free', 'obs']
                if has_id:
                    prev_id = sectors[i]
                    is_prev_obstacle = unnamed_sectors[i] == 'obs'
                else:
                    if unnamed_sectors[i] == 'obs' and is_prev_obstacle:
                        sectors[i] = prev_id
                    elif unnamed_sectors[i] == 'free' and is_prev_obstacle is False:
                        sectors[i] = prev_id
            
            # 3 backward id propagation
            next_id = None
            is_next_obstacle = None
            for i in range(self.config.NUM_SECTORS-1, -1, -1):
                has_id = sectors[i] not in ['free', 'obs']
                if has_id:
                    next_id = sectors[i]
                    is_next_obstacle = unnamed_sectors[i] == 'obs'
                else:
                    if unnamed_sectors[i] == 'obs' and is_next_obstacle:
                        sectors[i] = next_id
                    elif unnamed_sectors[i] == 'free' and is_next_obstacle is False:
                        sectors[i] = next_id
            
            # 4 new id assignment (to isles)
            prev_id = None
            prev_was_obstacle = None
            for i in range(self.config.NUM_SECTORS):
                has_id = sectors[i] not in ['free', 'obs']
                is_obstacle = unnamed_sectors[i] == 'obs'
                if not has_id:
                    if is_obstacle:
                        if not prev_was_obstacle or i == 0:
                            sectors[i] = self.__get_new_obstacle_id()
                            prev_id = sectors[i]
                        else:
                            sectors[i] = prev_id
                    else:
                        if prev_was_obstacle or i == 0:
                            sectors[i] = self.__get_new_space_id()
                            prev_id = sectors[i]
                        else:
                            sectors[i] = prev_id
                prev_was_obstacle = is_obstacle
            
            # 5 propagation of similar ids and types
            prec_type = None
            prec_id = None
            for i in range(self.config.NUM_SECTORS):
                curr_type = unnamed_sectors[i]
                if (curr_type == prec_type):
                    sectors[i] = prec_id
                else:
                    prec_id = sectors[i]
                prec_type = unnamed_sectors[i]

            # 6 final check of similarity to the unnamed one
            for i in range(self.config.NUM_SECTORS):
                obstacle_ok = unnamed_sectors[i] == 'obs' and sectors[i] > 0
                free_ok = unnamed_sectors[i] == 'free' and sectors[i] < 0
                if not (obstacle_ok or free_ok):
                    raise Exception(f"OBSTACLE AVOIDANCE: ID assignments failed on {i}: {unnamed_sectors} {sectors}")

        if 0 in sectors or None in sectors:
            raise Exception("OBSTACLE AVOIDANCE: Missing a sector assignment!")
        
        # CLEAN IDS BUFFER
        self.used_obstacle_ids.clear()
        self.used_space_ids.clear()
        for s in sectors:
            if s > 0:
                self.used_obstacle_ids.add(s)
            else:
                self.used_space_ids.add(s)
        
        return sectors
    
    def __calculate_sector_angle(self, i):
        return self.fov/2 - (i + 0.5) * self.sector_width 
    
    def __choose_direction(self, sectors, heading_e):
        ideal_direction_idx = None
        actual_direction_idx = None
        min_ideal_error = float('inf')
        min_actual_error = float('inf')

        for i in range(self.config.NUM_SECTORS):
            sector_angle = self.__calculate_sector_angle(i)
            error = abs(np.arctan2(np.sin(sector_angle - heading_e), np.cos(sector_angle - heading_e)))
            
            # find best ideal sector
            if error < min_ideal_error: 
                min_ideal_error = error
                ideal_direction_idx = i

            # find best actual sector
            lock_ok = self.locked_space is None or self.locked_space == sectors[i]
            if sectors[i] < 0 and lock_ok: 
                if error < min_actual_error:
                    min_actual_error = error
                    actual_direction_idx = i

        return ideal_direction_idx, actual_direction_idx

    def __visualize_map(self, sectors, ideal_sector_index = None, actual_sector_index = None):
        final_string = ""

        visual_map = ""
        for i, s in enumerate(sectors):
            char = '.' if s < 0 else str(s)
            ideal_ok = ideal_sector_index is not None
            actual_ok = actual_sector_index is not None
            if ideal_ok and i == ideal_sector_index: char = 'X'
            if actual_ok and i == actual_sector_index: char = 'O'
            if ideal_ok and actual_ok and i == ideal_sector_index and i == actual_sector_index: char = '*'
            visual_map += char + " "
        final_string += f"COMPLETE RADAR: [{visual_map}]"

        if actual_sector_index:
            steering_angle = self.__calculate_sector_angle(actual_sector_index)
            final_string += f" | Steering: {steering_angle:.2f}"

        final_string += f" | LOCKED ON: {self.locked_space} & {self.locked_obstacle}"

        print(final_string)