#!/usr/bin/env python3
"""
Migration script to add monthly_payments_received table
"""
import sqlite3
import os
from pathlib import Path

# Get database path
db_path = Path(__file__).parent / "data" / "fundmgr.db"

if not db_path.exists():
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

try:
    # Check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monthly_payments_received'")
    if cursor.fetchone():
        print("Table 'monthly_payments_received' already exists. Skipping migration.")
    else:
        # Create monthly_payments_received table
        cursor.execute("""
            CREATE TABLE monthly_payments_received (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                month_id INTEGER NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                received_at DATETIME NOT NULL,
                marked_by INTEGER NOT NULL,
                verified_by INTEGER,
                status VARCHAR NOT NULL DEFAULT 'pending',
                amount FLOAT NOT NULL,
                FOREIGN KEY(month_id) REFERENCES months (id),
                FOREIGN KEY(user_id) REFERENCES users (id),
                FOREIGN KEY(marked_by) REFERENCES users (id),
                FOREIGN KEY(verified_by) REFERENCES users (id)
            )
        """)
        conn.commit()
        print("Successfully created 'monthly_payments_received' table.")
except Exception as e:
    print(f"Error during migration: {e}")
    conn.rollback()
finally:
    conn.close()

