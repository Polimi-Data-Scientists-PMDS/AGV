import numpy as np

class Camera:
    """Handles camera image extraction and formatting for OpenCV/AI."""
    def __init__(self, robot, timestep):
        self.camera = robot.getDevice("camera")
        if self.camera:
            self.camera.enable(timestep)
            print("Camera set up correctly!")

    def get_image(self):
        if not self.camera:
            return None
            
        raw_image = self.camera.getImage()
        if not raw_image:
            return None
            
        width = self.camera.getWidth()
        height = self.camera.getHeight()
        
        # Convert Webots raw bytes (BGRA) into a fast numpy array (BGR for OpenCV)
        img = np.frombuffer(raw_image, np.uint8).reshape((height, width, 4))
        return img[:, :, :3]  # Drop the Alpha channel
