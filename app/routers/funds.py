from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.auth import get_current_user, get_current_admin_user
from app.models import User, Fund, Month, UserMonthAssignment, InstallmentPayment
from app.helpers import get_user_display_info
from app.audit import log_action

router = APIRouter()
import os
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
templates = Jinja2Templates(directory=template_dir)

# Add IST timezone filter to templates
from app.timezone_utils import utc_to_ist
import pytz
IST = pytz.timezone('Asia/Kolkata')

def format_ist(dt, format_str='%Y-%m-%d %H:%M:%S'):
    """Jinja2 filter to format datetime in IST"""
    if dt is None:
        return None
    ist_dt = utc_to_ist(dt)
    return ist_dt.strftime(format_str)

templates.env.filters['ist'] = format_ist

@router.get("/funds", response_class=HTMLResponse)
async def funds_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get funds - admin sees all (including archived), users see only active funds they're members of, guests see guest-visible funds
    if current_user.role == "admin":
        # Admin sees all funds including archived, but not deleted
        funds = db.query(Fund).filter(Fund.is_deleted == False).all()
    elif current_user.role == "guest":
        # Guest users see only guest-visible, active (non-archived, non-deleted) funds
        funds = db.query(Fund).filter(
            Fund.guest_visible == True,
            Fund.is_archived == False,
            Fund.is_deleted == False
        ).all()
    else:
        # Regular users see only active (non-archived, non-deleted) funds they're members of
        from app.models import fund_members
        from sqlalchemy import select
        funds = db.query(Fund).join(
            fund_members, Fund.id == fund_members.c.fund_id
        ).filter(
            fund_members.c.user_id == current_user.id,
            Fund.is_archived == False,
            Fund.is_deleted == False
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
    db.refresh(fund)
    
    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action_type="FUND_CREATED",
        action_description=f"Fund created: {name} - Total Amount: ₹{total_amount:,.2f}, Months: {number_of_months}",
        request=request,
        fund_id=fund.id,
        details={
            "fund_id": fund.id,
            "name": name,
            "description": description,
            "total_amount": float(total_amount),
            "number_of_months": number_of_months,
            "months_count": len(months_list)
        }
    )
    
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
    # Guest users cannot join funds
    if current_user.role == "guest":
        raise HTTPException(status_code=403, detail="Guest users cannot join funds")
    
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    # Check if fund is archived or deleted - non-admin users cannot join
    if current_user.role != "admin":
        if fund.is_deleted or fund.is_archived:
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
    
    # Check if fund is archived or deleted - non-admin users cannot access
    if current_user.role != "admin":
        if fund.is_deleted or fund.is_archived:
            raise HTTPException(status_code=404, detail="Fund not found")
    
    # Check access
    if current_user.role == "guest":
        # Guest users can only access guest-visible funds
        if not fund.guest_visible:
            raise HTTPException(status_code=403, detail="You don't have access to this fund")
    elif current_user.role != "admin" and current_user not in fund.members:
        raise HTTPException(status_code=403, detail="You don't have access to this fund")
    
    return {
        "id": fund.id,
        "name": fund.name,
        "description": fund.description,
        "total_amount": fund.total_amount,
        "number_of_months": fund.number_of_months
    }

@router.post("/api/funds/{fund_id}/toggle-guest-visible")
async def toggle_guest_visible(
    fund_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Toggle guest visibility for a fund"""
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    fund.guest_visible = not fund.guest_visible
    db.commit()
    
    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action_type="FUND_GUEST_VISIBILITY_TOGGLED",
        action_description=f"Guest visibility {'enabled' if fund.guest_visible else 'disabled'} for fund: {fund.name}",
        request=request,
        fund_id=fund_id,
        details={
            "fund_id": fund_id,
            "fund_name": fund.name,
            "guest_visible": fund.guest_visible
        }
    )
    
    return {"message": f"Guest visibility {'enabled' if fund.guest_visible else 'disabled'}", "guest_visible": fund.guest_visible}

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

@router.post("/funds/{fund_id}/archive")
async def archive_fund(
    fund_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    fund = db.query(Fund).filter(Fund.id == fund_id, Fund.is_deleted == False).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    fund.is_archived = True
    db.commit()
    
    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action_type="FUND_ARCHIVED",
        action_description=f"Fund archived: {fund.name}",
        request=request,
        fund_id=fund_id,
        details={
            "fund_id": fund_id,
            "name": fund.name,
            "total_amount": float(fund.total_amount) if fund.total_amount else None
        }
    )
    
    # Return JSON for AJAX or redirect for form submission
    if request.headers.get("Accept") == "application/json" or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"message": "Fund archived successfully", "fund_id": fund_id}
    return RedirectResponse(url="/funds", status_code=302)

@router.post("/funds/{fund_id}/unarchive")
async def unarchive_fund(
    fund_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    fund = db.query(Fund).filter(Fund.id == fund_id, Fund.is_deleted == False).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    fund.is_archived = False
    db.commit()
    
    # Return JSON for AJAX or redirect for form submission
    if request.headers.get("Accept") == "application/json" or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"message": "Fund unarchived successfully", "fund_id": fund_id}
    return RedirectResponse(url="/funds", status_code=302)

@router.post("/funds/{fund_id}/delete")
async def delete_fund(
    fund_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    fund = db.query(Fund).filter(Fund.id == fund_id, Fund.is_deleted == False).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    # Delete all associated data
    # 1. Delete all installment payments for months in this fund
    from app.models import MonthlyPaymentReceived
    months = db.query(Month).filter(Month.fund_id == fund_id).all()
    month_ids = [m.id for m in months]
    
    if month_ids:
        # Delete installment payments
        db.query(InstallmentPayment).filter(InstallmentPayment.month_id.in_(month_ids)).delete(synchronize_session=False)
        # Delete monthly payments received
        db.query(MonthlyPaymentReceived).filter(MonthlyPaymentReceived.month_id.in_(month_ids)).delete(synchronize_session=False)
        # Delete user month assignments
        db.query(UserMonthAssignment).filter(UserMonthAssignment.month_id.in_(month_ids)).delete(synchronize_session=False)
        # Delete months (cascade should handle this, but being explicit)
        db.query(Month).filter(Month.fund_id == fund_id).delete(synchronize_session=False)
    
    # Delete fund members associations
    from app.models import fund_members
    db.execute(fund_members.delete().where(fund_members.c.fund_id == fund_id))
    
    # Mark fund as deleted
    # Get fund details before deleting
    fund_name = fund.name
    fund_total = fund.total_amount
    
    fund.is_deleted = True
    db.commit()
    
    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action_type="FUND_DELETED",
        action_description=f"Fund deleted: {fund_name}",
        request=request,
        fund_id=fund_id,
        details={
            "fund_id": fund_id,
            "name": fund_name,
            "total_amount": float(fund_total) if fund_total else None,
            "number_of_months": fund.number_of_months
        }
    )
    
    # Return JSON for AJAX or redirect for form submission
    if request.headers.get("Accept") == "application/json" or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"message": "Fund deleted successfully", "fund_id": fund_id}
    return RedirectResponse(url="/funds", status_code=302)

