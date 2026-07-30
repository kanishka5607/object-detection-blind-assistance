import cv2
import pyttsx3
import os

print("=== Testing Camera ===")

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("CAP_DSHOW failed, trying normal...")
    cap = cv2.VideoCapture(0)

if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        print(f"Frame captured. Size: {frame.shape}")
    else:
        print("Camera opened, but frame could not be read.")
    cap.release()
else:
    print("Could not open camera.")

print("\n=== Testing pyttsx3 ===")

try:
    engine = pyttsx3.init()
    engine.say("Voice test successful")
    engine.runAndWait()
    print("pyttsx3 initialized successfully.")
except Exception as e:
    print("pyttsx3 Error:", e)

print("\n=== Testing YOLO ===")

try:
    from ultralytics import YOLO

    if os.path.exists("yolov8s.pt"):
        model_path = "yolov8s.pt"
    elif os.path.exists("yolov8n.pt"):
        model_path = "yolov8n.pt"
    else:
        raise FileNotFoundError("No YOLO model file found.")

    print(f"Loading model: {model_path}")
    model = YOLO(model_path)
    print("YOLO loaded successfully.")

except Exception as e:
    print("YOLO Error:", e)

print("\n=== Test Completed ===")