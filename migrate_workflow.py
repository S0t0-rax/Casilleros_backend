import sqlite3
import os

def upgrade():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.db")
    print(f"Migrating database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(lockers)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "pending_rent_hours" not in columns:
        print("Adding pending_rent_hours column...")
        cursor.execute("ALTER TABLE lockers ADD COLUMN pending_rent_hours FLOAT")
        
    if "approved_at" not in columns:
        print("Adding approved_at column...")
        cursor.execute("ALTER TABLE lockers ADD COLUMN approved_at DATETIME")
        
    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    upgrade()
