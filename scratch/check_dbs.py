import sqlite3
import os

dbs = [
    "attendance.sqlite",
    "localstoredb.sqlite",
    "attendance_system/attendance.db"
]

for db in dbs:
    if os.path.exists(db):
        print(f"\nChecking DB: {db}")
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for table in tables:
            table_name = table[0]
            print(f"  Table: {table_name}")
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
            rows = cursor.fetchall()
            for row in rows:
                print(f"    {row}")
        conn.close()
    else:
        print(f"\nDB {db} does not exist")
