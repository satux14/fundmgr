"""
Audit logging helper functions
"""
import json
from typing import Optional
from fastapi import Request
from sqlalchemy.orm import Session
from app.models import AuditLog


def get_client_ip(request: Optional[Request]) -> Optional[str]:
    """Extract client IP address from request"""
    if not request:
        return None
    
    # Check for forwarded IP (when behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    if request.client:
        return request.client.host
    
    return None


def get_user_agent(request: Optional[Request]) -> Optional[str]:
    """Extract user agent from request"""
    if not request:
        return None
    return request.headers.get("User-Agent")


def log_action(
    db: Session,
    user_id: Optional[int],
    action_type: str,
    action_description: str,
    request: Optional[Request] = None,
    fund_id: Optional[int] = None,
    details: Optional[dict] = None
) -> AuditLog:
    """
    Create an audit log entry
    
    Args:
        db: Database session
        user_id: ID of the user performing the action (None for anonymous actions)
        action_type: Type of action (e.g., "LOGIN", "LOGOUT", "PAYMENT_VERIFIED")
        action_description: Human-readable description of the action
        request: FastAPI Request object to extract IP and user agent
        fund_id: ID of the fund if action is fund-related
        details: Dictionary of additional details to store as JSON
    
    Returns:
        Created AuditLog object
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    # Convert details dict to JSON string if provided
    details_json = None
    if details:
        try:
            details_json = json.dumps(details)
        except (TypeError, ValueError):
            # If details can't be serialized, store as string representation
            details_json = str(details)
    
    audit_log = AuditLog(
        user_id=user_id,
        action_type=action_type,
        action_description=action_description,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details_json,
        fund_id=fund_id
    )
    
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    
    return audit_log

