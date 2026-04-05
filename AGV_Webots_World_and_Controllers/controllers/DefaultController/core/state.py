# core/state.py
from dataclasses import dataclass
import numpy as np

@dataclass
class Position:
    x: float
    y: float

@dataclass
class State:
    x: float
    y: float
    theta: float

    def calculate_errors(self, goal: Position):
        """ Compute distance and heading errors to a goal position."""
        if goal is None:
            return 0.0, 0.0
            
        dx = goal.x - self.x
        dy = goal.y - self.y
        rho = np.sqrt(np.square(dx) + np.square(dy))    
        
        alpha = np.arctan2(dy, dx) - self.theta         
        alpha = (alpha + np.pi) % (2 * np.pi) - np.pi   
        
        return rho, alpha
    
    def update_with_odometry(self, dS, dTheta):
        self.x += dS * np.cos(self.theta)
        self.y += dS * np.sin(self.theta)
        self.theta += dTheta
        self.theta = (self.theta + np.pi) % (2 * np.pi) - np.pi
    
    def fuse_with_gps(self, x, y, gps_weight=1.0):
        self.x = (x * gps_weight) + (self.x * (1 - gps_weight))
        self.y = (y * gps_weight) + (self.y * (1 - gps_weight))