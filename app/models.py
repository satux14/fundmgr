from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

# Association table for many-to-many relationship between Users and Funds
fund_members = Table(
    'fund_members',
    Base.metadata,
    Column('fund_id', Integer, ForeignKey('funds.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
)

class Fund(Base):
    __tablename__ = "funds"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    total_amount = Column(Float, nullable=False)  # Total fund amount (e.g., 1.5 Lakh)
    number_of_months = Column(Integer, default=10)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    months = relationship("Month", back_populates="fund", cascade="all, delete-orphan")
    members = relationship("User", secondary=fund_members, back_populates="funds")
    created_by_user = relationship("User", foreign_keys=[created_by], viewonly=True)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    customer_id = Column(String, unique=True, index=True, nullable=True)  # Unique customer identifier
    alias = Column(String, nullable=True)  # Display alias for privacy
    role = Column(String, default="user")  # "user" or "admin"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships - specify primaryjoin to avoid ambiguity with multiple foreign keys
    month_assignments = relationship(
        "UserMonthAssignment", 
        primaryjoin="User.id == UserMonthAssignment.user_id",
        back_populates="user"
    )
    installment_payments = relationship(
        "InstallmentPayment", 
        primaryjoin="User.id == InstallmentPayment.user_id",
        back_populates="user"
    )
    monthly_payments_received = relationship(
        "MonthlyPaymentReceived",
        primaryjoin="User.id == MonthlyPaymentReceived.user_id",
        back_populates="user"
    )
    funds = relationship("Fund", secondary=fund_members, back_populates="members")

class Month(Base):
    __tablename__ = "months"
    
    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    month_name = Column(String, nullable=False)  # Jan, Feb, etc.
    month_number = Column(Integer, nullable=False)  # 1-10
    installment_amount = Column(Float, nullable=False)
    payment_amount = Column(Float, nullable=False)
    year = Column(Integer, default=2026)
    
    # Relationships
    fund = relationship("Fund", back_populates="months")
    assignments = relationship("UserMonthAssignment", back_populates="month")
    payments = relationship("InstallmentPayment", back_populates="month")
    payment_received = relationship("MonthlyPaymentReceived", back_populates="month", uselist=False)

class UserMonthAssignment(Base):
    __tablename__ = "user_month_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    month_id = Column(Integer, ForeignKey("months.id"), nullable=False, unique=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships - explicitly specify foreign keys
    user = relationship("User", foreign_keys=[user_id], back_populates="month_assignments")
    month = relationship("Month", back_populates="assignments")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by], viewonly=True)

class InstallmentPayment(Base):
    __tablename__ = "installment_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    month_id = Column(Integer, ForeignKey("months.id"), nullable=False)
    paid_at = Column(DateTime, default=datetime.utcnow)
    payment_date = Column(DateTime, nullable=True)  # User-provided payment date
    transaction_id = Column(String, nullable=True)  # Transaction ID/Reference
    transaction_type = Column(String, nullable=True)  # GPay, Cash, UPI, etc.
    marked_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="pending")  # "pending", "verified", or "rejected"
    
    # Relationships - explicitly specify foreign keys
    user = relationship("User", foreign_keys=[user_id], back_populates="installment_payments")
    month = relationship("Month", back_populates="payments")
    marked_by_user = relationship("User", foreign_keys=[marked_by], viewonly=True)
    verified_by_user = relationship("User", foreign_keys=[verified_by], viewonly=True)

class MonthlyPaymentReceived(Base):
    __tablename__ = "monthly_payments_received"
    
    id = Column(Integer, primary_key=True, index=True)
    month_id = Column(Integer, ForeignKey("months.id"), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # The assigned user who received the payment
    received_at = Column(DateTime, default=datetime.utcnow)
    marked_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Admin who marked it as received
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="pending")  # "pending", "verified", or "rejected"
    amount = Column(Float, nullable=False)  # Amount received (from month.payment_amount)
    
    # Relationships
    month = relationship("Month", back_populates="payment_received")
    user = relationship("User", foreign_keys=[user_id], back_populates="monthly_payments_received")
    marked_by_user = relationship("User", foreign_keys=[marked_by], viewonly=True)
    verified_by_user = relationship("User", foreign_keys=[verified_by], viewonly=True)

