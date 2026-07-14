import sqlite3
import os
from werkzeug.security import generate_password_hash

def init():
    db_path = "database.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)
    
    # Create history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_name TEXT,
        confidence REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create emergency contacts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emergency_contacts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT
    )
    """)
    
    # Insert default admin user if not exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed_password = generate_password_hash("admin123")
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", hashed_password))
        print("Default user 'admin' with password 'admin123' created.")
        
    # Insert dummy contacts
    cursor.execute("SELECT COUNT(*) FROM emergency_contacts")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO emergency_contacts (name, phone) VALUES (?, ?)", ("Primary Caretaker", "+1-555-0199"))
        cursor.execute("INSERT INTO emergency_contacts (name, phone) VALUES (?, ?)", ("Secondary Contact", "+1-555-0144"))
        
    # Insert some dummy history
    cursor.execute("SELECT COUNT(*) FROM history")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO history (object_name, confidence) VALUES (?, ?)", ("person", 0.94))
        cursor.execute("INSERT INTO history (object_name, confidence) VALUES (?, ?)", ("chair", 0.81))
        cursor.execute("INSERT INTO history (object_name, confidence) VALUES (?, ?)", ("bottle", 0.76))

    conn.commit()
    conn.close()
    print("Database Created and Seeded Successfully!")

if __name__ == "__main__":
    init()
