import numpy as np

from localization.localization import RobotState, Position


def calculate_control_errors(state:RobotState, goal:Position):
    if goal is None:
        return 0.0, 0.0
        
    dx = goal.x - state.x
    dy = goal.y - state.y
    rho = np.sqrt(np.square(dx) + np.square(dy))    
    
    alpha = np.arctan2(dy, dx) - state.theta         
    alpha = (alpha + np.pi) % (2 * np.pi) - np.pi   
    
    return rho, alpha