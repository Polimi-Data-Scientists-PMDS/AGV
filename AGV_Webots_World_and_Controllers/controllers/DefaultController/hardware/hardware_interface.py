from abc import ABC, abstractmethod
from config import PhysicalConfig

class HardwareInterface(ABC):
    def __init__(self):
        self.config = PhysicalConfig()

        self.motors = None
        self.gps = None
        self.lidar = None
        self.camera = None
    
    @abstractmethod
    def is_alive(self):
        pass

    @abstractmethod
    def get_time(self):
        pass
