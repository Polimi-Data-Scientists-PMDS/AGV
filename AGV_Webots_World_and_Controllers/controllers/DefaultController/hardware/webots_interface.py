# hardware/webots_interface.py
from controller import Supervisor # type: ignore

from hardware.motors import Motors
from hardware.lidar import Lidar
from hardware.gps import GPS
from hardware.camera import Camera
    

class WebotsInterface:
    def __init__(self, config):
        self.config = config
        self.robot = Supervisor()
        self.timestep = int(self.robot.getBasicTimeStep())
        
        # initialize components
        self.motors = Motors(self.robot, self.timestep, self.config)
        self.lidar = Lidar(self.robot, self.timestep)
        self.gps = GPS(self.robot, self.timestep)
        self.camera = Camera(self.robot, self.timestep)
        
        # init step
        self.robot.step(self.timestep)

        # calibrate gps
        self.gps.calibrate_origin()

    def is_alive(self) -> bool:
        return self.robot.step(self.timestep) != -1

    def get_time(self) -> float:
        return self.robot.getTime()