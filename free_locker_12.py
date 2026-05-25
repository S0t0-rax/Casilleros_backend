import psycopg
import os

db_url = "postgresql://postgres.boraxblgsnwoxhekrsgw:fabicra4004M@aws-1-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require"

def free_locker_12():
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE lockers 
                    SET status = 'DISPONIBLE',
                        assigned_user_id = NULL,
                        occupied_until = NULL,
                        last_payment_at = NULL,
                        pin_close = NULL,
                        pin_open = NULL,
                        is_locked = FALSE,
                        payment_receipt_url = NULL,
                        pending_rent_hours = NULL,
                        approved_at = NULL,
                        contact_email = NULL,
                        warning_sent = FALSE
                    WHERE locker_number = 'C-12';
                """)
                conn.commit()
                print("El casillero 12 ha sido liberado exitosamente.")
    except Exception as e:
        print(f"Error al conectar con Supabase: {e}")

if __name__ == "__main__":
    free_locker_12()
