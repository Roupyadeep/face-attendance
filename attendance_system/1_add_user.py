import tkinter as tk
from tkinter import messagebox
import sqlite3
import cv2
import os

DB_FILE = "attendance.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def capture_images(user_id, roll, name):
    cam = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    count = 0
    os.makedirs('dataset', exist_ok=True)

    while True:
        ret, frame = cam.read()
        if not ret:
            messagebox.showerror("Error", "Failed to access webcam")
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            count += 1
            # Save the captured face
            file_name = f"dataset/User_{user_id}_{roll}_{count}.jpg"
            cv2.imwrite(file_name, gray[y:y+h, x:x+w])
            
            # Show live camera with rectangle
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"Captured: {count}/30", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.imshow('Capturing 30 Faces', frame)

        # Break loop after 30 images or if 'q' is pressed
        if count >= 30:
            break
        if cv2.waitKey(100) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()
    if count >= 30:
        messagebox.showinfo("Success", f"30 images captured securely for {name} ({roll})")

def submit_form():
    name = entry_name.get().strip()
    roll = entry_roll.get().strip()
    dept = entry_dept.get().strip()

    if not name or not roll or not dept:
        messagebox.showwarning("Incomplete", "Please fill all the details!")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        # Check if roll exists
        c.execute('SELECT id FROM users WHERE roll = ?', (roll,))
        existing = c.fetchone()
        
        if existing:
            user_id = existing[0]
            # Update user info if already exists
            c.execute('UPDATE users SET name = ?, department = ? WHERE id = ?', (name, dept, user_id))
        else:
            # Insert new user
            c.execute('INSERT INTO users (name, roll, department) VALUES (?, ?, ?)', (name, roll, dept))
            user_id = c.lastrowid
        conn.commit()
        
        messagebox.showinfo("Database", "Details Saved! Camera will now open.")
        capture_images(user_id, roll, name)
        
        # Clear fields
        entry_name.delete(0, tk.END)
        entry_roll.delete(0, tk.END)
        entry_dept.delete(0, tk.END)

    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        conn.close()

# --- TKINTER GUI ---
root = tk.Tk()
root.title("Add New User")
root.geometry("400x350")
root.configure(bg="#f4f4f4")

tk.Label(root, text="Register Profile", font=("Helvetica", 16, "bold"), bg="#f4f4f4").pack(pady=20)

frame = tk.Frame(root, bg="#f4f4f4")
frame.pack()

tk.Label(frame, text="Full Name:", font=("Helvetica", 12), bg="#f4f4f4").grid(row=0, column=0, pady=10, sticky="e")
entry_name = tk.Entry(frame, font=("Helvetica", 12), width=20)
entry_name.grid(row=0, column=1, pady=10, padx=10)

tk.Label(frame, text="Roll Number:", font=("Helvetica", 12), bg="#f4f4f4").grid(row=1, column=0, pady=10, sticky="e")
entry_roll = tk.Entry(frame, font=("Helvetica", 12), width=20)
entry_roll.grid(row=1, column=1, pady=10, padx=10)

tk.Label(frame, text="Department:", font=("Helvetica", 12), bg="#f4f4f4").grid(row=2, column=0, pady=10, sticky="e")
entry_dept = tk.Entry(frame, font=("Helvetica", 12), width=20)
entry_dept.grid(row=2, column=1, pady=10, padx=10)

btn_submit = tk.Button(root, text="Save & Capture Face", font=("Helvetica", 12, "bold"), bg="#007BFF", fg="white", command=submit_form)
btn_submit.pack(pady=20)

root.mainloop()
