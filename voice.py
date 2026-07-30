# voice.py
import pyttsx3
import threading
import queue
import time
import traceback

speech_queue = queue.Queue()
last_spoken = {}
pending_announcements = set()
COOLDOWN = 5.0 # seconds

def tts_worker():
    print("Debug: TTS Worker thread started.")
    
    # CRITICAL FIX FOR WINDOWS THREADING
    try:
        import pythoncom
        pythoncom.CoInitialize() 
    except ImportError:
        pass

    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        print("Debug: pyttsx3 engine initialized successfully.")
    except Exception as e:
        print(f"ERROR: Failed to initialize pyttsx3: {e}")
        traceback.print_exc()
        return

    while True:
        item = speech_queue.get()
        if item is None:
            break
            
        enqueue_time, text, label = item
        
        # Free up the pending lock so it can be re-queued if needed later
        if label and label in pending_announcements:
            pending_announcements.remove(label)
            
        # Discard stale announcements older than 2.5 seconds
        if time.time() - enqueue_time > 2.5:
            print(f"Debug: Discarding stale announcement: {text}")
            speech_queue.task_done()
            continue
            
        # Register that we actually spoke it, starting the cooldown now
        if label:
            # Double check cooldown just in case
            if label in last_spoken and (time.time() - last_spoken[label]) <= COOLDOWN:
                speech_queue.task_done()
                continue
            last_spoken[label] = time.time()
            
        print(f"Speaking: {text}")
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"ERROR during engine.say(): {e}")
            
        speech_queue.task_done()

tts_thread = threading.Thread(target=tts_worker, daemon=True)
tts_thread.start()

def enqueue_speech(label):
    current_time = time.time()
    
    # Do not enqueue if it is already waiting in the queue
    if label in pending_announcements:
        return
        
    # Do not enqueue if we just spoke it recently
    if label not in last_spoken or (current_time - last_spoken[label]) > COOLDOWN:
        pending_announcements.add(label)
        speech_queue.put((current_time, f"{label} detected", label))

def speak(text):
    # System announcements have no label and bypass the duplicate checks
    speech_queue.put((time.time(), text, None))