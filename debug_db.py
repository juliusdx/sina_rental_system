
import sqlite3
import os

DB_FILES = ['rental.db', 'instance/rental.db', 'rental_data.db']

for db_file in DB_FILES:
    if os.path.exists(db_file):
        print(f"--- Checking {db_file} ---")
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"Tables: {[t[0] for t in tables]}")
            conn.close()
        except Exception as e:
            print(f"Error reading {db_file}: {e}")
    else:
        print(f"--- {db_file} NOT FOUND ---")
