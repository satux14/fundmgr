#!/usr/bin/env python3
"""
Simple script to create guest user using SQLite directly
Works around bcrypt version issues in local venv
"""

import sqlite3
import os
import hashlib

# Database paths
db_path_dev = os.path.join(os.path.dirname(__file__), "data", "fundmgr.db")
db_path_prod = os.path.join(os.path.dirname(__file__), "data-prod", "fundmgr.db")

def create_guest_user_sqlite(db_path, db_name):
    """Create guest user using SQLite directly"""
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}, skipping {db_name}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if guest user exists
        cursor.execute("SELECT id, username, role, customer_id FROM users WHERE username = ?", ("guest",))
        existing = cursor.fetchone()
        
        if existing:
            print(f"[{db_name}] Guest user already exists.")
            print(f"  Username: {existing[1]}")
            print(f"  Role: {existing[2]}")
            print(f"  Customer ID: {existing[3]}")
        else:
            # Get a password hash from an existing user to use the same format
            # Or we can use a simple approach - get the hash from Docker container
            # For now, let's try to import and use the auth module if possible
            try:
                # Try to use the app's auth module (works in Docker)
                from app.auth import get_password_hash
                password_hash = get_password_hash("guest")
            except:
                # Fallback: Use a known hash format or create via SQL
                # We'll need to get the hash from Docker or use a workaround
                print(f"[{db_name}] Cannot create password hash locally. Please run this script in Docker container.")
                print(f"  Or run: docker-compose -f docker-compose.dev.yml exec fundmgr-app python create_guest_user.py")
                return
            
            # Insert guest user
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, role, customer_id, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, ("guest", password_hash, "Guest User", "guest", "GUEST"))
            
            conn.commit()
            print(f"[{db_name}] Guest user created successfully!")
            print(f"  Username: guest")
            print(f"  Password: guest")
            print(f"  Role: guest")
            print(f"  Customer ID: GUEST")
            
    except Exception as e:
        conn.rollback()
        print(f"[{db_name}] Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("Creating guest user in databases...")
    print("=" * 50)
    
    # Create guest user in dev database
    create_guest_user_sqlite(db_path_dev, "DEV")
    
    # Create guest user in prod database if it exists
    if os.path.exists(db_path_prod):
        create_guest_user_sqlite(db_path_prod, "PROD")
    
    print("=" * 50)
    print("Guest user creation completed!")

