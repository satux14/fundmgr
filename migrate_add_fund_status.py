#!/usr/bin/env python3
"""
Migration script to add is_archived and is_deleted columns to funds table
"""

import sqlite3
import os
import sys

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), "data", "fundmgr.db")
db_path_prod = os.path.join(os.path.dirname(__file__), "data-prod", "fundmgr.db")

def migrate_database(db_path):
    """Add is_archived and is_deleted columns to funds table"""
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}, skipping migration")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(funds)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add is_archived column if it doesn't exist
        if 'is_archived' not in columns:
            print(f"Adding is_archived column to funds table in {db_path}")
            cursor.execute("ALTER TABLE funds ADD COLUMN is_archived INTEGER DEFAULT 0 NOT NULL")
        else:
            print(f"Column is_archived already exists in {db_path}")
        
        # Add is_deleted column if it doesn't exist
        if 'is_deleted' not in columns:
            print(f"Adding is_deleted column to funds table in {db_path}")
            cursor.execute("ALTER TABLE funds ADD COLUMN is_deleted INTEGER DEFAULT 0 NOT NULL")
        else:
            print(f"Column is_deleted already exists in {db_path}")
        
        conn.commit()
        print(f"Migration completed successfully for {db_path}")
        
    except Exception as e:
        print(f"Error migrating {db_path}: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting migration: Add is_archived and is_deleted to funds table")
    
    # Migrate dev database
    migrate_database(db_path)
    
    # Migrate prod database if it exists
    if os.path.exists(db_path_prod):
        migrate_database(db_path_prod)
    
    print("Migration completed!")

