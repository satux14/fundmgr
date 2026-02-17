from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, get_current_admin_user, get_password_hash, verify_password
from app.models import User, Month, UserMonthAssignment, InstallmentPayment, Fund
from app.schemas import MonthWithStatus
from app.dependencies import get_current_fund
from app.helpers import get_user_display_info
from app.audit import log_action
from datetime import datetime
import pytz

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

@router.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get fund from query param first (user clicked a fund), then cookie (last viewed), or redirect to funds page
    # Prioritize query parameter over cookie to ensure clicking a fund card loads that fund
    fund_id = request.query_params.get("fund_id") or request.cookies.get("current_fund_id")
    
    if not fund_id:
        # Redirect to funds page if no fund selected
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/funds", status_code=302)
    
    try:
        fund_id = int(fund_id)
    except ValueError:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/funds", status_code=302)
    
    current_fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not current_fund:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/funds", status_code=302)
    
    # Check if fund is archived or deleted - non-admin users cannot access
    if current_user.role != "admin":
        if current_fund.is_deleted or current_fund.is_archived:
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/funds", status_code=302)
    
    # Check access - guest users can only access guest-visible funds
    if current_user.role == "guest":
        if not current_fund.guest_visible:
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/funds", status_code=302)
    
    # Check access - allow non-members to view but show join option
    # Admin can always access, members can access, non-members can view but need to join
    # We'll show a join button in the template for non-members
    # Guest users cannot join funds
    # Get all months for this fund
    months = db.query(Month).filter(Month.fund_id == current_fund.id).order_by(Month.month_number).all()
    
    # Get month IDs for this fund
    fund_month_ids = [m.id for m in months]
    
    # Get all assignments for months in this fund
    assignments = db.query(UserMonthAssignment).filter(
        UserMonthAssignment.month_id.in_(fund_month_ids)
    ).all()
    assignment_map = {a.month_id: a for a in assignments}
    
    # Get all users who are members of this fund
    # Include all members regardless of role (but filter out admin for display purposes)
    all_users = [u for u in current_fund.members if u.role == "user"]
    
    # Also check if there are users assigned to months who might not be in fund.members yet
    # Get all unique users who have assignments in this fund
    assigned_user_ids = set()
    for assignment in assignments:
        if assignment.user_id:
            assigned_user_ids.add(assignment.user_id)
    
    # Get all assigned users
    if assigned_user_ids:
        assigned_users = db.query(User).filter(
            User.id.in_(assigned_user_ids),
            User.role == "user"
        ).all()
        # Add any assigned users who aren't already in all_users
        existing_user_ids = {u.id for u in all_users}
        for assigned_user in assigned_users:
            if assigned_user.id not in existing_user_ids:
                all_users.append(assigned_user)
    
    # Get user's assigned month - MUST be in the current fund
    user_assignment = db.query(UserMonthAssignment).join(Month).filter(
        UserMonthAssignment.user_id == current_user.id,
        Month.fund_id == current_fund.id
    ).first()
    
    assigned_month_id = user_assignment.month_id if user_assignment else None
    
    # Get all installment payments for this user
    from app.models import MonthlyPaymentReceived
    installment_payments = db.query(InstallmentPayment).filter(
        InstallmentPayment.user_id == current_user.id
    ).all()
    
    installment_payment_map = {p.month_id: p for p in installment_payments}
    
    # Get all monthly payments received (for months assigned to this user)
    monthly_payments_received = db.query(MonthlyPaymentReceived).join(Month).filter(
        Month.fund_id == current_fund.id,
        MonthlyPaymentReceived.user_id == current_user.id
    ).all()
    
    monthly_payment_map = {p.month_id: p for p in monthly_payments_received}
    
    # Get all verified installment payments for this fund (to count how many users paid)
    from sqlalchemy.orm import joinedload
    all_verified_installments = db.query(InstallmentPayment).join(Month).options(
        joinedload(InstallmentPayment.month)
    ).filter(
        Month.fund_id == current_fund.id,
        InstallmentPayment.status == "verified"
    ).all()
    
    # Calculate total paid installments (sum of all verified installment amounts)
    total_paid_installments = sum(
        payment.month.installment_amount for payment in all_verified_installments
    )
    
    # Create a map: month_id -> list of all payments (count all payments, not unique users)
    verified_installments_map = {}
    for payment in all_verified_installments:
        if payment.month_id not in verified_installments_map:
            verified_installments_map[payment.month_id] = []
        verified_installments_map[payment.month_id].append(payment.user_id)
    
    # Get total number of months in the fund (for display: X/10 means X payments out of 10 total months)
    # This represents the total number of installments that should be paid (one per month)
    total_users = len(months)
    
    # Build month data with status
    months_data = []
    for month in months:
        is_taken = month.id == assigned_month_id
        installment_payment = installment_payment_map.get(month.id)
        monthly_payment = monthly_payment_map.get(month.id)
        assignment = assignment_map.get(month.id)
        assigned_user = assignment.user if assignment else None
        
        # Count verified installment payments for this month (count all payments, not unique users)
        verified_count = len(verified_installments_map.get(month.id, []))
        
        # For "Payment Received Status", we need to show how many installments have been paid
        # out of the total number of fund members (since each member should pay for each month)
        # However, if the user wants to see it as total months, we can use len(months) instead
        # But logically, it should be total_users (number of members who should pay)
        # Let's use total_users as it represents the number of people who should pay each month
        
        # Get display info for assigned user
        assigned_user_display = None
        if assigned_user:
            assigned_user_display = get_user_display_info(assigned_user, current_user)
        
        months_data.append({
            "id": month.id,
            "month_name": month.month_name,
            "month_number": month.month_number,
            "installment_amount": month.installment_amount,
            "payment_amount": month.payment_amount,
            "is_taken": is_taken,
            "installment_payment_status": installment_payment.status if installment_payment else None,
            "installment_payment_id": installment_payment.id if installment_payment else None,
            "monthly_payment_status": monthly_payment.status if monthly_payment else None,
            "monthly_payment_id": monthly_payment.id if monthly_payment else None,
            "assigned_user_id": assigned_user.id if assigned_user else None,
            "assigned_user_name": assigned_user_display["display_name"] if assigned_user_display else None,
            "assigned_user_display": assigned_user_display,
            "verified_installments_count": verified_count,
            "total_users": total_users  # This is the number of fund members who should pay for each month
        })
    
    # Calculate total installment amount for the table footer
    total_installment_amount = sum(month.installment_amount for month in months)
    
    # Get current month in Kolkata timezone
    kolkata_tz = pytz.timezone('Asia/Kolkata')
    current_datetime = datetime.now(kolkata_tz)
    current_month_short = current_datetime.strftime('%b')  # Jan, Feb, etc.
    
    # Mark current month in months_data
    for month_data in months_data:
        if month_data["month_name"] == current_month_short:
            month_data["is_current_month"] = True
        else:
            month_data["is_current_month"] = False
    
    # Check if current user is a member of the fund
    is_member = current_user in current_fund.members
    
    # Set cookie for fund_id and return response
    response = templates.TemplateResponse(
        "user_dashboard.html",
        {
            "request": request,
            "user": current_user,
            "fund": current_fund,
            "months": months_data,
            "all_users": all_users,
            "total_paid_installments": total_paid_installments,
            "total_installment_amount": total_installment_amount,
            "is_member": is_member
        }
    )
    response.set_cookie(key="current_fund_id", value=str(current_fund.id), httponly=True)
    return response

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
    # Get form data
    form_data = await request.form()
    month_id = int(form_data.get("month_id", 0))
    payment_date_str = form_data.get("payment_date", "")
    transaction_id = form_data.get("transaction_id", "").strip()
    transaction_type = form_data.get("transaction_type", "").strip()
    username = form_data.get("username", "").strip()
    
    # Determine which user this payment is for
    # If admin provided username, use that user; otherwise use current_user
    if current_user.role == "admin":
        if not username:
            raise HTTPException(status_code=400, detail="Username is required for admin")
        target_user = db.query(User).filter(User.username == username).first()
        if not target_user:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    else:
        # Regular user - use their own account
        target_user = current_user
    
    # Validate payment_date is provided (mandatory)
    if not payment_date_str:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment date is required")
    
    # Parse payment date
    try:
        from datetime import datetime
        payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d")
    except ValueError:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment date format")
    
    # Get month to get installment amount
    month = db.query(Month).filter(Month.id == month_id).first()
    if not month:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Month not found")
    
    # Check if payment already exists
    existing = db.query(InstallmentPayment).filter(
        InstallmentPayment.user_id == target_user.id,
        InstallmentPayment.month_id == month_id
    ).first()
    
    if existing:
        # If rejected, allow re-submission by changing status back to pending
        if existing.status == "rejected":
            existing.status = "pending"
            existing.paid_at = datetime.utcnow()
            existing.payment_date = payment_date
            existing.transaction_id = transaction_id if transaction_id else None
            existing.transaction_type = transaction_type if transaction_type else None
            db.commit()
            
            # Log action
            log_action(
                db=db,
                user_id=current_user.id,
                action_type="INSTALLMENT_PAID",
                action_description=f"Payment re-submitted for {target_user.username} - Month: {month.month_name}, Amount: ₹{month.installment_amount:,.2f}",
                request=request,
                fund_id=month.fund_id,
                details={
                    "payment_id": existing.id,
                    "user_id": target_user.id,
                    "username": target_user.username,
                    "month_id": month_id,
                    "month_name": month.month_name,
                    "amount": float(month.installment_amount),
                    "payment_date": payment_date_str,
                    "transaction_id": transaction_id,
                    "transaction_type": transaction_type,
                    "marked_by_admin": current_user.role == "admin"
                }
            )
            
            return {"message": "Payment re-submitted successfully", "payment_id": existing.id}
        # If existing payment is pending or verified, allow creating a new payment entry
        # This allows multiple payments to be submitted for the same user/month
    
    # Create new payment
    payment = InstallmentPayment(
        user_id=target_user.id,
        month_id=month_id,
        marked_by=current_user.id,
        status="pending",
        payment_date=payment_date,
        transaction_id=transaction_id if transaction_id else None,
        transaction_type=transaction_type if transaction_type else None
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action_type="INSTALLMENT_PAID",
        action_description=f"Payment marked for {target_user.username} - Month: {month.month_name}, Amount: ₹{month.installment_amount:,.2f}",
        request=request,
        fund_id=month.fund_id,
        details={
            "payment_id": payment.id,
            "user_id": target_user.id,
            "username": target_user.username,
            "month_id": month_id,
            "month_name": month.month_name,
            "amount": float(month.installment_amount),
            "payment_date": payment_date_str,
            "transaction_id": transaction_id,
            "transaction_type": transaction_type,
            "marked_by_admin": current_user.role == "admin"
        }
    )
    
    return {"message": "Payment marked successfully", "payment_id": payment.id}

