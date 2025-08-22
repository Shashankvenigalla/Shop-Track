"""
Prediction models for storing ML forecasts and predictions.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.core.database import Base


class PredictionType(enum.Enum):
    """Prediction type enumeration."""
    RUSH_HOUR = "rush_hour"
    STOCKOUT = "stockout"
    SALES_FORECAST = "sales_forecast"
    QUEUE_LENGTH = "queue_length"
    DEMAND_FORECAST = "demand_forecast"


class PredictionStatus(enum.Enum):
    """Prediction status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    VERIFIED = "verified"
    INVALIDATED = "invalidated"


class Prediction(Base):
    """Model for ML predictions and forecasts."""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Prediction details
    prediction_type = Column(Enum(PredictionType), nullable=False)
    status = Column(Enum(PredictionStatus), default=PredictionStatus.ACTIVE, nullable=False)
    
    # Target entity
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    location_id = Column(String(50), nullable=True)
    
    # Prediction data
    predicted_value = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)  # 0.0 to 1.0
    prediction_horizon = Column(Integer, nullable=False)  # hours ahead
    
    # Time windows
    prediction_for = Column(DateTime(timezone=True), nullable=False)  # When this prediction is for
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Model information
    model_version = Column(String(50), nullable=True)
    model_parameters = Column(JSON, nullable=True)  # Model configuration used
    
    # Additional data
    input_features = Column(JSON, nullable=True)  # Features used for prediction
    output_details = Column(JSON, nullable=True)  # Additional prediction details
    
    # Verification
    actual_value = Column(Float, nullable=True)  # Actual value when available
    accuracy_score = Column(Float, nullable=True)  # How accurate the prediction was
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    product = relationship("Product", backref="predictions")
    
    def __repr__(self):
        return f"<Prediction(id={self.id}, type={self.prediction_type}, value={self.predicted_value}, confidence={self.confidence_score})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if prediction has expired."""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        if self.prediction_for and datetime.utcnow() > self.prediction_for:
            return True
        return False
    
    @property
    def is_verified(self) -> bool:
        """Check if prediction has been verified with actual data."""
        return self.actual_value is not None and self.verified_at is not None
    
    def verify(self, actual_value: float, accuracy_score: float = None) -> None:
        """Mark prediction as verified with actual value."""
        self.actual_value = actual_value
        self.accuracy_score = accuracy_score
        self.verified_at = datetime.utcnow()
        self.status = PredictionStatus.VERIFIED 