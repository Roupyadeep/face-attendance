import os
import sqlite3
import cv2
import numpy as np
import threading
import time
import datetime
import shutil
from flask import Flask, request, jsonify, Response, render_template
from flask_cors import CORS

try:
    from ultralytics import YOLO
except ImportError:
    pass

app = Flask(__name__, 
            template_folder='attendance_system/templates', 
            static_folder='attendance_system/static')
CORS(app)

DB_FILE = "localstoredb.sqlite"
ATTENDANCE_DB = "attendance.sqlite"
DATASET_DIR = "dataset"
MODEL_FILE = "lbph_model.yml"

REGISTERING_USER = None
ATTENDANCE_COOLDOWN = {}
model_yolo = None
recognizer = None
face_cascade = None
camera = None

def init_db():
    for db in [DB_FILE, ATTENDANCE_DB]:
        conn = sqlite3.connect(db)
        c = conn.cursor()
        if db == DB_FILE:
            c.execute('CREATE TABLE IF NOT EXISTS Users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, department TEXT NOT NULL, class_roll_no TEXT UNIQUE NOT NULL, photos_stored INTEGER)')
        else:
            c.execute('CREATE TABLE IF NOT EXISTS AttendanceLogs (id INTEGER PRIMARY KEY AUTOINCREMENT, class_roll_no TEXT NOT NULL, timestamp TEXT NOT NULL)')
        conn.commit()
        conn.close()

init_db()

def setup_cv():
    global model_yolo, recognizer, face_cascade, camera
    try: model_yolo = YOLO('yolov8n.pt')
    except: pass
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    if os.path.exists(MODEL_FILE): 
        try: recognizer.read(MODEL_FILE)
        except: pass
    if camera is None: 
        camera = cv2.VideoCapture(0)
        time.sleep(1)

