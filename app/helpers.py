"""
Helper functions for the application
"""
from app.models import User

def get_user_display_name(user: User, current_user: User = None) -> str:
    """
    Get the display name for a user based on privacy settings.
    - If current_user is admin: return full_name
    - If current_user is guest: return only customer_id (never names)
    - If current_user is the same user: return full_name
    - Otherwise: return alias if available, else customer_id, else "Customer {id}"
    """
    if not user:
        return "Unknown"
    
    # Guest users can only see customer IDs, never names
    if current_user and current_user.role == "guest":
        if user.customer_id:
            return user.customer_id
        else:
            return f"C{user.id:03d}"
    
    # Admin can always see full names
    if current_user and current_user.role == "admin":
        return user.full_name
    
    # User can see their own name
    if current_user and current_user.id == user.id:
        return user.full_name
    
    # For other users, show alias or customer_id
    if user.alias:
        return user.alias
    elif user.customer_id:
        return user.customer_id
    else:
        return f"Customer {user.id}"

def get_user_display_info(user: User, current_user: User = None) -> dict:
    """
    Get display information for a user including both display name and identifier.
    Returns a dict with 'display_name' and 'identifier' (customer_id or id).
    Guest users can only see customer IDs, never names.
    """
    if not user:
        return {"display_name": "Unknown", "identifier": "N/A"}
    
    identifier = user.customer_id if user.customer_id else f"C{user.id:03d}"
    
    # Guest users can only see customer IDs, never names
    if current_user and current_user.role == "guest":
        return {
            "display_name": identifier,
            "identifier": identifier,
            "full_name": None,  # Hidden for guests
            "alias": None,  # Hidden for guests
            "customer_id": user.customer_id
        }
    
    if current_user and current_user.role == "admin":
        return {
            "display_name": user.full_name,
            "identifier": identifier,
            "full_name": user.full_name,
            "alias": user.alias,
            "customer_id": user.customer_id
        }
    
    if current_user and current_user.id == user.id:
        return {
            "display_name": user.full_name,
            "identifier": identifier,
            "full_name": user.full_name,
            "alias": user.alias,
            "customer_id": user.customer_id
        }
    
    # For other users
    display_name = user.alias if user.alias else identifier
    return {
        "display_name": display_name,
        "identifier": identifier,
        "full_name": None,  # Hidden for privacy
        "alias": user.alias,
        "customer_id": user.customer_id
    }

