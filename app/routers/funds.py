from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.auth import get_current_user, get_current_admin_user
from app.models import User, Fund, Month, UserMonthAssignment, InstallmentPayment
from app.helpers import get_user_display_info

router = APIRouter()
import os
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
templates = Jinja2Templates(directory=template_dir)

@router.get("/funds", response_class=HTMLResponse)
async def funds_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get funds - admin sees all, users see only their funds
    if current_user.role == "admin":
        funds = db.query(Fund).all()
    else:
        # Query funds where user is a member using the association table
        from app.models import fund_members
        from sqlalchemy import select
        funds = db.query(Fund).join(
            fund_members, Fund.id == fund_members.c.fund_id
        ).filter(
            fund_members.c.user_id == current_user.id
        ).all()
    
    # Get statistics for each fund
    funds_data = []
    for fund in funds:
        months_count = db.query(Month).filter(Month.fund_id == fund.id).count()
        assignments_count = db.query(UserMonthAssignment).join(Month).filter(
            Month.fund_id == fund.id
        ).count()
        
        # Calculate unique members - users who have assignments in this fund
        # Get all assignments for this fund and count unique user_ids
        assignments = db.query(UserMonthAssignment).join(Month).filter(
            Month.fund_id == fund.id
        ).all()
        unique_user_ids = set(assignment.user_id for assignment in assignments if assignment.user_id)
        unique_members_count = len(unique_user_ids)
        
        fund_data = {
            "fund": fund,
            "months_count": months_count,
            "assignments_count": assignments_count,
            "unique_members_count": unique_members_count
        }
        
        # Add admin-specific statistics
        if current_user.role == "admin":
            verified_payments = db.query(InstallmentPayment).join(Month).filter(
                Month.fund_id == fund.id,
                InstallmentPayment.status == "verified"
            ).count()
            fund_data["verified_payments"] = verified_payments
            
            # Count pending payments (both installment and monthly payments)
            pending_installments = db.query(InstallmentPayment).join(Month).filter(
                Month.fund_id == fund.id,
                InstallmentPayment.status == "pending"
            ).count()
            
            from app.models import MonthlyPaymentReceived
            pending_monthly = db.query(MonthlyPaymentReceived).join(Month).filter(
                Month.fund_id == fund.id,
                MonthlyPaymentReceived.status == "pending"
            ).count()
            
            pending_payments_count = pending_installments + pending_monthly
            fund_data["pending_payments_count"] = pending_payments_count
        
        funds_data.append(fund_data)
    
    # Get overall statistics for admin
    total_users = None
    total_funds = None
    if current_user.role == "admin":
        total_users = db.query(User).count()
        total_funds = len(funds)
    
    return templates.TemplateResponse(
        "funds_dashboard.html",
        {
            "request": request,
            "user": current_user,
            "funds_data": funds_data,
            "total_users": total_users,
            "total_funds": total_funds
        }
    )

