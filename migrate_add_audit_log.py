#!/usr/bin/env python3
"""
Migration script to add audit_logs table for tracking user actions
"""

import sqlite3
import os
import sys

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), "data", "fundmgr.db")
db_path_prod = os.path.join(os.path.dirname(__file__), "data-prod", "fundmgr.db")

def migrate_database(db_path):
    """Add audit_logs table"""
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}, skipping migration")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
        if cursor.fetchone():
            print(f"Table audit_logs already exists in {db_path}")
            return
        
        print(f"Creating audit_logs table in {db_path}")
        
        # Create audit_logs table
        cursor.execute("""
            CREATE TABLE audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action_type VARCHAR NOT NULL,
                action_description VARCHAR NOT NULL,
                ip_address VARCHAR,
                user_agent VARCHAR,
                details VARCHAR,
                fund_id INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (fund_id) REFERENCES funds(id)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id)")
        cursor.execute("CREATE INDEX idx_audit_logs_action_type ON audit_logs(action_type)")
        cursor.execute("CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at)")
        cursor.execute("CREATE INDEX idx_audit_logs_fund_id ON audit_logs(fund_id)")
        
        conn.commit()
        print(f"Migration completed successfully for {db_path}")
        
    except Exception as e:
        print(f"Error migrating {db_path}: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting migration: Add audit_logs table")
    
    # Migrate dev database
    migrate_database(db_path)
    
    # Migrate prod database if it exists
    if os.path.exists(db_path_prod):
        migrate_database(db_path_prod)
    
    print("Migration completed!")

