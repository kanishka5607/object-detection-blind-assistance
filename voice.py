import pyttsx3
import json
import os

def speak(text):
    # Load settings from a configuration file if it exists
    rate = 150
    volume = 1.0
    config_path = os.path.join(os.path.dirname(__file__), "settings.json")
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                rate = int(config.get("voice_speed", 150))
                volume = float(config.get("voice_volume", 100)) / 100.0
        except Exception:
            pass
            
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", rate)
        engine.setProperty("volume", volume)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"TTS error: {e}")
        pass

if __name__ == "__main__":
    speak("Hello World")
