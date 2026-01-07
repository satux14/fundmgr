"""
Script to seed initial data for the chit fund management system.
Run this once to populate the database with fund, month data and create admin user.
"""
from app.database import SessionLocal, engine, Base
from app.models import User, Month, Fund
from app.auth import get_password_hash

# Create tables
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # Check if admin user exists, create if not
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        admin_user = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            full_name="Administrator",
            role="admin"
        )
        db.add(admin_user)
        db.flush()  # Get the admin user ID
        print("Created admin user (username: admin, password: admin123)")
    else:
        print("Admin user already exists.")
    
    # Check if guest user exists, create if not
    guest_user = db.query(User).filter(User.username == "guest").first()
    if not guest_user:
        guest_user = User(
            username="guest",
            password_hash=get_password_hash("guest"),
            full_name="Guest User",
            role="guest",
            customer_id="GUEST"
        )
        db.add(guest_user)
        print("Created guest user (username: guest, password: guest)")
    else:
        print("Guest user already exists.")
    
    # Check if default fund exists
    default_fund = db.query(Fund).filter(Fund.name == "1.5 Lakh Scheme - 2026").first()
    if not default_fund:
        # Create default fund
        default_fund = Fund(
            name="NewYear2026 Scheme",
            description="Default chit fund scheme",
            total_amount=150000.0,
            number_of_months=10,
            created_by=admin_user.id
        )
        db.add(default_fund)
        db.flush()  # Get the fund ID
        
        # Add admin as member
        default_fund.members.append(admin_user)
        
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
            month = Month(**month_data, fund_id=default_fund.id, year=2026)
            db.add(month)
        
        print("Created default fund '1.5 Lakh Scheme - 2026' with 10 months of data.")
    else:
        print("Default fund already exists. Skipping fund and month creation.")
    
    db.commit()
    print("Database seeded successfully!")
    
except Exception as e:
    db.rollback()
    print(f"Error seeding database: {e}")
    raise
finally:
    db.close()

