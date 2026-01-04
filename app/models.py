from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="user")  # "user" or "admin"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    month_assignments = relationship("UserMonthAssignment", back_populates="user")
    installment_payments = relationship("InstallmentPayment", back_populates="user")

class Month(Base):
    __tablename__ = "months"
    
    id = Column(Integer, primary_key=True, index=True)
    month_name = Column(String, nullable=False)  # Jan, Feb, etc.
    month_number = Column(Integer, nullable=False)  # 1-10
    installment_amount = Column(Float, nullable=False)
    payment_amount = Column(Float, nullable=False)
    year = Column(Integer, default=2026)
    
    # Relationships
    assignments = relationship("UserMonthAssignment", back_populates="month")
    payments = relationship("InstallmentPayment", back_populates="month")

class UserMonthAssignment(Base):
    __tablename__ = "user_month_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    month_id = Column(Integer, ForeignKey("months.id"), nullable=False, unique=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="month_assignments")
    month = relationship("Month", back_populates="assignments")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])

class InstallmentPayment(Base):
    __tablename__ = "installment_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    month_id = Column(Integer, ForeignKey("months.id"), nullable=False)
    paid_at = Column(DateTime, default=datetime.utcnow)
    marked_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="pending")  # "pending" or "verified"
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="installment_payments")
    month = relationship("Month", back_populates="payments")
    marked_by_user = relationship("User", foreign_keys=[marked_by])
    verified_by_user = relationship("User", foreign_keys=[verified_by])

