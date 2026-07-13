import math


class InertialUnit:
    """Provides the robot's absolute world-frame yaw."""

    def __init__(self, robot, timestep):
        self.inertial_unit = robot.getDevice("inertial unit")
        self.inertial_unit.enable(timestep)

    def get_yaw(self):
        yaw = self.inertial_unit.getRollPitchYaw()[2]
        return (yaw + math.pi) % (2.0 * math.pi) - math.pi