@router.post("/api/user/monthly-payment/mark-received")
async def mark_monthly_payment_received_user(
    request: Request,
    month_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """User can mark their monthly payment as received"""
    from app.models import MonthlyPaymentReceived
    
    # Get the month and verify it's assigned to this user
    month = db.query(Month).filter(Month.id == month_id).first()
    if not month:
        raise HTTPException(status_code=404, detail="Month not found")
    
    # Verify this month is assigned to the current user
    assignment = db.query(UserMonthAssignment).filter(
        UserMonthAssignment.month_id == month_id,
        UserMonthAssignment.user_id == current_user.id
    ).first()
    
    if not assignment:
        raise HTTPException(status_code=403, detail="This month is not assigned to you")
    
    # Check if already exists
    existing = db.query(MonthlyPaymentReceived).filter(
        MonthlyPaymentReceived.month_id == month_id
    ).first()
    
    if existing:
        # Update existing - only if status is not verified (allow re-submission if rejected)
        if existing.status != "verified":
            existing.status = "pending"
            existing.received_at = datetime.utcnow()
            existing.marked_by = current_user.id
            db.commit()
            return {"message": "Payment receipt marked successfully", "payment_id": existing.id}
        return {"message": "Payment already marked as received and verified", "payment_id": existing.id}
    
    # Create new
    monthly_payment = MonthlyPaymentReceived(
        month_id=month_id,
        user_id=current_user.id,
        amount=month.payment_amount,
        marked_by=current_user.id,
        status="pending"
    )
    db.add(monthly_payment)
    db.commit()
    db.refresh(monthly_payment)
    
    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action_type="MONTHLY_PAYMENT_MARKED",
        action_description=f"Monthly payment marked as received - Month: {month.month_name}, Amount: ₹{month.payment_amount:,.2f}",
        request=request,
        fund_id=month.fund_id,
        details={
            "payment_id": monthly_payment.id,
            "month_id": month_id,
            "month_name": month.month_name,
            "amount": float(month.payment_amount),
            "user_id": current_user.id,
            "username": current_user.username
        }
    )
    
    return {"message": "Payment receipt marked successfully", "payment_id": monthly_payment.id}

