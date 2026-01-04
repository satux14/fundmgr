from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.models import User, Month, UserMonthAssignment, InstallmentPayment
from app.schemas import MonthWithStatus

router = APIRouter()
import os
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
templates = Jinja2Templates(directory=template_dir)

@router.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get all months
    months = db.query(Month).order_by(Month.month_number).all()
    
    # Get user's assigned month
    user_assignment = db.query(UserMonthAssignment).filter(
        UserMonthAssignment.user_id == current_user.id
    ).first()
    
    assigned_month_id = user_assignment.month_id if user_assignment else None
    
    # Get all payments for this user
    payments = db.query(InstallmentPayment).filter(
        InstallmentPayment.user_id == current_user.id
    ).all()
    
    payment_map = {p.month_id: p for p in payments}
    
    # Build month data with status
    months_data = []
    for month in months:
        is_taken = month.id == assigned_month_id
        payment = payment_map.get(month.id)
        months_data.append({
            "id": month.id,
            "month_name": month.month_name,
            "month_number": month.month_number,
            "installment_amount": month.installment_amount,
            "payment_amount": month.payment_amount,
            "is_taken": is_taken,
            "payment_status": payment.status if payment else None,
            "payment_id": payment.id if payment else None
        })
    
    return templates.TemplateResponse(
        "user_dashboard.html",
        {
            "request": request,
            "user": current_user,
            "months": months_data
        }
    )

@router.get("/api/user/months")
async def get_user_months(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    months = db.query(Month).order_by(Month.month_number).all()
    user_assignment = db.query(UserMonthAssignment).filter(
        UserMonthAssignment.user_id == current_user.id
    ).first()
    assigned_month_id = user_assignment.month_id if user_assignment else None
    
    payments = db.query(InstallmentPayment).filter(
        InstallmentPayment.user_id == current_user.id
    ).all()
    payment_map = {p.month_id: p for p in payments}
    
    months_data = []
    for month in months:
        payment = payment_map.get(month.id)
        months_data.append(MonthWithStatus(
            id=month.id,
            month_name=month.month_name,
            month_number=month.month_number,
            installment_amount=month.installment_amount,
            payment_amount=month.payment_amount,
            is_taken=month.id == assigned_month_id,
            payment_status=payment.status if payment else None,
            payment_id=payment.id if payment else None
        ))
    
    return months_data

@router.post("/api/user/payments")
async def mark_payment(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get month_id from form data
    form_data = await request.form()
    month_id = int(form_data.get("month_id", 0))
    # Check if payment already exists
    existing = db.query(InstallmentPayment).filter(
        InstallmentPayment.user_id == current_user.id,
        InstallmentPayment.month_id == month_id
    ).first()
    
    if existing:
        return {"message": "Payment already marked", "payment_id": existing.id}
    
    # Create new payment
    payment = InstallmentPayment(
        user_id=current_user.id,
        month_id=month_id,
        marked_by=current_user.id,
        status="pending"
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    return {"message": "Payment marked successfully", "payment_id": payment.id}

