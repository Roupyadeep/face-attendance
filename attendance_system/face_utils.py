import cv2
import os
import numpy as np
from PIL import Image
import threading
import time
from datetime import datetime
from database import get_db_connection

# Load Haar Cascade (Traditional method)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Global variables for state management
lock = threading.Lock()
capture_count = 0
is_capturing = False
current_user_id = None
is_attendance_running = False

def capture_faces(user_id):
    global capture_count, is_capturing, current_user_id
    current_user_id = user_id
    capture_count = 0
    is_capturing = True

def train_model():
    dataset_path = 'dataset'
    if not os.path.exists(dataset_path):
        os.makedirs(dataset_path)
        
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    image_paths = [os.path.join(dataset_path, f) for f in os.listdir(dataset_path) if f.endswith('.jpg')]
    face_samples = []
    ids = []
    
    for image_path in image_paths:
        PIL_img = Image.open(image_path).convert('L')
        img_numpy = np.array(PIL_img, 'uint8')
        
        filename = os.path.split(image_path)[-1]
        user_id = int(filename.split("_")[1])
        
        face_samples.append(img_numpy)
        ids.append(user_id)
            
    if len(ids) > 0:
        recognizer.train(face_samples, np.array(ids))
        if not os.path.exists('trainer'):
            os.makedirs('trainer')
        recognizer.write('trainer/trainer.yml')
        return True
    return False

def gen_capture_frames():
    global capture_count, is_capturing, current_user_id
    cam = cv2.VideoCapture(0)
    
    while is_capturing and capture_count < 100:
        success, frame = cam.read()
        if not success:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # Save the captured image
            capture_count += 1
            img_path = f"dataset/User_{current_user_id}_{capture_count}.jpg"
            cv2.imwrite(img_path, gray[y:y+h, x:x+w])
            
            cv2.putText(frame, f"Captured: {capture_count}/100", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            time.sleep(0.1) # Add small delay to allow for head movement
            
            if capture_count >= 100:
                is_capturing = False
                break
                
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
    cam.release()
    is_capturing = False

def gen_attendance_frames():
    global is_attendance_running
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    trainer_path = 'trainer/trainer.yml'
    if not os.path.exists(trainer_path):
        return
        
    recognizer.read(trainer_path)
    cam = cv2.VideoCapture(0)
    recognized_today = set()
    
    while is_attendance_running:
        success, frame = cam.read()
        if not success:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.2, 5)
        
        for (x, y, w, h) in faces:
            id, confidence = recognizer.predict(gray[y:y+h, x:x+w])
            
            if confidence < 75: # Increased threshold for better robustness to head movement
                conn = None
                try:
                    conn = get_db_connection()
                    user = conn.execute('SELECT * FROM users WHERE id = ?', (id,)).fetchone()
                    
                    if user:
                        name = user['name']
                        roll = user['roll']
                        dept = user['department']
                        
                        today = datetime.now().strftime('%Y-%m-%d')
                        if id not in recognized_today:
                            existing = conn.execute('SELECT id FROM attendance WHERE user_id = ? AND date = ?', (id, today)).fetchone()
                            if not existing:
                                conn.execute('INSERT INTO attendance (user_id, name, roll, department, status) VALUES (?, ?, ?, ?, ?)',
                                            (id, name, roll, dept, 'Present'))
                                conn.commit()
                            recognized_today.add(id)
                        
                        current_time = datetime.now().strftime('%H:%M:%S')
                        color = (0, 255, 0)
                        label = f"{name} | {roll} | {dept} | {current_time}"
                        status_label = "PRESENT"
                        
                        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                        cv2.putText(frame, label, (x, y-45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                        cv2.putText(frame, status_label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    else:
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                        cv2.putText(frame, "UNKNOWN", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                finally:
                    if conn:
                        conn.close()
            else:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(frame, "UNKNOWN", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
    cam.release()
