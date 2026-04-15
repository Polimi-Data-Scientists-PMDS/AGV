class GPS:
    """Handles GPS coordinate tracking and origin normalization."""
    def __init__(self, robot, timestep):
        self.gps = robot.getDevice('gps')
        self.gps.enable(timestep)
        self.initial_state = None

    def calibrate_origin(self):
        """Must be called AFTER the first simulation step to lock in starting coordinates."""
        self.initial_state = self.gps.getValues()
        print("GPS set up and calibrated correctly!")

    def get_position(self):
        x, y, _ = self.gps.getValues()
        if self.initial_state:
            x -= self.initial_state[0]
            y -= self.initial_state[1]
        return x, y