class GPS:
    """Provides absolute world coordinates and the recorded startup position."""
    def __init__(self, robot, timestep):
        self.gps = robot.getDevice('gps')
        self.gps.enable(timestep)
        self.initial_position = None

    def calibrate_origin(self):
        """Record the absolute spawn position after the first simulation step."""
        x, y, _ = self.gps.getValues()
        self.initial_position = (x, y)
        print("GPS set up and calibrated correctly!")

    def get_initial_position(self):
        if self.initial_position is None:
            raise RuntimeError("GPS startup position has not been calibrated")
        return self.initial_position

    def get_position(self):
        x, y, _ = self.gps.getValues()
        return x, y
