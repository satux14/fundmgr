"""
Audit logging helper functions.

Thin wrapper around srs_audit shared library. Maintains the same
log_action() API so all existing callers continue to work unchanged.
"""
import json
from typing import Optional
from fastapi import Request
from sqlalchemy.orm import Session

from srs_audit import get_audit_logger


def get_client_ip(request: Optional[Request]) -> Optional[str]:
    """Extract client IP address from request."""
    if not request:
        return None
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return None


def get_user_agent(request: Optional[Request]) -> Optional[str]:
    """Extract user agent from request."""
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
    details: Optional[dict] = None,
):
    """
    Create an audit log entry via the shared srs_audit library.

    This is a drop-in replacement for the old log_action() that stored
    directly in the fundmgr AuditLog model. Now delegates to the shared
    library which stores in the unified audit_logs table and increments
    Prometheus metrics.

    The 'db' parameter is accepted for backward compatibility but is
    not used -- the shared library manages its own sessions.
    """
    try:
        logger = get_audit_logger("fundmgr")
    except RuntimeError:
        return None

    audit_details = details.copy() if details else {}
    if fund_id is not None:
        audit_details["fund_id"] = fund_id
    audit_details["description"] = action_description

    return logger.audit(
        action=action_type,
        user_id=user_id,
        resource_type="fund" if fund_id else None,
        resource_id=str(fund_id) if fund_id else None,
        details=audit_details if audit_details else None,
        request=request,
    )
