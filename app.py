# app.py
from flask import Flask, render_template, redirect, request, session, url_for, flash, jsonify, Response
from voice import speak
import sqlite3
import os
import json
import time
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "blind_assistant_super_secret_key"

SETTINGS_FILE = "settings.json"ss

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "dark_mode": False,
        "voice_speed": 150,
        "voice_volume": 100,
        "detection_sensitivity": 70,
        "speech_gap": 3
    }

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        pass

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            flash("Please log in to access this page.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_settings():
    return dict(settings=load_settings())

@app.route("/", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user["password"], password):
            session["username"] = user["username"]
            session.permanent = True
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "danger")
            
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if "username" in session:
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
            
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")
            
        hashed_password = generate_password_hash(password)
        
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")
        finally:
            conn.close()
            
    return render_template("register.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/camera")
@login_required
def camera():
    return render_template("camera.html", settings_data=load_settings())

# ----------------- MJPEG CAMERA PIPELINE -----------------
from camera import VideoCamera
camera_instance = None

def get_camera():
    global camera_instance
    if camera_instance is None:
        camera_instance = VideoCamera()
    return camera_instance

def gen(camera):
    last_settings_time = 0
    settings = None
    conf = 0.4
    
    while True:
        current_time = time.time()
        # Reload settings every 2 seconds to avoid disk I/O per frame
        if current_time - last_settings_time > 2.0:
            settings = load_settings()
            conf = float(settings.get("detection_sensitivity", 40)) / 100.0 
            last_settings_time = current_time
            
        frame, _ = camera.get_frame(conf_threshold=conf)
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        else:
            time.sleep(0.05)

@app.route('/video_feed')
@login_required
def video_feed():
    return Response(gen(get_camera()), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/detections')
@login_required
def api_detections():
    if camera_instance is None:
        return jsonify({"detections": []})
    return jsonify({"detections": camera_instance.current_detections})
# ---------------------------------------------------------

@app.route("/voice")
@login_required
def voice():
    speak("Voice Assistant initialized.")
    return render_template("voice_assistant.html")

@app.route("/sos", methods=["GET", "POST"])
@login_required
def sos():
    conn = get_db()
    cursor = conn.cursor()
    gps_coordinates = "13.0827 N, 80.2707 E"
    
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            name = request.form.get("name")
            phone = request.form.get("phone")
            cursor.execute("INSERT INTO emergency_contacts (name, phone) VALUES (?, ?)", (name, phone))
            conn.commit()
        elif action == "delete":
            contact_id = request.form.get("id")
            cursor.execute("DELETE FROM emergency_contacts WHERE id = ?", (contact_id,))
            conn.commit()
                
    cursor.execute("SELECT * FROM emergency_contacts")
    contacts = cursor.fetchall()
    
    simulated_alerts = []
    for contact in contacts:
        alert_msg = f"EMERGENCY: Visually impaired user requires immediate assistance! Last known location: {gps_coordinates}."
        simulated_alerts.append({
            "name": contact["name"],
            "phone": contact["phone"],
            "message": alert_msg,
            "status": "SMS Dispatched",
            "time": time.strftime("%H:%M:%S")
        })
        cursor.execute("INSERT INTO history (object_name, confidence) VALUES (?, ?)", (f"SOS: Dispatched SMS to {contact['name']}", 1.0))
        
    conn.commit()
    conn.close()
    
    speak("SOS distress alert triggered.")
    return render_template("sos.html", contacts=contacts, gps_coordinates=gps_coordinates, alerts=simulated_alerts)

@app.route("/history", methods=["GET", "POST"])
@login_required
def history():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == "POST":
        cursor.execute("DELETE FROM history")
        conn.commit()
        
    cursor.execute("SELECT * FROM history ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()
    return render_template("history.html", logs=logs)

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    settings_data = load_settings()
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == "POST":
        form_type = request.form.get("form_type")
        
        if form_type == "preferences":
            settings_data.update({
                "dark_mode": request.form.get("dark_mode") == "on",
                "voice_speed": int(request.form.get("voice_speed", 150)),
                "voice_volume": int(request.form.get("voice_volume", 100)),
                "detection_sensitivity": int(request.form.get("detection_sensitivity", 70)),
                "speech_gap": int(request.form.get("speech_gap", 3))
            })
            save_settings(settings_data)
            
        elif form_type == "account":
            new_username = request.form.get("username", "").strip()
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            
            cursor.execute("SELECT * FROM users WHERE username = ?", (session["username"],))
            user = cursor.fetchone()
            
            if user and check_password_hash(user["password"], current_password):
                if new_password:
                    cursor.execute("UPDATE users SET username = ?, password = ? WHERE id = ?", (new_username, generate_password_hash(new_password), user["id"]))
                else:
                    cursor.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, user["id"]))
                conn.commit()
                session["username"] = new_username
                
    cursor.execute("SELECT * FROM users WHERE username = ?", (session["username"],))
    user_info = cursor.fetchone()
    conn.close()
    
    return render_template("settings.html", settings_data=settings_data, user_info=user_info)

@app.route("/gps")
@login_required
def gps():
    speak("GPS Navigation started.")
    return render_template("gps.html")

@app.route("/website")
def website():
    return render_template("website.html")

@app.route("/logout")git status
git add .
git commit -m "Updated project"
git push origin main
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    if not os.path.exists("database.db"):
        import init_db
        init_db.init()
    app.run(debug=True)