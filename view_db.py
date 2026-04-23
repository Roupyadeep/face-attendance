import sqlite3
import os

def view_table(db_name, table_name):
    if not os.path.exists(db_name):
        print(f"--- {db_name} not found ---")
        return
        
    print(f"\n{'='*50}")
    print(f" DATABASE: {db_name} | TABLE: {table_name}")
    print(f"{'='*50}")
    
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        # Get column names
        names = [description[0] for description in cursor.description]
        print(" | ".join(names))
        print("-" * 50)
        
        if not rows:
            print("(No data found)")
        for row in rows:
            print(" | ".join(map(str, row)))
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    view_table("localstoredb.sqlite", "Users")
    view_table("attendance.sqlite", "AttendanceLogs")
