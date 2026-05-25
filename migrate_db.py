import os
import sys

# Add the current directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import psycopg
from app.core.config import settings

def run_migration():
    db_url = settings.DATABASE_URL
    print(f"Connecting to database to run schema migrations...")
    
    try:
        conn = psycopg.connect(db_url)
        with conn.cursor() as cur:
            print("Adding 'pin_close' column to table 'lockers' if not exists...")
            cur.execute("ALTER TABLE lockers ADD COLUMN IF NOT EXISTS pin_close VARCHAR;")
            
            print("Adding 'pin_open' column to table 'lockers' if not exists...")
            cur.execute("ALTER TABLE lockers ADD COLUMN IF NOT EXISTS pin_open VARCHAR;")
            
            print("Adding 'contact_email' column to table 'lockers' if not exists...")
            cur.execute("ALTER TABLE lockers ADD COLUMN IF NOT EXISTS contact_email VARCHAR;")
            
            print("Adding 'warning_sent' column to table 'lockers' if not exists...")
            cur.execute("ALTER TABLE lockers ADD COLUMN IF NOT EXISTS warning_sent BOOLEAN DEFAULT FALSE;")
            
            print("Adding 'is_locked' column to table 'lockers' if not exists...")
            cur.execute("ALTER TABLE lockers ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT FALSE;")
            
            print("Adding 'student_code' column to table 'users' if not exists...")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS student_code VARCHAR UNIQUE;")

            print("Adding 'payment_receipt_url' column to table 'lockers' if not exists...")
            cur.execute("ALTER TABLE lockers ADD COLUMN IF NOT EXISTS payment_receipt_url VARCHAR;")
            
            print("Adding 'pending_rent_hours' column to table 'lockers' if not exists...")
            cur.execute("ALTER TABLE lockers ADD COLUMN IF NOT EXISTS pending_rent_hours FLOAT;")
            
            print("Adding 'approved_at' column to table 'lockers' if not exists...")
            cur.execute("ALTER TABLE lockers ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;")
            
            conn.commit()
            print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
