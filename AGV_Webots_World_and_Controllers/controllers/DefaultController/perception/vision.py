# perception/vision.py
import os
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

import cv2
import numpy as np
from ultralytics import YOLO
import torch



class ObjectDetector:
    def __init__(self, config):
        self.config = config

        print("Loading YOLOv8 AI Model (this might take a few seconds)...")
        # 'yolov8n.pt' is the "Nano" version. It is incredibly fast and lightweight.
        # Ultralytics will automatically download the file the first time you run this.
        self.model = YOLO(self.config.YOLO_MODEL) 
        print("AI Model Loaded!")

        # --- CROSS-PLATFORM HARDWARE ACCELERATION ---
        # 1. Check for NVIDIA GPUs (Windows/Linux)
        if torch.cuda.is_available():
            self.device = 'cuda'
            print("🚀 NVIDIA GPU (CUDA) Activated!")
            
        # 2. Check for Apple Silicon (M1/M2/M3 Macs)
        elif torch.backends.mps.is_available():
            self.device = 'mps'
            print("🚀 Apple Silicon GPU (MPS) Activated!")
            
        # 3. Fallback to normal Processor (Older Macs or basic laptops)
        else:
            self.device = 'cpu'
            print("⚠️ Running on CPU (Standard hardware)")
        
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
        # show only categories of useful detections
        # 0 = person, 7 = truck
        results = self.model(image_array, 
                             conf=self.config.YOLO_THRESH, 
                             verbose=False, 
                             device=self.device,
                             classes=[0, 7])

        #rename the "truck" category to "forklift"
        for r in results:
            r.names[7] = "forklift"

        # 2. Draw the bounding boxes automatically
        annotated_frame = results[0].plot()

        # 3. Display the live video feed
        cv2.imshow("AGV AI Camera", annotated_frame)
        cv2.waitKey(1) 
        
        # Return the raw detection data in case the robot needs to react to it later!
        return results[0].boxes