# New endpoints for editing
from pydantic import BaseModel
from typing import Optional

class UpdateAmountRequest(BaseModel):
    amount: float

class AssignUserRequest(BaseModel):
    username: str

@router.put("/api/dashboard/month/{month_id}/installment")
async def update_installment(
    request: Request,
    month_id: int,
    request_data: UpdateAmountRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    month = db.query(Month).filter(Month.id == month_id).first()
    if not month:
        raise HTTPException(status_code=404, detail="Month not found")
    
    old_amount = month.installment_amount
    month.installment_amount = request_data.amount
    db.commit()
    
    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action_type="INSTALLMENT_AMOUNT_UPDATED",
        action_description=f"Installment amount updated for {month.month_name} - From ₹{old_amount:,.2f} to ₹{request_data.amount:,.2f}",
        request=request,
        fund_id=month.fund_id,
        details={
            "month_id": month_id,
            "month_name": month.month_name,
            "old_amount": float(old_amount),
            "new_amount": float(request_data.amount)
        }
    )
    
    return {"message": "Installment amount updated", "amount": request_data.amount}

@router.put("/api/dashboard/month/{month_id}/payment")
async def update_payment(
    request: Request,
    month_id: int,
    request_data: UpdateAmountRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    month = db.query(Month).filter(Month.id == month_id).first()
    if not month:
        raise HTTPException(status_code=404, detail="Month not found")
    
    old_amount = month.payment_amount
    month.payment_amount = request_data.amount
    db.commit()
    
    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action_type="PAYMENT_AMOUNT_UPDATED",
        action_description=f"Payment amount updated for {month.month_name} - From ₹{old_amount:,.2f} to ₹{request_data.amount:,.2f}",
        request=request,
        fund_id=month.fund_id,
        details={
            "month_id": month_id,
            "month_name": month.month_name,
            "old_amount": float(old_amount),
            "new_amount": float(request_data.amount)
        }
    )
    
    return {"message": "Payment amount updated", "amount": request_data.amount}

