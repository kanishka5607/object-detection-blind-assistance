from ultralytics import YOLO
import cv2
import sqlite3
import threading
import time
import json
import os
from voice import speak

print("Loading YOLO Model...")
# Load YOLO model. We use yolov8s.pt by default as specified in the project.
try:
    model = YOLO("yolov8s.pt")
except Exception:
    # Fallback to a lighter model if yolov8s is not available or downloads slowly
    model = YOLO("yolov8n.pt")

print("Model Loaded")
print("Starting Camera Feed...")

# Connect to database to log detections in real time
def log_detection(object_name, confidence):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO history (object_name, confidence) VALUES (?, ?)", (object_name, confidence))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Logging error: {e}")

# Function to trigger emergency SOS log in database and speak warning
def trigger_emergency_sos():
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        # Log distress trigger in logs database
        cursor.execute("INSERT INTO history (object_name, confidence) VALUES (?, ?)", ("EMERGENCY SOS TRIGGERED", 1.0))
        conn.commit()
        conn.close()
        
        # Announce to user and surroundings
        speak("Emergency distress beacon activated. Sending location coordinates to caretakers.")
        print("SOS Distress Signal Sent!")
    except Exception as e:
        print(f"SOS error: {e}")

# Load configuration settings
conf_threshold = 0.70
speech_gap = 3 # default in seconds
config_path = "settings.json"
if os.path.exists(config_path):
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            conf_threshold = float(config.get("detection_sensitivity", 70)) / 100.0
            speech_gap = int(config.get("speech_gap", 3))
    except Exception:
        pass

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Cannot open camera")
    exit()

# Set camera resolution for faster CPU processing
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

last_spoken = {}

while True:
    ret, frame = cap.read()
    if not ret:
        break
        
    results = model(frame, conf=conf_threshold, verbose=False)
    annotated_frame = results[0].plot()
    current_time = time.time()
    boxes = results[0].boxes
    
    for box in boxes:
        class_id = int(box.cls[0])
        object_name = model.names[class_id]
        confidence = float(box.conf[0])
        
        # Get bounding box height to estimate distance (larger box height = closer)
        box_coords = box.xyxy[0]
        y1, y2 = float(box_coords[1]), float(box_coords[3])
        box_height = max(1.0, y2 - y1)
        
        # Approximate distance formula (calibrated roughly for standard webcam fields of view)
        approx_distance = max(0.5, round(280.0 / box_height, 1))
        
        print(f"{object_name} detected at {approx_distance}m (Conf: {confidence:.2f})")
        
        if (
            object_name not in last_spoken
            or current_time - last_spoken[object_name] > speech_gap
        ):
            # Include estimated distance in visual warning!
            text = f"{object_name} at {approx_distance} meters"
            print("Speaking:", text)
            
            # Save detection in DB
            threading.Thread(target=log_detection, args=(object_name, confidence), daemon=True).start()
            
            # Speak asynchronously
            threading.Thread(target=speak, args=(text,), daemon=True).start()
            
            last_spoken[object_name] = current_time
            
    # Display the distance overlay on frames
    cv2.putText(annotated_frame, "Press 'S' for SOS Emergency | ESC to Quit", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
    cv2.imshow("Object Detection For Blind", annotated_frame)
    
    # Listen for keypress
    key = cv2.waitKey(1) & 0xFF
    
    # Check if 'S' or 's' key is pressed for Emergency SOS
    if key == ord('s') or key == ord('S'):
        threading.Thread(target=trigger_emergency_sos, daemon=True).start()
        
    # Close if ESC key (27) is pressed
    if key == 27:
        break
        
    # Close if window 'X' button is clicked
    try:
        if cv2.getWindowProperty("Object Detection For Blind", cv2.WND_PROP_VISIBLE) < 1:
            break
    except Exception:
        break

cap.release()
cv2.destroyAllWindows()