def generate_frames():
    global REGISTERING_USER, camera
    if camera is None: camera = cv2.VideoCapture(0)
    while True:
        success, frame = camera.read()
        if not success:
            time.sleep(0.1)
            continue
        if REGISTERING_USER and not REGISTERING_USER["done"]:
            if time.time() - REGISTERING_USER.get("last_capture", 0) > 0.15:
                REGISTERING_USER["frames"].append(frame.copy())
                REGISTERING_USER["count"] += 1
                REGISTERING_USER["last_capture"] = time.time()
                if REGISTERING_USER["count"] >= 30: REGISTERING_USER["done"] = True
            cv2.putText(frame, f"Capturing: {REGISTERING_USER['count']}/30", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
        else:
            if model_yolo is not None and recognizer is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                for (fx, fy, fw, fh) in faces:
                    face_roi = gray[fy:fy+fh, fx:fx+fw]
                    try:
                        label_id, conf = recognizer.predict(face_roi)
                        if conf < 95:
                            conn = sqlite3.connect(DB_FILE)
                            res = conn.execute('SELECT name, department, class_roll_no FROM Users WHERE id=?', (label_id,)).fetchone()
                            conn.close()
                            if res:
                                name, dept, roll = res
                                cv2.rectangle(frame, (fx, fy), (fx+fw, fy+fh), (0, 255, 0), 2)
                                y_offset = fy - 15
                                cv2.putText(frame, f"Status: Present", (fx, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                                y_offset -= 20
                                cv2.putText(frame, f"Dept: {dept}", (fx, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
                                y_offset -= 20
                                cv2.putText(frame, f"Roll: {roll}", (fx, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
                                y_offset -= 20
                                cv2.putText(frame, f"Name: {name}", (fx, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
                                log_attendance(roll)
                        else:
                            cv2.rectangle(frame, (fx, fy), (fx+fw, fy+fh), (0, 0, 255), 2)
                            cv2.putText(frame, "Unknown", (fx, fy-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    except Exception: pass
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

def log_attendance(roll):
    now = datetime.datetime.now()
    if not ATTENDANCE_COOLDOWN.get(roll) or (now - ATTENDANCE_COOLDOWN[roll]).total_seconds() > 60:
        ATTENDANCE_COOLDOWN[roll] = now
        conn = None
        try:
            conn = sqlite3.connect(ATTENDANCE_DB, timeout=20)
            conn.execute('INSERT INTO AttendanceLogs (class_roll_no, timestamp) VALUES (?, ?)', (roll, now.strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
        finally:
            if conn:
                conn.close()

# Page Routes
@app.route('/')
def index(): return render_template('index.html')
@app.route('/register')
def register(): return render_template('register.html')
@app.route('/attendance')
def attendance(): return render_template('attendance.html')
@app.route('/records')
def records(): return render_template('records.html')

# Video Feeds
@app.route('/video-feed')
@app.route('/attendance-feed')
def video_feed(): return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# API Endpoints
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    name, dept, roll = data.get('name'), data.get('department'), data.get('roll') or data.get('classRollNo')
    try:
        conn = sqlite3.connect(DB_FILE, timeout=20)
        c = conn.cursor()
        c.execute('INSERT INTO Users (name, department, class_roll_no, photos_stored) VALUES (?, ?, ?, 0)', (name, dept, roll))
        uid = c.lastrowid
        conn.commit()
        return jsonify({"user_id": uid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/capture-start', methods=['POST'])
def api_capture_start():
    global REGISTERING_USER
    uid = request.json.get('user_id')
    conn = sqlite3.connect(DB_FILE); res = conn.execute('SELECT class_roll_no FROM Users WHERE id=?', (uid,)).fetchone(); conn.close()
    if res:
        REGISTERING_USER = {"user_id": uid, "roll_no": res[0], "count": 0, "frames": [], "done": False, "last_capture": 0}
        return jsonify({"status": "started"})
    return jsonify({"error": "not found"}), 404

@app.route('/api/capture-status', methods=['GET'])
def api_capture_status():
    global REGISTERING_USER
    if not REGISTERING_USER: return jsonify({"count": 30, "total": 30, "done": True})
    if REGISTERING_USER["done"]:
        u = REGISTERING_USER; p = os.path.join(DATASET_DIR, str(u["roll_no"]))
        if not os.path.exists(p): os.makedirs(p)
        for i, f in enumerate(u["frames"]): cv2.imwrite(os.path.join(p, f"img_{i}.jpg"), f)
        conn = sqlite3.connect(DB_FILE); conn.execute('UPDATE Users SET photos_stored=30 WHERE id=?', (u["user_id"],)); conn.commit(); conn.close()
        REGISTERING_USER = None
        return jsonify({"count": 30, "total": 30, "done": True})
    return jsonify({"count": REGISTERING_USER["count"], "total": 30, "done": False})

@app.route('/api/train', methods=['POST'])
def api_train(): threading.Thread(target=train_lbph).start(); return jsonify({"status": "success"})

@app.route('/api/dashboard-stats', methods=['GET'])
def api_dashboard_stats():
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=20)
        total_users = conn.execute('SELECT COUNT(*) FROM Users').fetchone()[0]
        conn.execute(f"ATTACH DATABASE '{ATTENDANCE_DB}' AS att_db")
        present_today = conn.execute(f"SELECT COUNT(DISTINCT class_roll_no) FROM att_db.AttendanceLogs WHERE timestamp LIKE '{today}%'").fetchone()[0]
        recent = conn.execute(f"SELECT U.name, U.class_roll_no, A.timestamp FROM att_db.AttendanceLogs A JOIN Users U ON A.class_roll_no = U.class_roll_no WHERE A.timestamp LIKE '{today}%' ORDER BY A.id DESC LIMIT 10").fetchall()
        
        absent_today = total_users - present_today
        attendance_pct = round((present_today / total_users * 100), 1) if total_users > 0 else 0
        recent_activity = [{"name": r[0], "roll": r[1], "timestamp": r[2], "status": "Present"} for r in recent]
        return jsonify({"total_users": total_users, "present_today": present_today, "absent_today": absent_today, "attendance_pct": attendance_pct, "recent_activity": recent_activity})
    except Exception as e:
        print(f"Dashboard stats error: {e}")
        return jsonify({"error": "Stats error"}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/users', methods=['GET'])
def api_get_users():
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=20)
        users = conn.execute('SELECT id, name, class_roll_no, department FROM Users').fetchall()
        return jsonify([{"id": r[0], "name": r[1], "roll": r[2], "department": r[3]} for r in users])
    finally:
        if conn: conn.close()

@app.route('/api/users/delete/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    conn = None
    conn_att = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=20)
        user = conn.execute('SELECT class_roll_no FROM Users WHERE id=?', (user_id,)).fetchone()
        if user:
            roll = user[0]
            conn.execute('DELETE FROM Users WHERE id=?', (user_id,))
            conn.commit()
            
            conn_att = sqlite3.connect(ATTENDANCE_DB, timeout=20)
            conn_att.execute('DELETE FROM AttendanceLogs WHERE class_roll_no=?', (roll,))
            conn_att.commit()
            
            path = os.path.join(DATASET_DIR, str(roll))
            if os.path.exists(path):
                shutil.rmtree(path)
            
            threading.Thread(target=train_lbph).start()
            return jsonify({"status": "success"})
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        print(f"Delete error: {e}")
        return jsonify({"error": "Delete error"}), 500
    finally:
        if conn: conn.close()
        if conn_att: conn_att.close()

@app.route('/api/records', methods=['GET'])
def api_records():
    date_filter = request.args.get('date') or datetime.datetime.now().strftime('%Y-%m-%d')
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=20)
        conn.execute(f"ATTACH DATABASE '{ATTENDANCE_DB}' AS att_db")
        rows = conn.execute(f'''
            SELECT U.name, U.class_roll_no, U.department, A.timestamp, U.id
            FROM att_db.AttendanceLogs A JOIN Users U ON A.class_roll_no = U.class_roll_no
            WHERE A.timestamp LIKE '{date_filter}%'
            ORDER BY A.id DESC
        ''').fetchall()
        return jsonify([{
            "name": r[0], "roll": r[1], "department": r[2], 
            "date": r[3].split(' ')[0], "timestamp": r[3], "status": "Present", "id": r[4]
        } for r in rows])
    except Exception as e:
        print(f"Records error: {e}")
        return jsonify([])
    finally:
        if conn: conn.close()

@app.route('/api/start-attendance', methods=['POST'])
@app.route('/api/stop-attendance', methods=['POST'])
def api_dummy(): return jsonify({"status": "success"})

def train_lbph():
    global recognizer
    setup_cv()
    conn = sqlite3.connect(DB_FILE); users = conn.execute('SELECT id, class_roll_no FROM Users').fetchall(); conn.close()
    faces, labels = [], []
    for uid, roll in users:
        p = os.path.join(DATASET_DIR, str(roll))
        if os.path.exists(p):
            for f in os.listdir(p):
                img = cv2.imread(os.path.join(p, f))
                if img is not None:
                    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); d = face_cascade.detectMultiScale(g, 1.1, 4)
                    for (x,y,w,h) in d: faces.append(g[y:y+h, x:x+w]); labels.append(uid)
    if faces: 
        recognizer.train(faces, np.array(labels))
        recognizer.write(MODEL_FILE)
    elif os.path.exists(MODEL_FILE): os.remove(MODEL_FILE)

if __name__ == '__main__':
    threading.Thread(target=setup_cv).start(); app.run(port=5000, threaded=True)
