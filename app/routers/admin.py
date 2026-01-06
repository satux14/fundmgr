from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from app.database import get_db
from app.auth import get_current_admin_user, get_password_hash, verify_password
from app.models import User, Month, InstallmentPayment, Fund, MonthlyPaymentReceived
from app.models import UserMonthAssignment as UMA  # Import with alias to avoid local variable issues
from app.schemas import UserCreate, UserResponse
from app.dependencies import get_current_fund, get_optional_fund
from app.helpers import get_user_display_info
from typing import Optional

router = APIRouter()
logger = logging.getLogger(__name__)
import os
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
templates = Jinja2Templates(directory=template_dir)

@router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # Redirect admin dashboard to /funds (consolidated dashboard)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/funds", status_code=302)

@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # Eager load funds relationship for each user
    from sqlalchemy.orm import joinedload
    users = db.query(User).options(joinedload(User.funds)).all()
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
    
    # Generate customer_id if not provided (for new users)
    # Get the highest customer_id number and increment
    last_customer = db.query(User).filter(User.customer_id.isnot(None)).order_by(User.customer_id.desc()).first()
    if last_customer and last_customer.customer_id:
        try:
            last_num = int(last_customer.customer_id.replace('C', ''))
            new_customer_id = f"C{last_num + 1:03d}"
        except:
            new_customer_id = f"C{db.query(User).count() + 1:03d}"
    else:
        new_customer_id = f"C{db.query(User).count() + 1:03d}"
    
    # Create user
    new_user = User(
        username=username,
        password_hash=get_password_hash(password),
        full_name=full_name,
        customer_id=new_customer_id,
        role=role
    )
    db.add(new_user)
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=302)

@router.post("/admin/users/update-alias")
async def update_user_alias(
    request: Request,
    user_id: int = Form(...),
    alias: str = Form(""),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.alias = alias.strip() if alias else None
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=302)

@router.post("/admin/users/update-customer-id")
async def update_user_customer_id(
    request: Request,
    user_id: int = Form(...),
    customer_id: str = Form(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    customer_id = customer_id.strip()
    # Check if customer_id is already taken by another user
    existing = db.query(User).filter(User.customer_id == customer_id, User.id != user_id).first()
    if existing:
        return templates.TemplateResponse(
            "admin_users.html",
            {
                "request": request,
                "user": current_user,
                "users": db.query(User).all(),
                "error": f"Customer ID '{customer_id}' is already taken by another user"
            },
            status_code=400
        )
    
    user.customer_id = customer_id
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=302)

@router.post("/admin/users/reset-password")
async def admin_reset_password(
    request: Request,
    user_id: int = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Admin can reset any user's password"""
    # Find the user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if passwords match
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "admin_users.html",
            {
                "request": request,
                "user": current_user,
                "users": db.query(User).all(),
                "error": "New password and confirmation do not match"
            },
            status_code=400
        )
    
    # Check password length
    if len(new_password) < 3:
        return templates.TemplateResponse(
            "admin_users.html",
            {
                "request": request,
                "user": current_user,
                "users": db.query(User).all(),
                "error": "Password must be at least 3 characters long"
            },
            status_code=400
        )
    
    # Update password
    user.password_hash = get_password_hash(new_password)
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=302)

