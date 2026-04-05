# webots/MovingWalls.py
import numpy as np

class MovingWalls:
    def __init__(self, timestep, controller_robot, name):
        self.TIME_STEP = timestep
        self.wall = controller_robot.getFromDef("MOVING_WALL" + name)
        if self.wall:
            self.position = self.wall.getField("translation")
            self.initial_position = self.position.getSFVec3f()
        else:
            print(f"WARNING: MOVING_WALL{name} not found in world!")
    
    def move_wall(self, t, amplitude, frequency, axis):
        if not self.wall:
            return
            
        current = self.position.getSFVec3f()
        offset = amplitude * np.sin(frequency * t)

        if axis == 'x':
            self.position.setSFVec3f([
                self.initial_position[0] + offset,
                current[1],
                current[2],
            ])
        else:
            self.position.setSFVec3f([
                current[0],
                self.initial_position[1] + offset,
                current[2],
            ])