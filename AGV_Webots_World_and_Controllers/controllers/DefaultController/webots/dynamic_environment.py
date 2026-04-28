# webots/DynamicEnvironment.py
import numpy as np

from config import WorldConfig

class DynamicObstacle:
    """Helper class to manage a single moving entity."""
    def __init__(self, node, amplitude, speed, axis):
        self.node = node
        self.amplitude = amplitude
        self.speed = speed
        self.axis = axis.lower()
        
        # Because we are halving the wave size to keep it above 0, 
        # we have to double the frequency to maintain the correct top speed.
        self.calculated_frequency = (2.0 * self.speed) / self.amplitude
        
        if self.node:
            self.position_field = self.node.getField("translation")
            self.initial_position = self.position_field.getSFVec3f()
            
    def update(self, t):
        if not self.node:
            return
            
        offset = (self.amplitude / 2.0) * (1.0 - np.cos(self.calculated_frequency * t))
        
        if self.axis == 'x':
            self.position_field.setSFVec3f([
                self.initial_position[0] + offset,
                self.initial_position[1],
                self.initial_position[2]  # Z is locked to the original spawn height!
            ])
        elif self.axis == 'y':
            self.position_field.setSFVec3f([
                self.initial_position[0],
                self.initial_position[1] + offset,
                self.initial_position[2]  # Z is locked to the original spawn height!
            ])
            
        # Stops Webots from calculating wheel friction and joint forces while we are moving it.
        self.node.resetPhysics()

class DynamicEnvironment:
    """Master class that reads the config and holds all moving warehouse entities."""
    def __init__(self, robot):
        self.config = WorldConfig()
        self.robot = robot
        self.obstacles = []
        
        for config in self.config.dynamic_obstacles:
            node = self.robot.getFromDef(config["def_name"])
            if node:
                self.obstacles.append(
                    DynamicObstacle(
                        node=node, 
                        amplitude=config["amplitude"], 
                        speed=config["speed"], 
                        axis=config["axis"]
                    )
                )
            else:
                print(f"WARNING: {config['def_name']} not found in the world!")

    def update_all(self, current_time):
        """Moves all dynamic objects. Call this once per timestep."""
        for obstacle in self.obstacles:
            obstacle.update(current_time)