# perception/vision.py
import os
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

import cv2
import numpy as np
from dataclasses import dataclass
from ultralytics import YOLO
import torch

from config import LOGS_DIR, VisionConfig


@dataclass
class Detection:
    """Simple detection record consumed by planning (YoloLabeler)."""
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    class_name: str
    confidence: float


class ObjectDetector:
    def __init__(self):
        self.config = VisionConfig()

        print("Loading YOLOv8 AI Model (this might take a few seconds)...")
        # 'yolov8n.pt' is the "Nano" version. It is incredibly fast and lightweight.
        # Ultralytics will automatically download the file the first time you run this.
        self.model = YOLO(self.config.yolo_model) 
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

    def detect(self, image, current_time):
        """Runs AI inference and displays the camera feed."""
        if image is None:
            return None

        # PERFORMANCE THROTTLE:
        # We don't want to run heavy AI every 1ms (your simulation timestep).
        # This restricts the AI to run at 10 FPS (every 0.1 seconds), keeping Webots smooth.
        if current_time - self.last_process_time < 0.1:
            return None
            
        self.last_process_time = current_time

        # 1. Run YOLO Inference
        # 0 = person, 7 = truck
        results = self.model(image, 
                             conf=self.config.yolo_thresh, 
                             verbose=False, 
                             device=self.device,
                             classes=[0, 7])

        #rename the "truck" category to "forklift"
        for r in results:
            r.names[7] = "forklift"

        # 2. Draw the bounding boxes automatically
        annotated_frame = results[0].plot()

        # 3. Save the live video feed to disk
        # Save the frame to disk so the Streamlit dashboard can access it
        os.makedirs(LOGS_DIR, exist_ok=True)
        cv2.imwrite(os.path.join(LOGS_DIR, "camera_feed.jpg"), annotated_frame)
        
        # Convert ultralytics Boxes into simple Detection records so downstream
        # code (YoloLabeler) doesn't depend on the ultralytics API.
        detections = []
        names = results[0].names
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append(Detection(
                xmin=x1, ymin=y1, xmax=x2, ymax=y2,
                class_name=names[int(box.cls[0])],
                confidence=float(box.conf[0]),
            ))
        return detections
