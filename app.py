from flask import Flask, render_template, redirect, request, session, url_for, flash, jsonify
from voice import speak
import subprocess
import sqlite3
import os
import json
import time
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "blind_assistant_super_secret_key"

SETTINGS_FILE = "settings.json"

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
        "detection_sensitivity": 70
    }

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            flash("Please log in to access this page.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# Context processor to inject theme setting globally
@app.context_processor
def inject_settings():
    return dict(settings=load_settings())

# Login Page
@app.route("/", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            flash("Please fill in all fields.", "danger")
            return render_template("login.html")
            
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user["password"], password):
            session["username"] = user["username"]
            session.permanent = True
            flash("Successfully logged in!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "danger")
            
    return render_template("login.html")

# Register Page
@app.route("/register", methods=["GET", "POST"])
def register():
    if "username" in session:
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not username or not password or not confirm_password:
            flash("Please fill in all fields.", "danger")
            return render_template("register.html")
            
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")
            
        hashed_password = generate_password_hash(password)
        
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")
        finally:
            conn.close()
            
    return render_template("register.html")

# Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

# Start Camera
@app.route("/camera")
@login_required
def camera():
    try:
        # Start detection loop process
        subprocess.Popen(["python", "camera.py"])
        speak("Camera Started. Open CV window active.")
        return render_template("camera.html", status="Active")
    except Exception as e:
        flash(f"Failed to start camera process: {e}", "danger")
        return redirect(url_for("dashboard"))

# Voice Assistant
@app.route("/voice")
@login_required
def voice():
    speak("Welcome to Object Detection For Blind. Voice Assistant active.")
    return render_template("voice_assistant.html")

# SOS Emergency
@app.route("/sos", methods=["GET", "POST"])
@login_required
def sos():
    conn = get_db()
    cursor = conn.cursor()
    
    # Simple simulated GPS coordinates (Chennai, India Context: 13.0827, 80.2707)
    gps_coordinates = "13.0827 N, 80.2707 E"
    
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            name = request.form.get("name")
            phone = request.form.get("phone")
            if name and phone:
                cursor.execute("INSERT INTO emergency_contacts (name, phone) VALUES (?, ?)", (name, phone))
                conn.commit()
                flash("Emergency caretaker contact registered successfully.", "success")
        elif action == "delete":
            contact_id = request.form.get("id")
            if contact_id:
                cursor.execute("DELETE FROM emergency_contacts WHERE id = ?", (contact_id,))
                conn.commit()
                flash("Emergency contact removed.", "success")
                
    cursor.execute("SELECT * FROM emergency_contacts")
    contacts = cursor.fetchall()
    
    # Simulate broadcasting SMS to each caretaker contact
    simulated_alerts = []
    for contact in contacts:
        alert_msg = f"EMERGENCY: Visually impaired user requires immediate assistance! Last known location: {gps_coordinates}."
        simulated_alerts.append({
            "name": contact["name"],
            "phone": contact["phone"],
            "message": alert_msg,
            "status": "SMS Dispatched Successfully",
            "time": time.strftime("%H:%M:%S")
        })
        # Log distress trigger in logs database history
        cursor.execute("INSERT INTO history (object_name, confidence) VALUES (?, ?)", (f"SOS: Dispatched SMS to {contact['name']}", 1.0))
        
    conn.commit()
    conn.close()
    
    speak("Emergency Alert Activated. Broadcasting location coordinates to caretakers.")
    return render_template("sos.html", contacts=contacts, gps_coordinates=gps_coordinates, alerts=simulated_alerts)

# Detection History
@app.route("/history", methods=["GET", "POST"])
@login_required
def history():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == "POST":
        cursor.execute("DELETE FROM history")
        conn.commit()
        flash("History log cleared successfully.", "success")
        
    cursor.execute("SELECT * FROM history ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()
    return render_template("history.html", logs=logs)

# Settings & Account Alteration
@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    settings_data = load_settings()
    
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == "POST":
        form_type = request.form.get("form_type")
        
        # 1. Device and system preferences
        if form_type == "preferences":
            dark_mode = request.form.get("dark_mode") == "on"
            voice_speed = request.form.get("voice_speed", 150)
            voice_volume = request.form.get("voice_volume", 100)
            detection_sensitivity = request.form.get("detection_sensitivity", 70)
            speech_gap = request.form.get("speech_gap", 3)
            
            settings_data = {
                "dark_mode": dark_mode,
                "voice_speed": int(voice_speed),
                "voice_volume": int(voice_volume),
                "detection_sensitivity": int(detection_sensitivity),
                "speech_gap": int(speech_gap)
            }
            save_settings(settings_data)
            flash("System preferences updated.", "success")
            
        # 2. Account Profile Alteration (username / password change)
        elif form_type == "account":
            new_username = request.form.get("username", "").strip()
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            
            # Fetch user details
            cursor.execute("SELECT * FROM users WHERE username = ?", (session["username"],))
            user = cursor.fetchone()
            
            if user and check_password_hash(user["password"], current_password):
                if new_password:
                    hashed_pass = generate_password_hash(new_password)
                    cursor.execute("UPDATE users SET username = ?, password = ? WHERE id = ?", (new_username, hashed_pass, user["id"]))
                else:
                    cursor.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, user["id"]))
                
                conn.commit()
                session["username"] = new_username
                flash("Account details updated successfully.", "success")
            else:
                flash("Invalid current password. Cannot update account.", "danger")
                
    cursor.execute("SELECT * FROM users WHERE username = ?", (session["username"],))
    user_info = cursor.fetchone()
    conn.close()
    
    return render_template("settings.html", settings_data=settings_data, user_info=user_info)

# GPS Navigation
@app.route("/gps")
@login_required
def gps():
    speak("GPS Navigation Started. Loading mapping modules.")
    return render_template("gps.html")

# Project Website
@app.route("/website")
def website():
    return render_template("website.html")

# Logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("Successfully logged out.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    # Setup initial database if not exists
    if not os.path.exists("database.db"):
        import init_db
        init_db.init()
    app.run(debug=True)