@router.get("/admin/months", response_class=HTMLResponse)
async def admin_months(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    current_fund: Optional[Fund] = Depends(get_optional_fund),
    db: Session = Depends(get_db)
):
    
    logger.info(f"=== admin_months called ===")
    logger.info(f"admin_months: URL path={request.url.path}")
    logger.info(f"admin_months: Full URL={request.url}")
    logger.info(f"admin_months: query_params={dict(request.query_params)}")
    logger.info(f"admin_months: cookies={dict(request.cookies)}")
    
    # DIRECT CHECK: Get fund_id from query param directly to verify
    direct_fund_id_from_query = request.query_params.get("fund_id")
    direct_fund_id_from_cookie = request.cookies.get("current_fund_id")
    logger.info(f"admin_months: DIRECT CHECK - query fund_id={direct_fund_id_from_query}, cookie fund_id={direct_fund_id_from_cookie}")
    
    logger.info(f"admin_months: current_fund from dependency={current_fund.id if current_fund else None} ({current_fund.name if current_fund else 'None'})")
    
    # OVERRIDE: ALWAYS use query param if it exists, regardless of dependency result
    # This ensures the URL query parameter always takes precedence
    if direct_fund_id_from_query:
        try:
            query_fund_id = int(direct_fund_id_from_query)
            query_fund = db.query(Fund).filter(Fund.id == query_fund_id).first()
            if query_fund:
                # Always override with query param fund
                old_fund_info = f"{current_fund.id} ({current_fund.name})" if current_fund else "None"
                current_fund = query_fund
                logger.info(f"admin_months: OVERRIDE - Using query param fund {query_fund_id} ({query_fund.name}) instead of dependency fund {old_fund_info}")
            else:
                logger.info(f"admin_months: Query fund_id {query_fund_id} not found in database, keeping dependency result")
        except (ValueError, TypeError) as e:
            logger.info(f"admin_months: Invalid query fund_id format: {direct_fund_id_from_query}, error: {e}, keeping dependency result")
    else:
        logger.info(f"admin_months: No query param, using dependency result")
    
    # Get all funds for selection
    all_funds = db.query(Fund).all()
    logger.info(f"admin_months: Found {len(all_funds)} funds")
    
    # If no fund selected, show fund selection
    if not current_fund:
        logger.info("admin_months: No fund selected, showing fund selection page")
        return templates.TemplateResponse(
            "admin_months_select.html",
            {
                "request": request,
                "user": current_user,
                "funds": all_funds
            }
        )
    
    logger.info(f"admin_months: FINAL - Using fund ID={current_fund.id}, name={current_fund.name} for template rendering")
    
    # Fund selected, show months for that fund
    months = db.query(Month).filter(Month.fund_id == current_fund.id).order_by(Month.month_number).all()
    logger.info(f"admin_months: DEBUG - About to query UMA, months count: {len(months)}")
    assignments = db.query(UMA).join(Month).filter(
        Month.fund_id == current_fund.id
    ).all()
    logger.info(f"admin_months: DEBUG - Successfully queried assignments, count: {len(assignments)}")
    # Get all users in the system (not just fund members) for assignment
    users = db.query(User).filter(User.role == "user").all()
    
    logger.info(f"admin_months: Found {len(months)} months, {len(assignments)} assignments, {len(users)} users")
    
    assignment_map = {a.month_id: a for a in assignments}
    
    # Get all fund members (users only, not admin)
    # IMPORTANT: Refresh the fund to ensure members relationship is loaded
    db.refresh(current_fund, ['members'])
    fund_members = [u for u in current_fund.members if u.role == "user"]
    
    # Also get users who have assignments in this fund (in case they're not members yet)
    # Query UMA first, then get distinct users to avoid join ambiguity
    month_ids_for_fund = [m.id for m in months]
    logger.info(f"admin_months: DEBUG - Querying assignments_in_fund for {len(month_ids_for_fund)} months")
    assignments_in_fund = db.query(UMA).filter(
        UMA.month_id.in_(month_ids_for_fund)
    ).all()
    logger.info(f"admin_months: DEBUG - Found {len(assignments_in_fund)} assignments_in_fund")
    
    # Get unique user IDs from assignments
    user_ids_with_assignments = set()
    for assignment in assignments_in_fund:
        user_ids_with_assignments.add(assignment.user_id)
    
    # Get users who have assignments but aren't fund members yet
    if user_ids_with_assignments:
        users_with_assignments = db.query(User).filter(
            User.id.in_(list(user_ids_with_assignments)),
            User.role == "user"
        ).all()
    else:
        users_with_assignments = []
    
    # Combine both lists, removing duplicates
    all_tracked_users = {u.id: u for u in fund_members}
    for u in users_with_assignments:
        if u.id not in all_tracked_users:
            all_tracked_users[u.id] = u
            # Add to fund if not already a member
            if u not in current_fund.members:
                current_fund.members.append(u)
                logger.info(f"admin_months: Added user {u.full_name} to fund {current_fund.name} (has assignment)")
    
    fund_members = list(all_tracked_users.values())
    db.commit()  # Commit any new member additions
    
    logger.info(f"admin_months: Found {len(fund_members)} users to track: {[m.full_name for m in fund_members]}")
    
    if len(fund_members) == 0:
        logger.warning(f"admin_months: No fund members found for fund {current_fund.id} ({current_fund.name})")
        logger.warning(f"admin_months: All members: {[m.full_name + ' (' + m.role + ')' for m in current_fund.members]}")
    
    # Get all installment payments for this fund
    all_installment_payments = db.query(InstallmentPayment).join(Month).filter(
        Month.fund_id == current_fund.id
    ).all()
    logger.info(f"admin_months: Found {len(all_installment_payments)} installment payments")
    
    # Create a map: (month_id, user_id) -> payment
    payment_map = {(p.month_id, p.user_id): p for p in all_installment_payments}
    
    months_data = []
    for month in months:
        assignment = assignment_map.get(month.id)
        
        # Get payment status for each fund member for this month
        # IMPORTANT: Show ALL fund members, even if they haven't paid
        # This ensures we always show all users for tracking purposes
        # For a 10-month fund with 10 users, each month should show 10 rows
        member_payments = []
        for member in fund_members:
            payment = payment_map.get((month.id, member.id))
            # Eager load relationships if payment exists
            if payment:
                _ = payment.marked_by_user
                _ = payment.verified_by_user
            # Get display info for the member
            member_display = get_user_display_info(member, current_user)
            member_payments.append({
                "user": member,
                "user_display": member_display,
                "payment": payment,
                "status": payment.status if payment else None
            })
        
        logger.debug(f"admin_months: Month {month.month_name} (ID: {month.id}) - {len(member_payments)} member entries created")
        
        # Get display info for assigned user
        assigned_user_display = None
        if assignment and assignment.user:
            assigned_user_display = get_user_display_info(assignment.user, current_user)
        
        months_data.append({
            "month": month,
            "assignment": assignment,
            "assigned_user": assignment.user if assignment else None,
            "assigned_user_display": assigned_user_display,
            "member_payments": member_payments
        })
    
    # Log summary
    logger.info(f"admin_months: Created months_data with {len(months_data)} months")
    for md in months_data:
        logger.info(f"admin_months: Month {md['month'].month_name} has {len(md['member_payments'])} member payment entries")
    
    # Set cookie for fund_id - always use the current_fund.id (which came from query param if present)
    fund_id_to_set = str(current_fund.id)
    
    # Final verification before rendering
    logger.info(f"admin_months: RENDERING - Passing fund ID={current_fund.id}, name={current_fund.name} to template")
    logger.info(f"admin_months: Template context - current_fund.id={current_fund.id}, current_fund.name={current_fund.name}")
    
    response = templates.TemplateResponse(
        "admin_months.html",
        {
            "request": request,
            "user": current_user,
            "current_fund": current_fund,
            "all_funds": all_funds,
            "months_data": months_data,
            "users": users,
            "fund_members": fund_members
        }
    )
    # Set cookie with the fund_id that was actually used (from query param if present, otherwise cookie)
    response.set_cookie(key="current_fund_id", value=fund_id_to_set, httponly=True, path="/", max_age=86400)
    logger.info(f"admin_months: Setting cookie current_fund_id={fund_id_to_set} for fund {current_fund.name}")
    return response

