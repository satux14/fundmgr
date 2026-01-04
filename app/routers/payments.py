from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, get_current_admin_user
from app.models import User, InstallmentPayment

router = APIRouter()

@router.get("/api/payments")
async def get_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "admin":
        payments = db.query(InstallmentPayment).all()
    else:
        payments = db.query(InstallmentPayment).filter(
            InstallmentPayment.user_id == current_user.id
        ).all()
    
    return payments

