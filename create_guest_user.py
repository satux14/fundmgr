#!/usr/bin/env python3
"""
Script to create guest user if it doesn't exist
Works with both dev and prod databases
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import User, Base

# Try to import get_password_hash, with fallback for local venv issues
try:
    from app.auth import get_password_hash
except Exception as e:
    print(f"Warning: Could not import get_password_hash: {e}")
    print("This script should be run inside Docker container where dependencies are correct.")
    sys.exit(1)

# Database paths
db_path_dev = os.path.join(os.path.dirname(__file__), "data", "fundmgr.db")
db_path_prod = os.path.join(os.path.dirname(__file__), "data-prod", "fundmgr.db")

def create_guest_user_in_db(db_path, db_name):
    """Create guest user in a specific database"""
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}, skipping {db_name}")
        return
    
    # Create engine for this specific database
    database_url = f"sqlite:///{db_path}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if guest user exists
        guest_user = db.query(User).filter(User.username == "guest").first()
        
        if guest_user:
            print(f"[{db_name}] Guest user already exists.")
            print(f"  Username: {guest_user.username}")
            print(f"  Role: {guest_user.role}")
            print(f"  Customer ID: {guest_user.customer_id}")
        else:
            print(f"[{db_name}] Creating guest user...")
            guest_user = User(
                username="guest",
                password_hash=get_password_hash("guest"),
                full_name="Guest User",
                role="guest",
                customer_id="GUEST"
            )
            db.add(guest_user)
            db.commit()
            db.refresh(guest_user)
            print(f"[{db_name}] Guest user created successfully!")
            print(f"  Username: guest")
            print(f"  Password: guest")
            print(f"  Role: guest")
            print(f"  Customer ID: GUEST")
            
    except Exception as e:
        db.rollback()
        print(f"[{db_name}] Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Creating guest user in databases...")
    print("=" * 50)
    
    # Create guest user in dev database
    create_guest_user_in_db(db_path_dev, "DEV")
    
    # Create guest user in prod database if it exists
    if os.path.exists(db_path_prod):
        create_guest_user_in_db(db_path_prod, "PROD")
    
    print("=" * 50)
    print("Guest user creation completed!")

