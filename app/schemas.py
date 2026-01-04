from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# User schemas
class UserBase(BaseModel):
    username: str
    full_name: str

class UserCreate(UserBase):
    password: str
    role: str = "user"

class UserResponse(UserBase):
    id: int
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True
        orm_mode = True

# Month schemas
class MonthBase(BaseModel):
    month_name: str
    month_number: int
    installment_amount: float
    payment_amount: float
    year: int = 2026

class MonthResponse(MonthBase):
    id: int
    
    class Config:
        from_attributes = True

# Assignment schemas
class AssignmentResponse(BaseModel):
    id: int
    user_id: int
    month_id: int
    assigned_at: datetime
    assigned_by: int
    user: Optional[UserResponse] = None
    month: Optional[MonthResponse] = None
    
    class Config:
        from_attributes = True

# Payment schemas
class PaymentCreate(BaseModel):
    month_id: int

class PaymentResponse(BaseModel):
    id: int
    user_id: int
    month_id: int
    paid_at: datetime
    marked_by: int
    verified_by: Optional[int]
    status: str
    month: Optional[MonthResponse] = None
    
    class Config:
        from_attributes = True

# Login schemas
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Dashboard schemas
class MonthWithStatus(BaseModel):
    id: int
    month_name: str
    month_number: int
    installment_amount: float
    payment_amount: float
    is_taken: bool
    payment_status: Optional[str] = None
    payment_id: Optional[int] = None
    
    class Config:
        from_attributes = True

