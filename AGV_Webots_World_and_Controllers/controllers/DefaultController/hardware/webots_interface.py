# hardware/webots_interface.py
from controller import Robot # type: ignore

from hardware.hardware_interface import HardwareInterface
from hardware.motors import Motors
from hardware.lidar import Lidar
from hardware.gps import GPS
from hardware.inertial_unit import InertialUnit
from hardware.camera import Camera
    
class WebotsInterface(HardwareInterface):
    def __init__(self):
        super().__init__()
        self.robot = Robot()
        self.timestep = int(self.robot.getBasicTimeStep())
        
        # initialize components
        self.motors = Motors(self.robot, self.timestep)
        self.lidar = Lidar(self.robot, self.timestep)
        self.gps = GPS(self.robot, self.timestep)
        self.inertial_unit = InertialUnit(self.robot, self.timestep)
        self.camera = Camera(self.robot, self.timestep)
        
        # init step
        self.robot.step(self.timestep)

        # calibrate gps
        self.gps.calibrate_origin()

    def is_alive(self) -> bool:
        return self.robot.step(self.timestep) != -1

    def get_time(self) -> float:
        return self.robot.getTime()

    def get_robot_name(self) -> str:
        return self.robot.getName()
