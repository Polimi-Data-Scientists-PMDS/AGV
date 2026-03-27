from RobotControllers.RobotController_v1 import RobotController_v1


class MovingWalls:
    def __init__(self, timestep, controller_robot):
        self.TIME_STEP = timestep
        self.wall = controller_robot.getFromDef("MOVING_WALL")
        self.position = self.wall.getField("translation")

    def move_wall(self, t):
        y = 3 * __import__("math").sin(t)
        self.position.setSFVec3f([-7, y, 0.0])