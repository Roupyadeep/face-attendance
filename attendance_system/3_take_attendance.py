import cv2
import numpy as np
import sqlite3
import os
import datetime

DB_FILE = "attendance.db"

def init_attendance_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            roll TEXT,
            department TEXT,
            status TEXT,
            timestamp TEXT,
            date TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_attendance_db()

def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('SELECT name, roll, department FROM users WHERE id = ?', (user_id,))
        return c.fetchone()
    except:
        return None
    finally:
        conn.close()

def mark_attendance(user_id, name, roll, department):
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.datetime.now().strftime('%H:%M:%S')

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if already present today
    c.execute('SELECT id FROM attendance WHERE roll = ? AND date = ?', (roll, current_date))
    if not c.fetchone():
        c.execute('''
            INSERT INTO attendance (user_id, name, roll, department, status, timestamp, date) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, name, roll, department, "Present", current_time, current_date))
        conn.commit()
    conn.close()

def mark_absentees():
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        c.execute('SELECT id, name, roll, department FROM users')
        all_users = c.fetchall()
        
        for user in all_users:
            u_id, name, roll, dept = user
            c.execute('SELECT id FROM attendance WHERE roll = ? AND date = ?', (roll, current_date))
            if not c.fetchone():
                c.execute('''
                    INSERT INTO attendance (user_id, name, roll, department, status, timestamp, date) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (u_id, name, roll, dept, "Absent", "00:00:00", current_date))
        conn.commit()
    except Exception as e:
        print("Could not mark absentees:", e)
    finally:
        conn.close()

def take_attendance():
    if not os.path.exists('trainer/trainer.yml'):
        print("Model not found. Please train the model first.")
        return

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read('trainer/trainer.yml')

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    cam = cv2.VideoCapture(0)
    # Using 50 for strict high confidence as requested. Note: LBPH lower = better.
    CONFIDENCE_THRESHOLD = 50 

    print("Scanner Active. Press 'q' to quit.")

    while True:
        ret, frame = cam.read()
        if not ret:
            print("Failed to access camera.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.2, 5)

        for (x, y, w, h) in faces:
            user_id, confidence = recognizer.predict(gray[y:y+h, x:x+w])
            
            # LBPH confidence: 0 is perfect match.
            if confidence < CONFIDENCE_THRESHOLD:
                user = get_user_by_id(user_id)
                if user:
                    name, roll, dept = user
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # Overlay Details
                    cv2.putText(frame, f"Name: {name}", (x, y - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(frame, f"Roll: {roll}", (x, y - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(frame, f"Dept: {dept}", (x, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(frame, f"Status: PRESENT V", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(frame, f"Conf: {round(100 - confidence)}%", (x+w-100, y+h+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                    mark_attendance(user_id, name, roll, dept)
            else:
                # UNKNOWN
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(frame, "UNKNOWN", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                cv2.putText(frame, f"Conf: {round(100 - confidence)}%", (x+w-100, y+h+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        cv2.imshow('Live Face Scanner', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()
    
    # Auto mark absentees
    print("Session ended. Auto-marking absentees...")
    mark_absentees()
    print("Done. All logs recorded for the day.")

if __name__ == "__main__":
    take_attendance()
