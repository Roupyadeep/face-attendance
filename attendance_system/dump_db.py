import sqlite3

def dump_db():
    conn = sqlite3.connect('attendance.db')
    conn.row_factory = sqlite3.Row
    
    print("--- USERS TABLE ---")
    users = conn.execute('SELECT * FROM users').fetchall()
    for user in users:
        print(dict(user))
        
    print("\n--- ATTENDANCE TABLE (Last 10) ---")
    attendance = conn.execute('SELECT * FROM attendance ORDER BY timestamp DESC LIMIT 10').fetchall()
    for record in attendance:
        print(dict(record))
        
    conn.close()

if __name__ == "__main__":
    dump_db()
