from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models import Fund, User
from app.auth import get_current_user

def get_current_fund(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current fund from cookie or query parameter"""
    fund_id = request.cookies.get("current_fund_id") or request.query_params.get("fund_id")
    
    if not fund_id:
        raise HTTPException(status_code=400, detail="No fund selected. Please select a fund first.")
    
    try:
        fund_id = int(fund_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid fund ID")
    
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    # Check if fund is archived or deleted - non-admin users cannot access
    if current_user.role != "admin":
        if fund.is_deleted or fund.is_archived:
            raise HTTPException(status_code=404, detail="Fund not found")
    
    # Check access - admin can access all, users only their funds
    if current_user.role != "admin" and current_user not in fund.members:
        raise HTTPException(status_code=403, detail="You don't have access to this fund")
    
    return fund

def get_optional_fund(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Optional[Fund]:
    """Get current fund from query parameter first, then cookie (optional for admin)"""
    import logging
    logger = logging.getLogger(__name__)
    
    # ALWAYS prioritize query parameter over cookie - if query param exists, use it and ignore cookie
    fund_id_from_query = request.query_params.get("fund_id")
    fund_id_from_cookie = request.cookies.get("current_fund_id")
    
    logger.info(f"=== get_optional_fund called ===")
    logger.info(f"get_optional_fund: URL={request.url}")
    logger.info(f"get_optional_fund: query_params={dict(request.query_params)}")
    logger.info(f"get_optional_fund: cookies={dict(request.cookies)}")
    logger.info(f"get_optional_fund: fund_id_from_query={fund_id_from_query}, fund_id_from_cookie={fund_id_from_cookie}")
    
    # If query param exists, use it (ignore cookie completely)
    if fund_id_from_query:
        fund_id = fund_id_from_query
        logger.info(f"get_optional_fund: Using query param fund_id={fund_id} (ignoring cookie={fund_id_from_cookie})")
    else:
        fund_id = fund_id_from_cookie
        logger.info(f"get_optional_fund: No query param, using cookie fund_id={fund_id}")
    
    if not fund_id:
        logger.info("get_optional_fund: No fund_id found, returning None")
        return None
    
    try:
        fund_id_int = int(fund_id)
    except (ValueError, TypeError) as e:
        logger.info(f"get_optional_fund: Invalid fund_id format: {fund_id}, error: {e}")
        return None
    
    fund = db.query(Fund).filter(Fund.id == fund_id_int).first()
    if not fund:
        logger.info(f"get_optional_fund: Fund with id {fund_id_int} not found in database")
        return None
    
    # Check if fund is archived or deleted - non-admin users cannot access
    if current_user.role != "admin":
        if fund.is_deleted or fund.is_archived:
            logger.info(f"get_optional_fund: Fund {fund_id_int} is archived/deleted, user {current_user.id} cannot access")
            return None
    
    # Check access - admin can access all, users only their funds
    if current_user.role != "admin" and current_user not in fund.members:
        logger.info(f"get_optional_fund: User {current_user.id} does not have access to fund {fund_id_int}")
        return None
    
    logger.info(f"get_optional_fund: Successfully returning fund {fund.id} - {fund.name}")
    return fund