@router.post("/admin/assign-month")
async def assign_month(
    request: Request,
    month_id: int = Form(...),
    user_id: int = Form(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # Get the month to find its fund_id
    month = db.query(Month).filter(Month.id == month_id).first()
    if not month:
        raise HTTPException(status_code=404, detail="Month not found")
    
    fund_id = month.fund_id
    
    # Check if month is already assigned
    existing = db.query(UMA).filter(
        UMA.month_id == month_id
    ).first()
    
    if user_id:  # Only assign if user_id is provided
        # Get the user being assigned
        assigned_user = db.query(User).filter(User.id == user_id).first()
        if not assigned_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get the fund
        fund = db.query(Fund).filter(Fund.id == fund_id).first()
        if not fund:
            raise HTTPException(status_code=404, detail="Fund not found")
        
        # IMPORTANT: Add user to fund if not already a member
        if assigned_user not in fund.members:
            fund.members.append(assigned_user)
            logger.info(f"assign_month: Added user {assigned_user.full_name} to fund {fund.name}")
        
        if existing:
            # Update existing assignment
            existing.user_id = user_id
            existing.assigned_by = current_user.id
            existing.assigned_at = datetime.utcnow()
        else:
            # Create new assignment
            assignment = UMA(
                user_id=user_id,
                month_id=month_id,
                assigned_by=current_user.id
            )
            db.add(assignment)
    else:
        # Remove assignment if user_id is empty
        if existing:
            db.delete(existing)
    
    db.commit()
    
    # Preserve fund_id in redirect and set cookie
    response = RedirectResponse(url=f"/admin/months?fund_id={fund_id}", status_code=302)
    response.set_cookie(key="current_fund_id", value=str(fund_id), httponly=True)
    return response

@router.get("/admin/payments", response_class=HTMLResponse)
async def admin_payments(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    current_fund: Optional[Fund] = Depends(get_optional_fund),
    db: Session = Depends(get_db)
):
    # Get all funds for selection
    all_funds = db.query(Fund).all()
    
    # If no fund selected, show fund selection
    if not current_fund:
        return templates.TemplateResponse(
            "admin_payments_select.html",
            {
                "request": request,
                "user": current_user,
                "funds": all_funds
            }
        )
    
    # Fund selected, show payments for that fund
    # Get filter parameters
    filter_month_id = request.query_params.get("filter_month_id")
    filter_user_id = request.query_params.get("filter_user_id")
    
    # Get all months for this fund (for filter dropdown)
    months = db.query(Month).filter(Month.fund_id == current_fund.id).order_by(Month.month_number).all()
    
    # Get all users who have payments in this fund (for filter dropdown)
    # Explicitly specify the join condition to avoid ambiguous foreign key error
    users_with_payments = db.query(User).join(
        InstallmentPayment, User.id == InstallmentPayment.user_id
    ).join(Month).filter(
        Month.fund_id == current_fund.id
    ).distinct().all()
    
    # Build query for installment payments with filters
    installment_query = db.query(InstallmentPayment).join(Month).filter(
        Month.fund_id == current_fund.id
    )
    
    if filter_month_id:
        try:
            month_id_int = int(filter_month_id)
            installment_query = installment_query.filter(Month.id == month_id_int)
        except ValueError:
            pass
    
    if filter_user_id:
        try:
            user_id_int = int(filter_user_id)
            installment_query = installment_query.filter(InstallmentPayment.user_id == user_id_int)
        except ValueError:
            pass
    
    installment_payments = installment_query.order_by(InstallmentPayment.paid_at.desc()).all()
    
    # Add display info for each payment's user
    installment_payments_with_display = []
    for payment in installment_payments:
        user_display = get_user_display_info(payment.user, current_user)
        marked_by_display = get_user_display_info(payment.marked_by_user, current_user) if payment.marked_by_user else None
        verified_by_display = get_user_display_info(payment.verified_by_user, current_user) if payment.verified_by_user else None
        installment_payments_with_display.append({
            "payment": payment,
            "user_display": user_display,
            "marked_by_display": marked_by_display,
            "verified_by_display": verified_by_display
        })
    
    # Get monthly payments received
    monthly_payments = db.query(MonthlyPaymentReceived).join(Month).filter(
        Month.fund_id == current_fund.id
    ).order_by(MonthlyPaymentReceived.received_at.desc()).all()
    
    return templates.TemplateResponse(
        "admin_payments.html",
        {
            "request": request,
            "user": current_user,
            "current_fund": current_fund,
            "all_funds": all_funds,
            "installment_payments": installment_payments_with_display,
            "monthly_payments": monthly_payments,
            "months": months,
            "users_with_payments": users_with_payments,
            "filter_month_id": filter_month_id,
            "filter_user_id": filter_user_id
        }
    )

@router.post("/admin/payments/verify")
async def verify_payment(
    payment_id: int = Form(...),
    request: Request = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    from fastapi.responses import JSONResponse, RedirectResponse
    
    payment = db.query(InstallmentPayment).filter(
        InstallmentPayment.id == payment_id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment.status = "verified"
    payment.verified_by = current_user.id
    db.commit()
    
    # Check if this is an AJAX request (from modal) - check for AJAX-specific headers
    is_ajax = False
    if request:
        accept_header = request.headers.get("accept", "")
        x_requested_with = request.headers.get("x-requested-with", "")
        # AJAX requests typically have Accept: application/json or X-Requested-With: XMLHttpRequest
        if "application/json" in accept_header or x_requested_with == "XMLHttpRequest":
            is_ajax = True
    
    if is_ajax:
        return JSONResponse({"message": "Payment verified successfully", "payment_id": payment_id})
    
    # Regular form submission - redirect back to payments page
    fund_id = payment.month.fund_id
    return RedirectResponse(url=f"/admin/payments?fund_id={fund_id}", status_code=302)

@router.post("/admin/payments/reject")
async def reject_payment(
    payment_id: int = Form(...),
    request: Request = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    from fastapi.responses import JSONResponse
    
    payment = db.query(InstallmentPayment).filter(
        InstallmentPayment.id == payment_id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment.status = "rejected"
    payment.verified_by = current_user.id
    db.commit()
    
    # Check if this is an AJAX/fetch request (from modal)
    # Look for X-Requested-With header or Accept header containing application/json
    is_ajax = False
    if request:
        accept_header = request.headers.get("accept", "")
        x_requested_with = request.headers.get("x-requested-with", "")
        # Check if it's a fetch/AJAX request
        if "application/json" in accept_header or x_requested_with.lower() == "xmlhttprequest":
            is_ajax = True
    
    if is_ajax:
        # Return JSON for modal/fetch requests
        return JSONResponse({"message": "Payment rejected", "payment_id": payment_id})
    
    # Regular form submission - redirect back to payments page
    fund_id = payment.month.fund_id
    return RedirectResponse(url=f"/admin/payments?fund_id={fund_id}", status_code=302)

@router.post("/admin/payments/delete")
async def delete_payment(
    payment_id: int = Form(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    payment = db.query(InstallmentPayment).filter(
        InstallmentPayment.id == payment_id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Get fund_id before deleting
    fund_id = payment.month.fund_id
    db.delete(payment)
    db.commit()
    
    return RedirectResponse(url=f"/admin/payments?fund_id={fund_id}", status_code=302)

@router.post("/admin/payments/mark-on-behalf")
async def mark_payment_on_behalf(
    user_id: int = Form(...),
    month_id: int = Form(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Admin can mark payment as paid on behalf of a user"""
    from datetime import datetime
    
    # Check if payment already exists
    existing = db.query(InstallmentPayment).filter(
        InstallmentPayment.user_id == user_id,
        InstallmentPayment.month_id == month_id
    ).first()
    
    if existing:
        # If rejected, allow re-submission by changing status back to pending
        if existing.status == "rejected":
            existing.status = "pending"
            existing.paid_at = datetime.utcnow()
            existing.marked_by = current_user.id
            db.commit()
            return {"message": "Payment re-submitted successfully", "payment_id": existing.id}
        return {"message": "Payment already marked", "payment_id": existing.id}
    
    # Create new payment
    payment = InstallmentPayment(
        user_id=user_id,
        month_id=month_id,
        marked_by=current_user.id,
        status="pending"
    )
    db.add(payment)
    db.commit()
    
    return {"message": "Payment marked successfully", "payment_id": payment.id}

@router.post("/admin/monthly-payment/mark-received")
async def mark_monthly_payment_received(
    request: Request,
    month_id: int = Form(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Mark monthly payment as received by the assigned user"""
    from fastapi.responses import JSONResponse, RedirectResponse
    
    # Get the month and its assignment
    month = db.query(Month).filter(Month.id == month_id).first()
    if not month:
        raise HTTPException(status_code=404, detail="Month not found")
    
    assignment = db.query(UMA).filter(
        UMA.month_id == month_id
    ).first()
    
    if not assignment:
        raise HTTPException(status_code=400, detail="No user assigned to this month")
    
    # Check if already exists
    existing = db.query(MonthlyPaymentReceived).filter(
        MonthlyPaymentReceived.month_id == month_id
    ).first()
    
    if existing:
        # Update existing
        existing.status = "pending"
        existing.received_at = datetime.utcnow()
        existing.marked_by = current_user.id
    else:
        # Create new
        monthly_payment = MonthlyPaymentReceived(
            month_id=month_id,
            user_id=assignment.user_id,
            amount=month.payment_amount,
            marked_by=current_user.id,
            status="pending"
        )
        db.add(monthly_payment)
    
    db.commit()
    
    # Check if this is an AJAX request
    is_ajax = False
    if request:
        accept_header = request.headers.get("accept", "")
        x_requested_with = request.headers.get("x-requested-with", "")
        if "application/json" in accept_header or x_requested_with == "XMLHttpRequest":
            is_ajax = True
    
    if is_ajax:
        return JSONResponse({"message": "Monthly payment marked as received", "month_id": month_id})
    
    # Regular form submission - redirect back with fund_id
    fund_id = month.fund_id
    return RedirectResponse(url=f"/admin/payments?fund_id={fund_id}", status_code=302)

@router.post("/admin/monthly-payment/verify")
async def verify_monthly_payment(
    payment_id: int = Form(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    payment = db.query(MonthlyPaymentReceived).filter(
        MonthlyPaymentReceived.id == payment_id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment.status = "verified"
    payment.verified_by = current_user.id
    db.commit()
    
    # Redirect back with fund_id
    fund_id = payment.month.fund_id
    return RedirectResponse(url=f"/admin/payments?fund_id={fund_id}", status_code=302)

@router.post("/admin/monthly-payment/reject")
async def reject_monthly_payment(
    payment_id: int = Form(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    payment = db.query(MonthlyPaymentReceived).filter(
        MonthlyPaymentReceived.id == payment_id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment.status = "rejected"
    payment.verified_by = current_user.id
    db.commit()
    
    # Redirect back with fund_id
    fund_id = payment.month.fund_id
    return RedirectResponse(url=f"/admin/payments?fund_id={fund_id}", status_code=302)

@router.post("/admin/monthly-payment/delete")
async def delete_monthly_payment(
    payment_id: int = Form(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    payment = db.query(MonthlyPaymentReceived).filter(
        MonthlyPaymentReceived.id == payment_id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    fund_id = payment.month.fund_id
    db.delete(payment)
    db.commit()
    
    return RedirectResponse(url=f"/admin/payments?fund_id={fund_id}", status_code=302)

