from ultralytics import YOLO
import cv2
import pyttsx3
import threading
import time

print("Loading YOLO Model...")

model = YOLO("yolov8s.pt")

print("Model Loaded")
print("Starting Camera Feed...")

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Cannot open camera")
    exit()

last_spoken = {}
speech_gap = 3  # seconds


def speak(text):
    engine = pyttsx3.init()
    engine.setProperty("rate", 150)
    engine.say(text)
    engine.runAndWait()
    engine.stop()


while True:

    ret, frame = cap.read()

    if not ret:
        break

    results = model(frame, conf=0.7)

    annotated_frame = results[0].plot()

    current_time = time.time()

    boxes = results[0].boxes

    for box in boxes:

        class_id = int(box.cls[0])
        object_name = model.names[class_id]

        confidence = float(box.conf[0])

        print(f"{object_name}: {confidence:.2f}")

        if (
            object_name not in last_spoken
            or current_time - last_spoken[object_name] > speech_gap
        ):

            text = f"{object_name} detected"

            print("Speaking:", text)

            threading.Thread(
                target=speak,
                args=(text,),
                daemon=True
            ).start()

            last_spoken[object_name] = current_time

    cv2.imshow("Object Detection For Blind", annotated_frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()