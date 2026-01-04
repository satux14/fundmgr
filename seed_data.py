"""
Script to seed initial data for the chit fund management system.
Run this once to populate the database with month data and create admin user.
"""
from app.database import SessionLocal, engine, Base
from app.models import User, Month
from app.auth import get_password_hash

# Create tables
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # Check if months already exist
    existing_months = db.query(Month).count()
    if existing_months > 0:
        print("Months already exist. Skipping seed.")
    else:
        # Create months data from the image
        months_data = [
            {"month_name": "Jan", "month_number": 1, "installment_amount": 12450.0, "payment_amount": 123000.0},
            {"month_name": "Feb", "month_number": 2, "installment_amount": 15000.0, "payment_amount": 150000.0},
            {"month_name": "Mar", "month_number": 3, "installment_amount": 13050.0, "payment_amount": 129000.0},
            {"month_name": "Apr", "month_number": 4, "installment_amount": 13350.0, "payment_amount": 132000.0},
            {"month_name": "May", "month_number": 5, "installment_amount": 13650.0, "payment_amount": 135000.0},
            {"month_name": "Jun", "month_number": 6, "installment_amount": 13950.0, "payment_amount": 138000.0},
            {"month_name": "Jul", "month_number": 7, "installment_amount": 14250.0, "payment_amount": 141000.0},
            {"month_name": "Aug", "month_number": 8, "installment_amount": 14550.0, "payment_amount": 144000.0},
            {"month_name": "Sep", "month_number": 9, "installment_amount": 14850.0, "payment_amount": 147000.0},
            {"month_name": "Oct", "month_number": 10, "installment_amount": 15150.0, "payment_amount": 150000.0},
        ]
        
        for month_data in months_data:
            month = Month(**month_data, year=2026)
            db.add(month)
        
        print("Created 10 months of data.")
    
    # Check if admin user exists
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        admin_user = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            full_name="Administrator",
            role="admin"
        )
        db.add(admin_user)
        print("Created admin user (username: admin, password: admin123)")
    else:
        print("Admin user already exists.")
    
    db.commit()
    print("Database seeded successfully!")
    
except Exception as e:
    db.rollback()
    print(f"Error seeding database: {e}")
    raise
finally:
    db.close()

