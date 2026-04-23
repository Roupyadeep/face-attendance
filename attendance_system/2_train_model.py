import cv2
import numpy as np
import os
from tkinter import messagebox
import tkinter as tk

def train_model():
    path = 'dataset'
    
    if not os.path.exists(path) or len(os.listdir(path)) == 0:
        messagebox.showerror("Error", "No dataset found. Please run 1_add_user.py first.")
        return

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    image_paths = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.jpg')]
    
    faces = []
    ids = []

    for image_path in image_paths:
        try:
            # Filename format: User_{id}_{roll}_{count}.jpg
            filename = os.path.split(image_path)[-1]
            user_id = int(filename.split('_')[1])
            
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            
            if img is not None:
                faces.append(img)
                ids.append(user_id)
        except Exception as e:
            print(f"Skipping {image_path}: {e}")

    if len(faces) == 0:
        messagebox.showerror("Error", "No valid face images found in dataset.")
        return

    os.makedirs('trainer', exist_ok=True)
    
    print("Training in progress... please wait.")
    recognizer.train(faces, np.array(ids))
    recognizer.write('trainer/trainer.yml')
    
    # Extract unique users trained
    unique_faces = len(set(ids))
    print(f"Model trained successfully. Profiles trained: {unique_faces}")
    messagebox.showinfo("Success", f"Model trained with {len(faces)} images across {unique_faces} users.\nSaved to trainer/trainer.yml")

if __name__ == "__main__":
    # Create an invisible Tkinter root for messageboxes
    root = tk.Tk()
    root.withdraw()
    train_model()
    root.destroy()
