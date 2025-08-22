"""
Alert models for tracking system notifications.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.core.database import Base


class AlertType(enum.Enum):
    """Alert type enumeration."""
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    RUSH_HOUR = "rush_hour"
    HIGH_QUEUE = "high_queue"
    SYSTEM_ERROR = "system_error"
    MAINTENANCE = "maintenance"


class AlertSeverity(enum.Enum):
    """Alert severity enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(enum.Enum):
    """Alert status enumeration."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class Alert(Base):
    """Model for system alerts."""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Alert details
    alert_type = Column(Enum(AlertType), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.ACTIVE, nullable=False)
    
    # Alert content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON string for additional data
    
    # Related entities
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)
    
    # User tracking
    created_by = Column(String(50), nullable=True)  # System or user ID
    acknowledged_by = Column(String(50), nullable=True)
    resolved_by = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_expired = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    product = relationship("Product", backref="alerts")
    sale = relationship("Sale", backref="alerts")
    
    def __repr__(self):
        return f"<Alert(id={self.id}, type={self.alert_type}, severity={self.severity}, status={self.status})>"
    
    @property
    def is_active(self) -> bool:
        """Check if alert is currently active."""
        if self.status != AlertStatus.ACTIVE:
            return False
        if self.is_expired:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True 