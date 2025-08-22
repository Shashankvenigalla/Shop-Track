"""
Inventory models for tracking products and stock levels.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.core.database import Base


class ProductCategory(enum.Enum):
    """Product category enumeration."""
    FOOD = "food"
    BEVERAGES = "beverages"
    HOUSEHOLD = "household"
    PERSONAL_CARE = "personal_care"
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    OTHER = "other"


class StockMovementType(enum.Enum):
    """Stock movement type enumeration."""
    PURCHASE = "purchase"
    SALE = "sale"
    ADJUSTMENT = "adjustment"
    RETURN = "return"
    DAMAGED = "damaged"
    EXPIRED = "expired"


class Product(Base):
    """Model for products."""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Enum(ProductCategory), nullable=False)
    
    # Pricing
    cost_price = Column(Float, nullable=False)
    selling_price = Column(Float, nullable=False)
    
    # Inventory settings
    min_stock_level = Column(Integer, default=10, nullable=False)
    max_stock_level = Column(Integer, default=100, nullable=False)
    reorder_point = Column(Integer, default=20, nullable=False)
    
    # Product status
    is_active = Column(Boolean, default=True, nullable=False)
    is_tracked = Column(Boolean, default=True, nullable=False)  # Whether to track inventory
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    inventory_levels = relationship("InventoryLevel", back_populates="product", cascade="all, delete-orphan")
    stock_movements = relationship("StockMovement", back_populates="product", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Product(id={self.id}, sku='{self.sku}', name='{self.name}')>"


class InventoryLevel(Base):
    """Model for current inventory levels."""
    __tablename__ = "inventory_levels"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Current stock
    current_quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)  # For pending orders
    available_quantity = Column(Integer, default=0, nullable=False)  # current - reserved
    
    # Location tracking (for multi-location stores)
    location_id = Column(String(50), default="main", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="inventory_levels")
    
    def __repr__(self):
        return f"<InventoryLevel(product_id={self.product_id}, current={self.current_quantity}, available={self.available_quantity})>"


class StockMovement(Base):
    """Model for tracking all stock movements."""
    __tablename__ = "stock_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Movement details
    movement_type = Column(Enum(StockMovementType), nullable=False)
    quantity = Column(Integer, nullable=False)  # Positive for additions, negative for reductions
    previous_quantity = Column(Integer, nullable=False)
    new_quantity = Column(Integer, nullable=False)
    
    # Reference information
    reference_id = Column(String(50), nullable=True)  # Sale ID, Purchase Order ID, etc.
    reference_type = Column(String(50), nullable=True)  # "sale", "purchase", "adjustment"
    
    # User tracking
    user_id = Column(String(50), nullable=True)  # Who made the change
    notes = Column(Text, nullable=True)
    
    # Location
    location_id = Column(String(50), default="main", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="stock_movements")
    
    def __repr__(self):
        return f"<StockMovement(id={self.id}, product_id={self.product_id}, type={self.movement_type}, quantity={self.quantity})>" 