"""
Sales models for tracking POS transactions.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.core.database import Base


class PaymentMethod(enum.Enum):
    """Payment method enumeration."""
    CASH = "cash"
    CARD = "card"
    MOBILE = "mobile"
    OTHER = "other"


class Sale(Base):
    """Model for sales transactions."""
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(50), unique=True, index=True, nullable=False)
    cashier_id = Column(String(50), nullable=False)
    customer_id = Column(String(50), nullable=True)
    
    # Payment information
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    subtotal = Column(Float, nullable=False)
    tax_amount = Column(Float, nullable=False, default=0.0)
    discount_amount = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(String(20), default="completed", nullable=False)
    notes = Column(Text, nullable=True)
    
    # Relationships
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Sale(id={self.id}, transaction_id='{self.transaction_id}', total={self.total_amount})>"


class SaleItem(Base):
    """Model for individual items in a sale."""
    __tablename__ = "sale_items"
    
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Item details
    product_name = Column(String(200), nullable=False)  # Cached for performance
    sku = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", backref="sale_items")
    
    def __repr__(self):
        return f"<SaleItem(id={self.id}, product='{self.product_name}', quantity={self.quantity})>" 