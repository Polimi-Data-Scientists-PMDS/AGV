from hardware.hardware_interface import HardwareInterface
from perception.vision import ObjectDetector
from config import VisionConfig

class SensorData:
    def __init__(self, time):
        self.time = time
        self.dt = None
        self.wheels_delta = (None, None)    # (dL, dR)
        self.gps = (None, None)             # (x, y)
        self.pointcloud = None
        self.image = None
        self.detections = None


class Perception:
    def __init__(self, hardware: HardwareInterface):
        self.vision_config = VisionConfig()
        self.hardware = hardware
        self.__last_time = None

        self.object_detection = None
        if self.vision_config.enable_object_detection:
            self.object_detection = ObjectDetector()

    def perceive(self) -> SensorData:
        current_time = self.hardware.get_time()
        data = SensorData(current_time)

        data.dt =  self.__get_dt(current_time)
        data.wheels_delta = self.hardware.motors.get_deltas()
        data.gps = self.hardware.gps.get_position()
        data.pointcloud = self.hardware.lidar.read_scan()
        data.image = self.hardware.camera.get_image()

        if self.object_detection:
            data.detections = self.object_detection.detect(data.image, data.time)

        return data

    def __get_dt(self, current_time):
        dt = 0
        if self.__last_time is not None:
            dt = current_time - self.__last_time
        self.__last_time = current_time
        return dt
