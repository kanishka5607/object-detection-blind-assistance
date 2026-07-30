# camera.py
import cv2
import sqlite3
import time
import numpy as np
import torch
import threading
from voice import enqueue_speech

class VideoCamera:
    def __init__(self):
        print("Debug: Initializing VideoCamera...")
        self.error_msg = None
        self.frame_count = 0
        
        try:
            print("Debug: Attempting cv2.VideoCapture(0, cv2.CAP_DSHOW)")
            self.video = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            
            if not self.video.isOpened():
                print("Debug: CAP_DSHOW failed, falling back to cv2.VideoCapture(0)")
                self.video = cv2.VideoCapture(0)
                
            if not self.video.isOpened():
                self.error_msg = "WEBCAM UNAVAILABLE (IN USE BY ANOTHER APP?)"
                print(f"ERROR: {self.error_msg}")
            else:
                self.video.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
                self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                self.video.set(cv2.CAP_PROP_FPS, 15)
                self.video.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                print("Camera opened successfully")
                
        except Exception as e:
            self.error_msg = f"CAMERA INIT ERROR: {str(e)}"
            print(self.error_msg)
            
        # YOLO Loading
        self.model = None
        try:
            from ultralytics import YOLO
            model_path = "yolov8n.pt"
            self.model = YOLO(model_path)
            self.model.fuse()
            print(f"YOLO model {model_path} loaded successfully")
        except Exception as e:
            self.error_msg = "YOLO LOAD ERROR. CHECK TERMINAL."
            print(f"ERROR: Failed to load YOLO. Reason: {e}")
            import traceback
            traceback.print_exc()
            
        self.last_db_log_time = 0
        self.current_detections = []
        
    def __del__(self):
        if hasattr(self, 'video') and self.video:
            self.video.release()
            
    def _get_error_frame(self, message):
        """ Generates a red visual error frame to stream to the browser """
        img = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(img, "SERVER ERROR:", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.putText(img, message, (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        ret, jpeg = cv2.imencode('.jpg', img)
        return jpeg.tobytes(), []

    def _log_to_db(self, detections):
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            for d in detections:
                cursor.execute("INSERT INTO history (object_name, confidence) VALUES (?, ?)", (d['label'], d['confidence']))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def get_frame(self, conf_threshold=0.40):
        # If there's an initialization error, stream the error frame
        if self.error_msg:
            return self._get_error_frame(self.error_msg)
            
        if not self.video.isOpened():
            return self._get_error_frame("CAMERA NOT OPENED")
            
        success, image = self.video.read()
        if not success or image is None:
            return self._get_error_frame("FRAME CAPTURE FAILED (CAMERA LOCKED?)")
            
        self.frame_count += 1
        
        if self.frame_count % 3 == 0 and self.model:
            try:
                with torch.no_grad():
                    # We use conf_threshold from the settings (defaults to 0.40 or 0.50 based on user slider)
                    results = self.model(image, imgsz=320, conf=conf_threshold, device="cpu", verbose=False)
                
                boxes = results[0].boxes
                detections = []
                
                for box in boxes:
                    class_id = int(box.cls[0])
                    label = self.model.names[class_id]
                    conf = float(box.conf[0])
                    
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    box_height = max(1.0, float(y2 - y1))
                    approx_distance = max(0.5, round(280.0 / box_height, 1))
                    
                    detections.append({
                        "label": label, 
                        "confidence": conf, 
                        "distance": approx_distance,
                        "box": [x1, y1, x2, y2]
                    })
                    
                    enqueue_speech(label)
                    
                self.current_detections = detections
                
            except Exception as e:
                print(f"YOLO Inference Error: {e}")
                
        for d in self.current_detections:
            x1, y1, x2, y2 = d["box"]
            label = d["label"]
            conf = d["confidence"]
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 206, 201), 2)
            cv2.putText(image, f"{label} {int(conf*100)}%", (x1, max(10, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 206, 201), 2)
        
        current_time = time.time()
        if self.current_detections and (current_time - self.last_db_log_time) > 3.0:
            threading.Thread(target=self._log_to_db, args=(self.current_detections,), daemon=True).start()
            self.last_db_log_time = current_time
        
        ret, jpeg = cv2.imencode('.jpg', image)
        if not ret:
            return self._get_error_frame("JPEG ENCODE ERROR")
            
        return jpeg.tobytes(), self.current_detections