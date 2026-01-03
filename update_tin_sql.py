import sqlite3
import os

# Database Path
# Flask default for SQLALCHEMY_DATABASE_URI='sqlite:///rental_system.db' is usually in root or instance folder.
# Let's check root first.

db_path = "instance/rental.db"
if not os.path.exists(db_path):
    db_path = "rental.db"

if not os.path.exists(db_path):
    # Try absolute path from previous knowledge or just listing
    print(f"Database file not found. Tried {db_path} and instance/rental.db")
    exit(1)

print(f"Connecting to {db_path}...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check current value
    cursor.execute("SELECT issuer_tin FROM my_invois_config")
    row = cursor.fetchone()
    if row:
        print(f"Old TIN: {row[0]}")
    
    # Update
    new_tin = "C7850149000"
    cursor.execute("UPDATE my_invois_config SET issuer_tin = ?", (new_tin,))
    conn.commit()
    
    print(f"Updated TIN to {new_tin}")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
