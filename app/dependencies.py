from fastapi import Depends
from app.auth import get_current_user, get_current_admin_user
from app.models import User

# Dependencies for route protection
def get_current_user_dep():
    return Depends(get_current_user)

def get_current_admin_dep():
    return Depends(get_current_admin_user)

