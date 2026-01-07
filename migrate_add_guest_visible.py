#!/usr/bin/env python3
"""
Migration script to add guest_visible column to funds table
"""

import sqlite3
import os
import sys

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), "data", "fundmgr.db")
db_path_prod = os.path.join(os.path.dirname(__file__), "data-prod", "fundmgr.db")

def migrate_database(db_path):
    """Add guest_visible column to funds table"""
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}, skipping migration")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(funds)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "guest_visible" in columns:
            print(f"Column guest_visible already exists in {db_path}")
            return
        
        print(f"Adding guest_visible column to funds table in {db_path}")
        
        # Add guest_visible column
        cursor.execute("""
            ALTER TABLE funds
            ADD COLUMN guest_visible INTEGER NOT NULL DEFAULT 0
        """)
        
        conn.commit()
        print(f"Migration completed successfully for {db_path}")
        
    except Exception as e:
        print(f"Error migrating {db_path}: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting migration: Add guest_visible column to funds table")
    
    # Migrate dev database
    migrate_database(db_path)
    
    # Migrate prod database if it exists
    if os.path.exists(db_path_prod):
        migrate_database(db_path_prod)
    
    print("Migration completed!")

