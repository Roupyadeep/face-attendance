import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import datetime
import csv
import os

DB_FILE = "attendance.db"

def fetch_data(date_filter=None):
    if not date_filter:
        date_filter = datetime.datetime.now().strftime('%Y-%m-%d')
        
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('SELECT name, roll, department, status, timestamp, date FROM attendance WHERE date = ? ORDER BY timestamp DESC', (date_filter,))
        rows = c.fetchall()
        return rows
    except Exception as e:
        print("Database error:", e)
        return []
    finally:
        conn.close()

def refresh_table():
    for item in tree.get_children():
        tree.delete(item)
    
    date_filter = entry_date.get()
    rows = fetch_data(date_filter)
    
    for row in rows:
        tree.insert("", "end", values=row)

def export_csv():
    date_filter = entry_date.get()
    rows = fetch_data(date_filter)
    
    if not rows:
        messagebox.showwarning("Warning", f"No records found for {date_filter} to export.")
        return
        
    filename = f"Attendance_{date_filter}.csv"
    try:
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow(['Name', 'Roll Number', 'Department', 'Status', 'Time', 'Date'])
            writer.writerows(rows)
        messagebox.showinfo("Success", f"Attendance exported successfully to {filename}")
    except Exception as e:
        messagebox.showerror("Error", f"Could not export CSV:\n{e}")

# --- TKINTER GUI ---
root = tk.Tk()
root.title("View Attendance")
root.geometry("800x500")

# Top Frame for filters
top_frame = tk.Frame(root, pady=10)
top_frame.pack()

tk.Label(top_frame, text="Filter by Date (YYYY-MM-DD):", font=("Helvetica", 12)).pack(side=tk.LEFT, padx=10)
entry_date = tk.Entry(top_frame, font=("Helvetica", 12))
entry_date.insert(0, datetime.datetime.now().strftime('%Y-%m-%d'))
entry_date.pack(side=tk.LEFT, padx=10)

tk.Button(top_frame, text="Load Data", font=("Helvetica", 10, "bold"), bg="#28a745", fg="white", command=refresh_table).pack(side=tk.LEFT, padx=5)
tk.Button(top_frame, text="Export CSV", font=("Helvetica", 10, "bold"), bg="#17a2b8", fg="white", command=export_csv).pack(side=tk.LEFT, padx=5)

# Treeview
columns = ("Name", "Roll", "Department", "Status", "Timestamp", "Date")
tree = ttk.Treeview(root, columns=columns, show="headings", height=20)

for col in columns:
    tree.heading(col, text=col)
    tree.column(col, anchor=tk.CENTER, minwidth=100, width=120)

tree.pack(pady=20, fill=tk.BOTH, expand=True)

# Initial Load
refresh_table()

root.mainloop()