@router.put("/api/dashboard/month/{month_id}/assign")
async def assign_month_to_user(
    request: Request,
    month_id: int,
    request_data: AssignUserRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # Verify month exists
    month = db.query(Month).filter(Month.id == month_id).first()
    if not month:
        raise HTTPException(status_code=404, detail="Month not found")
    
    username = request_data.username.strip()
    
    # If empty username, remove assignment
    if not username:
        existing = db.query(UserMonthAssignment).filter(
            UserMonthAssignment.month_id == month_id
        ).first()
        if existing:
            old_user_id = existing.user_id
            db.delete(existing)
            db.commit()
            
            # Log action
            log_action(
                db=db,
                user_id=current_user.id,
                action_type="MONTH_ASSIGNED",
                action_description=f"Month {month.month_name} assignment removed",
                request=request,
                fund_id=month.fund_id,
                details={
                    "month_id": month_id,
                    "month_name": month.month_name,
                    "old_user_id": old_user_id,
                    "action": "removed"
                }
            )
        return {"message": "Assignment removed", "user_id": None, "username": None}
    
    # Verify user exists
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found in system")
    
    # Check if month is already assigned
    existing = db.query(UserMonthAssignment).filter(
        UserMonthAssignment.month_id == month_id
    ).first()
    
    old_user_id = None
    if existing:
        old_user_id = existing.user_id
        # Update existing assignment
        existing.user_id = user.id
        existing.assigned_by = current_user.id
        existing.assigned_at = datetime.utcnow()
    else:
        # Create new assignment
        assignment = UserMonthAssignment(
            user_id=user.id,
            month_id=month_id,
            assigned_by=current_user.id
        )
        db.add(assignment)
    
    db.commit()
    
    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action_type="MONTH_ASSIGNED",
        action_description=f"Month {month.month_name} assigned to {user.full_name} ({user.username})",
        request=request,
        fund_id=month.fund_id,
        details={
            "month_id": month_id,
            "month_name": month.month_name,
            "user_id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "old_user_id": old_user_id,
            "is_update": existing is not None
        }
    )
    
    return {"message": f"Month assigned to {user.full_name}", "user_id": user.id, "username": user.username}

@router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Page for users to change their own password"""
    return templates.TemplateResponse(
        "change_password.html",
        {
            "request": request,
            "user": current_user
        }
    )

@router.post("/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allow users to change their own password"""
    from fastapi.responses import RedirectResponse
    
    # Verify current password
    if not verify_password(current_password, current_user.password_hash):
        return templates.TemplateResponse(
            "change_password.html",
            {
                "request": request,
                "user": current_user,
                "error": "Current password is incorrect"
            },
            status_code=400
        )
    
    # Check if new password matches confirmation
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "change_password.html",
            {
                "request": request,
                "user": current_user,
                "error": "New password and confirmation do not match"
            },
            status_code=400
        )
    
    # Check password length
    if len(new_password) < 3:
        return templates.TemplateResponse(
            "change_password.html",
            {
                "request": request,
                "user": current_user,
                "error": "Password must be at least 3 characters long"
            },
            status_code=400
        )
    
    # Update password
    current_user.password_hash = get_password_hash(new_password)
    db.commit()
    
    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action_type="PASSWORD_CHANGED",
        action_description=f"User {current_user.username} changed their password",
        request=request
    )
    
    return templates.TemplateResponse(
        "change_password.html",
        {
            "request": request,
            "user": current_user,
            "success": "Password changed successfully!"
        }
    )
