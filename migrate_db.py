"""
Migration script to add fund_id column to months table and create funds table
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
    # Check if fund_id column exists
    cursor.execute("PRAGMA table_info(months)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'fund_id' not in columns:
        print("Adding fund_id column to months table...")
        # Add fund_id column (nullable first, we'll update it later)
        cursor.execute("ALTER TABLE months ADD COLUMN fund_id INTEGER")
        
        # Check if funds table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='funds'")
        if not cursor.fetchone():
            print("Creating funds table...")
            cursor.execute("""
                CREATE TABLE funds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR NOT NULL,
                    description VARCHAR,
                    total_amount FLOAT NOT NULL,
                    number_of_months INTEGER DEFAULT 10,
                    created_by INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(created_by) REFERENCES users(id)
                )
            """)
            
            # Create fund_members association table
            cursor.execute("""
                CREATE TABLE fund_members (
                    fund_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY (fund_id, user_id),
                    FOREIGN KEY(fund_id) REFERENCES funds(id),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)
            
            # Create a default fund and assign all existing months to it
            # First, get admin user
            cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
            admin_result = cursor.fetchone()
            if admin_result:
                admin_id = admin_result[0]
                print("Creating default fund...")
                cursor.execute("""
                    INSERT INTO funds (name, description, total_amount, number_of_months, created_by)
                    VALUES ('NewYear2026 Scheme', 'Default chit fund scheme', 150000.0, 10, ?)
                """, (admin_id,))
                fund_id = cursor.lastrowid
                
                # Add admin as member
                cursor.execute("INSERT INTO fund_members (fund_id, user_id) VALUES (?, ?)", (fund_id, admin_id))
                
                # Update all existing months to belong to this fund
                cursor.execute("UPDATE months SET fund_id = ?", (fund_id,))
                print(f"Assigned {cursor.rowcount} months to default fund")
            else:
                print("Warning: No admin user found. Please create a fund manually.")
        
        conn.commit()
        print("Migration completed successfully!")
    else:
        print("fund_id column already exists. Migration not needed.")
    
    # Check if fund_members table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fund_members'")
    if not cursor.fetchone():
        print("Creating fund_members table...")
        cursor.execute("""
            CREATE TABLE fund_members (
                fund_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (fund_id, user_id),
                FOREIGN KEY(fund_id) REFERENCES funds(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
        print("fund_members table created!")
    
except Exception as e:
    conn.rollback()
    print(f"Error during migration: {e}")
    raise
finally:
    conn.close()