@router.get("/funds/create", response_class=HTMLResponse)
async def create_fund_page(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    users = db.query(User).filter(User.role == "user").all()
    return templates.TemplateResponse(
        "create_fund.html",
        {"request": request, "user": current_user, "users": users}
    )

@router.post("/funds/create")
async def create_fund(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    total_amount: float = Form(...),
    number_of_months: int = Form(1),
    months_data: str = Form(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    import json
    from datetime import datetime
    
    # Parse months data from JSON string
    try:
        months_list = json.loads(months_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid months data format")
    
    if not months_list or len(months_list) == 0:
        raise HTTPException(status_code=400, detail="At least one month is required")
    
    # Update number_of_months from actual months count
    number_of_months = len(months_list)
    
    # Create fund
    fund = Fund(
        name=name,
        description=description,
        total_amount=total_amount,
        number_of_months=number_of_months,
        created_by=current_user.id
    )
    db.add(fund)
    db.flush()  # Get the fund ID
    
    # Add admin as member
    if current_user not in fund.members:
        fund.members.append(current_user)
    
    # Create all months
    current_year = datetime.now().year
    for index, month_data in enumerate(months_list, start=1):
        month = Month(
            fund_id=fund.id,
            month_name=month_data.get("month_name", "").strip(),
            month_number=index,
            installment_amount=float(month_data.get("installment_amount", 0)),
            payment_amount=float(month_data.get("payment_amount", 0)),
            year=current_year
        )
        db.add(month)
    
    db.commit()
    
    return RedirectResponse(url=f"/dashboard?fund_id={fund.id}", status_code=302)

@router.get("/funds/{fund_id}", response_class=HTMLResponse)
async def fund_detail(
    fund_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Redirect to dashboard - consolidated view
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/dashboard?fund_id={fund_id}", status_code=302)
    from sqlalchemy.orm import joinedload
    from app.models import MonthlyPaymentReceived
    
    fund = db.query(Fund).options(
        joinedload(Fund.months).joinedload(Month.assignments).joinedload(UserMonthAssignment.user),
        joinedload(Fund.months).joinedload(Month.payment_received)
    ).filter(Fund.id == fund_id).first()
    
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    # Check access - admin can see all, users only their funds
    if current_user.role != "admin" and current_user not in fund.members:
        raise HTTPException(status_code=403, detail="You don't have access to this fund")
    
    # Get all fund members (users only, not admin)
    fund_members = [u for u in fund.members if u.role == "user"]
    
    # Get all installment payments for this fund
    all_installment_payments = db.query(InstallmentPayment).join(Month).filter(
        Month.fund_id == fund_id,
        InstallmentPayment.status == "verified"
    ).all()
    
    # Get all monthly payments received
    all_monthly_payments = db.query(MonthlyPaymentReceived).join(Month).filter(
        Month.fund_id == fund_id
    ).all()
    
    # Create maps for quick lookup
    installment_payment_map = {(p.month_id, p.user_id): p for p in all_installment_payments}
    monthly_payment_map = {p.month_id: p for p in all_monthly_payments}
    
    # Total installments expected = number of months (each month requires installments from all members)
    # But for display, we show how many installments have been paid out of total months
    total_installments = len(fund.months)
    
    # Build month data with payment statistics
    months_data = []
    for month in sorted(fund.months, key=lambda m: m.month_number):
        assignment = month.assignments[0] if month.assignments else None
        
        # Count verified installment payments for this month
        # Count how many fund members have paid their installment for this specific month
        verified_payments_count = sum(
            1 for member in fund_members 
            if (month.id, member.id) in installment_payment_map
        )
        
        # For display: show how many installments paid out of total months (installments)
        # This represents the total number of installments that should be paid across all months
        
        # Get monthly payment received status
        monthly_payment = monthly_payment_map.get(month.id)
        monthly_payment_status = monthly_payment.status if monthly_payment else None
        
        # Get display info for assigned user
        assigned_user_display = None
        if assignment and assignment.user:
            assigned_user_display = get_user_display_info(assignment.user, current_user)
        
        months_data.append({
            "month": month,
            "assignment": assignment,
            "assigned_user": assignment.user if assignment else None,
            "assigned_user_id": assignment.user.id if assignment and assignment.user else None,
            "assigned_user_display": assigned_user_display,
            "verified_installments": verified_payments_count,
            "total_users": total_installments,  # Use total months (installments) instead of unique users
            "monthly_payment": monthly_payment,
            "monthly_payment_status": monthly_payment_status
        })
    
    # Store fund_id in session/cookie for subsequent requests
    response = templates.TemplateResponse(
        "fund_detail.html",
        {
            "request": request,
            "user": current_user,
            "fund": fund,
            "months_data": months_data
        }
    )
    response.set_cookie(key="current_fund_id", value=str(fund_id), httponly=True)
    return response

@router.post("/funds/{fund_id}/join")
async def join_fund(
    fund_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allow users to join a fund"""
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    # Admin can't join (they're already members or can access all)
    if current_user.role == "admin":
        return RedirectResponse(url=f"/dashboard?fund_id={fund_id}", status_code=302)
    
    # Check if user is already a member
    if current_user in fund.members:
        return RedirectResponse(url=f"/dashboard?fund_id={fund_id}", status_code=302)
    
    # Add user to fund
    fund.members.append(current_user)
    db.commit()
    
    return RedirectResponse(url=f"/dashboard?fund_id={fund_id}", status_code=302)

@router.get("/api/funds/{fund_id}")
async def get_fund(
    fund_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    # Check access
    if current_user.role != "admin" and current_user not in fund.members:
        raise HTTPException(status_code=403, detail="You don't have access to this fund")
    
    return {
        "id": fund.id,
        "name": fund.name,
        "description": fund.description,
        "total_amount": fund.total_amount,
        "number_of_months": fund.number_of_months
    }

@router.put("/api/funds/{fund_id}")
async def update_fund(
    fund_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    data = await request.json()
    fund.name = data.get("name", fund.name)
    fund.description = data.get("description", fund.description)
    
    db.commit()
    return {"message": "Fund updated successfully"}

