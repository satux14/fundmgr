from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.auth import get_current_admin_user, get_password_hash
from app.models import User, Month, UserMonthAssignment, InstallmentPayment
from app.schemas import UserCreate, UserResponse

router = APIRouter()
import os
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
templates = Jinja2Templates(directory=template_dir)

@router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # Get statistics
    total_users = db.query(User).count()
    total_months = db.query(Month).count()
    assigned_months = db.query(UserMonthAssignment).count()
    total_payments = db.query(InstallmentPayment).count()
    verified_payments = db.query(InstallmentPayment).filter(
        InstallmentPayment.status == "verified"
    ).count()
    
    # Get all months with assignments
    months = db.query(Month).order_by(Month.month_number).all()
    assignments = db.query(UserMonthAssignment).all()
    assignment_map = {a.month_id: a for a in assignments}
    
    months_data = []
    for month in months:
        assignment = assignment_map.get(month.id)
        months_data.append({
            "month": month,
            "assignment": assignment,
            "assigned_user": assignment.user if assignment else None
        })
    
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "user": current_user,
            "total_users": total_users,
            "total_months": total_months,
            "assigned_months": assigned_months,
            "total_payments": total_payments,
            "verified_payments": verified_payments,
            "months_data": months_data
        }
    )

@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    return templates.TemplateResponse(
        "admin_users.html",
        {"request": request, "user": current_user, "users": users}
    )

@router.post("/admin/users")
async def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form("user"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # Check if username exists
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return templates.TemplateResponse(
            "admin_users.html",
            {
                "request": request,
                "user": current_user,
                "users": db.query(User).all(),
                "error": "Username already exists"
            },
            status_code=400
        )
    
    # Create user
    new_user = User(
        username=username,
        password_hash=get_password_hash(password),
        full_name=full_name,
        role=role
    )
    db.add(new_user)
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=302)

@router.get("/admin/months", response_class=HTMLResponse)
async def admin_months(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    months = db.query(Month).order_by(Month.month_number).all()
    assignments = db.query(UserMonthAssignment).all()
    assignment_map = {a.month_id: a for a in assignments}
    users = db.query(User).filter(User.role == "user").all()
    
    months_data = []
    for month in months:
        assignment = assignment_map.get(month.id)
        months_data.append({
            "month": month,
            "assignment": assignment,
            "assigned_user": assignment.user if assignment else None
        })
    
    return templates.TemplateResponse(
        "admin_months.html",
        {
            "request": request,
            "user": current_user,
            "months_data": months_data,
            "users": users
        }
    )

@router.post("/admin/assign-month")
async def assign_month(
    month_id: int = Form(...),
    user_id: int = Form(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # Check if month is already assigned
    existing = db.query(UserMonthAssignment).filter(
        UserMonthAssignment.month_id == month_id
    ).first()
    
    if existing:
        # Update existing assignment
        existing.user_id = user_id
        existing.assigned_by = current_user.id
        existing.assigned_at = datetime.utcnow()
    else:
        # Create new assignment
        assignment = UserMonthAssignment(
            user_id=user_id,
            month_id=month_id,
            assigned_by=current_user.id
        )
        db.add(assignment)
    
    db.commit()
    return RedirectResponse(url="/admin/months", status_code=302)

@router.get("/admin/payments", response_class=HTMLResponse)
async def admin_payments(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    payments = db.query(InstallmentPayment).order_by(InstallmentPayment.paid_at.desc()).all()
    return templates.TemplateResponse(
        "admin_payments.html",
        {"request": request, "user": current_user, "payments": payments}
    )

@router.post("/admin/payments/verify")
async def verify_payment(
    payment_id: int = Form(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    payment = db.query(InstallmentPayment).filter(
        InstallmentPayment.id == payment_id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment.status = "verified"
    payment.verified_by = current_user.id
    db.commit()
    
    return RedirectResponse(url="/admin/payments", status_code=302)

