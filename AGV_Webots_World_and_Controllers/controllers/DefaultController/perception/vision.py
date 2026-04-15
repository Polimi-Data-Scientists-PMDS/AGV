# perception/vision.py
import cv2
import numpy as np
from ultralytics import YOLO

class ObjectDetector:
    def __init__(self):
        print("Loading YOLOv8 AI Model (this might take a few seconds)...")
        # 'yolov8n.pt' is the "Nano" version. It is incredibly fast and lightweight.
        # Ultralytics will automatically download the file the first time you run this.
        self.model = YOLO('yolov8n.pt') 
        print("AI Model Loaded!")
        
        self.last_process_time = 0.0

    def process_and_display(self, image_array, current_time):
        """Runs AI inference and displays the camera feed."""
        if image_array is None:
            return None

        # PERFORMANCE THROTTLE:
        # We don't want to run heavy AI every 1ms (your simulation timestep).
        # This restricts the AI to run at 10 FPS (every 0.1 seconds), keeping Webots smooth.
        if current_time - self.last_process_time < 0.1:
            cv2.waitKey(1) # Keep the OpenCV window from freezing
            return None
            
        self.last_process_time = current_time

        # 1. Run YOLO Inference
        # conf=0.5 means it only highlights objects it is 50%+ confident about.
        # verbose=False stops it from spamming your terminal with detection logs.
        results = self.model(image_array, conf=0.5, verbose=False)

        # 2. Draw the bounding boxes automatically
        annotated_frame = results[0].plot()

        # 3. Display the live video feed
        cv2.imshow("AGV AI Camera", annotated_frame)
        cv2.waitKey(1) 
        
        # Return the raw detection data in case the robot needs to react to it later!
        return results[0].boxes