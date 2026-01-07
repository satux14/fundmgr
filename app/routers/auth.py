from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.auth import authenticate_user, create_access_token, get_current_user
from app.schemas import LoginRequest, LoginResponse, UserResponse
from app.models import User
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

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, username, password)
    if not user:
        # Log failed login attempt
        log_action(
            db=db,
            user_id=None,
            action_type="LOGIN_FAILED",
            action_description=f"Failed login attempt for username: {username}",
            request=request
        )
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"},
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Log successful login
    log_action(
        db=db,
        user_id=user.id,
        action_type="LOGIN",
        action_description=f"User {user.username} ({user.full_name}) logged in",
        request=request
    )
    
    access_token_expires = timedelta(minutes=30 * 24 * 60)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=30*24*60*60)
    return response

@router.get("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Log logout action
    log_action(
        db=db,
        user_id=current_user.id,
        action_type="LOGOUT",
        action_description=f"User {current_user.username} ({current_user.full_name}) logged out",
        request=request
    )
    
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response

@router.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

