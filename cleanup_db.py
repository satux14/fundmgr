"""
Database cleanup script to remove all funds and months data while preserving users.
Run this script to start fresh with the new fund creation flow.
"""
from app.database import SessionLocal, engine, Base
from app.models import User, Month, Fund, UserMonthAssignment, InstallmentPayment
from sqlalchemy import text
from pathlib import Path

# Database path
db_path = Path("data/fundmgr.db")
if not db_path.exists():
    print("Database does not exist. Nothing to clean up.")
    exit(0)

print("=" * 60)
print("DATABASE CLEANUP SCRIPT")
print("=" * 60)
print("\nThis script will DELETE:")
print("  - All funds")
print("  - All months")
print("  - All month assignments")
print("  - All installment payments")
print("  - All fund memberships")
print("\nThis script will PRESERVE:")
print("  - All users (including admin)")
print("=" * 60)

response = input("\nAre you sure you want to proceed? (yes/no): ")
if response.lower() != "yes":
    print("Cleanup cancelled.")
    exit(0)

db = SessionLocal()

try:
    # Get counts before deletion
    funds_count = db.query(Fund).count()
    months_count = db.query(Month).count()
    assignments_count = db.query(UserMonthAssignment).count()
    payments_count = db.query(InstallmentPayment).count()
    
    # Get fund_members count using raw SQL (association table)
    result = db.execute(text("SELECT COUNT(*) FROM fund_members"))
    memberships_count = result.scalar() or 0
    
    # Delete in order to respect foreign key constraints
    print("\nDeleting installment payments...")
    db.query(InstallmentPayment).delete()
    print(f"  Deleted {payments_count} installment payment(s)")
    
    print("Deleting month assignments...")
    db.query(UserMonthAssignment).delete()
    print(f"  Deleted {assignments_count} month assignment(s)")
    
    print("Deleting months...")
    db.query(Month).delete()
    print(f"  Deleted {months_count} month(s)")
    
    # Delete fund_members association table entries using SQLAlchemy text()
    print("Deleting fund memberships...")
    db.execute(text("DELETE FROM fund_members"))
    print(f"  Deleted {memberships_count} fund membership(s)")
    
    print("Deleting funds...")
    db.query(Fund).delete()
    print(f"  Deleted {funds_count} fund(s)")
    
    # Verify users are preserved
    users_count = db.query(User).count()
    print(f"\nUsers preserved: {users_count}")
    
    db.commit()
    print("\n" + "=" * 60)
    print("CLEANUP COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\nYou can now create new funds using the fund creation form.")
    
except Exception as e:
    db.rollback()
    print(f"\nERROR during cleanup: {e}")
    import traceback
    traceback.print_exc()
    raise
finally:
    db.close()

