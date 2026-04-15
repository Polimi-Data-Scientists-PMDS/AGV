class Lidar:
    """Handles the LIDAR pointcloud and specifications."""
    def __init__(self, robot, timestep):
        self.lidar = robot.getDevice('Lidar1')
        self.lidar.enable(timestep)
        print("Lidar set up correctly!")

    def get_specs(self):
        return self.lidar.getFov(), self.lidar.getMaxRange()

    def read_scan(self):
        ranges = self.lidar.getRangeImage()
        fov = self.lidar.getFov()
        resolution = self.lidar.getHorizontalResolution()
        angle_step = fov / resolution
        
        points = []
        for i, r in enumerate(ranges):
            angle = -fov/2 + i * angle_step
            points.append((angle, r))
        return points