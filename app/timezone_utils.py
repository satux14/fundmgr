"""
Timezone utility functions for converting UTC to IST (GMT+5:30)
"""
import pytz
from datetime import datetime

IST = pytz.timezone('Asia/Kolkata')

def get_ist_now():
    """Get current datetime in IST timezone"""
    return datetime.now(IST)

def utc_to_ist(utc_dt):
    """
    Convert UTC datetime to IST timezone.
    If datetime is naive (no timezone), assumes it's UTC.
    """
    if utc_dt is None:
        return None
    
    # If datetime is naive, assume it's UTC
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)
    
    # Convert to IST
    ist_dt = utc_dt.astimezone(IST)
    return ist_dt

def format_datetime_ist(dt, format_str='%Y-%m-%d %H:%M:%S'):
    """
    Format datetime in IST timezone.
    If datetime is naive or UTC, converts to IST first.
    """
    if dt is None:
        return None
    
    ist_dt = utc_to_ist(dt)
    return ist_dt.strftime(format_str)

