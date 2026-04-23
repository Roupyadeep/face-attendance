from flask import Flask, render_template, Response, request, jsonify
from flask_cors import CORS
import database
import face_utils
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Ensure required directories exist
for folder in ['dataset', 'trainer']:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Initialize Database
database.init_db()

# --- Page Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/attendance')
def attendance():
    return render_template('attendance.html')

@app.route('/records')
def records():
    return render_template('records.html')

# --- API Endpoints ---

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    name = data.get('name')
    roll = data.get('roll')
    dept = data.get('department')
    
    if not all([name, roll, dept]):
        return jsonify({"error": "Missing fields"}), 400
        
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (name, roll, department) VALUES (?, ?, ?)', (name, roll, dept))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"user_id": user_id, "message": "User registered successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/capture-start', methods=['POST'])
def api_capture_start():
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({"error": "User ID required"}), 400
    
    face_utils.capture_faces(user_id)
    return jsonify({"message": "Capture started"})

@app.route('/api/capture-status')
def api_capture_status():
    return jsonify({
        "count": face_utils.capture_count,
        "total": 30,
        "is_capturing": face_utils.is_capturing
    })

@app.route('/api/train', methods=['POST'])
def api_train():
    success = face_utils.train_model()
    if success:
        return jsonify({"message": "Model trained successfully"})
    else:
        return jsonify({"error": "No images found to train or training failed"}), 400

@app.route('/api/start-attendance', methods=['POST'])
def api_start_attendance():
    face_utils.is_attendance_running = True
    return jsonify({"message": "Attendance started"})

@app.route('/api/stop-attendance', methods=['POST'])
def api_stop_attendance():
    face_utils.is_attendance_running = False
    
    # Mark absent users for today
    today = datetime.now().strftime('%Y-%m-%d')
    conn = database.get_db_connection()
    # Find users who are NOT in attendance for today
    absent_users = conn.execute('''
        SELECT id, name, roll, department FROM users 
        WHERE id NOT IN (SELECT user_id FROM attendance WHERE date = ?)
    ''', (today,)).fetchall()
    
    for user in absent_users:
        conn.execute('''
            INSERT INTO attendance (user_id, name, roll, department, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (user['id'], user['name'], user['roll'], user['department'], 'Absent'))
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Attendance stopped and absentees marked"})

@app.route('/api/records')
def api_records():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    conn = database.get_db_connection()
    records = conn.execute('SELECT * FROM attendance WHERE date = ? ORDER BY timestamp DESC', (date,)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in records])

@app.route('/api/users')
def api_users():
    conn = database.get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return jsonify([dict(row) for row in users])

@app.route('/api/users/delete/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    try:
        conn = database.get_db_connection()
        # Delete attendance records
        conn.execute('DELETE FROM attendance WHERE user_id = ?', (user_id,))
        # Delete user
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        # Delete dataset images
        import glob
        files = glob.glob(f"dataset/User_{user_id}_*.jpg")
        for f in files:
            if os.path.exists(f):
                os.remove(f)
                
        return jsonify({"message": "User and associated data deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = database.get_db_connection()
    
    total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    present_today = conn.execute('SELECT COUNT(*) FROM attendance WHERE date = ? AND status = "Present"', (today,)).fetchone()[0]
    absent_today = conn.execute('SELECT COUNT(*) FROM attendance WHERE date = ? AND status = "Absent"', (today,)).fetchone()[0]
    
    attendance_pct = 0
    if total_users > 0:
        attendance_pct = round((present_today / total_users) * 100, 2)
        
    recent_activity = conn.execute('SELECT * FROM attendance ORDER BY timestamp DESC LIMIT 10').fetchall()
    
    conn.close()
    
    return jsonify({
        "total_users": total_users,
        "present_today": present_today,
        "absent_today": absent_today,
        "attendance_pct": attendance_pct,
        "recent_activity": [dict(row) for row in recent_activity]
    })

# --- Video Feed Streams ---

@app.route('/video-feed')
def video_feed():
    return Response(face_utils.gen_capture_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/attendance-feed')
def attendance_feed():
    return Response(face_utils.gen_attendance_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
