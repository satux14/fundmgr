import sqlite3
from pathlib import Path

db_path = Path("data/fundmgr.db")
if not db_path.exists():
    print("Database does not exist. Skipping payment fields migration.")
    exit(0)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

try:
    cursor.execute("PRAGMA table_info(installment_payments)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'payment_date' not in columns:
        print("Adding payment_date, transaction_id, and transaction_type columns to installment_payments table...")
        cursor.execute("ALTER TABLE installment_payments ADD COLUMN payment_date DATETIME")
        cursor.execute("ALTER TABLE installment_payments ADD COLUMN transaction_id VARCHAR")
        cursor.execute("ALTER TABLE installment_payments ADD COLUMN transaction_type VARCHAR")
        conn.commit()
        print("Payment fields added successfully!")
    else:
        print("Payment fields already exist. Migration not needed.")

except Exception as e:
    conn.rollback()
    print(f"Error during payment fields migration: {e}")
    raise
finally:
    conn.close()

