"""
Migration script to add customer_id and alias columns to users table
"""
import sqlite3
import os
from pathlib import Path

# Database path
db_path = Path("data/fundmgr.db")
if not db_path.exists():
    print("Database does not exist. It will be created on first run.")
    exit(0)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

try:
    # Check if customer_id column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'customer_id' not in columns:
        print("Adding customer_id column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN customer_id VARCHAR")
        
        # Generate customer IDs for existing users (format: C001, C002, etc.)
        cursor.execute("SELECT id FROM users ORDER BY id")
        user_ids = cursor.fetchall()
        for idx, (user_id,) in enumerate(user_ids, start=1):
            customer_id = f"C{idx:03d}"
            cursor.execute("UPDATE users SET customer_id = ? WHERE id = ?", (customer_id, user_id))
        print(f"Generated customer IDs for {len(user_ids)} users")
        
        # Create unique index on customer_id
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_customer_id ON users(customer_id)")
        conn.commit()
        print("customer_id column added successfully!")
    else:
        print("customer_id column already exists. Migration not needed.")
    
    if 'alias' not in columns:
        print("Adding alias column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN alias VARCHAR")
        conn.commit()
        print("alias column added successfully!")
    else:
        print("alias column already exists. Migration not needed.")
    
except Exception as e:
    conn.rollback()
    print(f"Error during migration: {e}")
    raise
finally:
    conn.close()

