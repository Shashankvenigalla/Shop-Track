"""
Core configuration settings for ShopTrack application.
"""
import os
from typing import Optional
from pydantic import BaseSettings, validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "ShopTrack"
    debug: bool = False
    secret_key: str = "your-secret-key-here"
    api_v1_str: str = "/api/v1"
    
    # Database
    database_url: str = "postgresql://user:password@localhost/shop_track"
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    
    # ML Settings
    ml_model_path: str = "models/rush_predictor.pkl"
    ml_update_interval: int = 3600  # 1 hour
    prediction_horizon: int = 24  # hours
    
    # Alert Settings
    alert_threshold: float = 0.7
    low_stock_threshold: int = 10
    rush_prediction_threshold: float = 0.8
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Dashboard
    dashboard_port: int = 8050
    dashboard_host: str = "0.0.0.0"
    
    # Monitoring
    prometheus_port: int = 9090
    metrics_enabled: bool = True
    
    @validator("database_url")
    def validate_database_url(cls, v):
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError("Database URL must be a PostgreSQL connection string")
        return v
    
    @validator("redis_url")
    def validate_redis_url(cls, v):
        if not v.startswith("redis://"):
            raise ValueError("Redis URL must start with redis://")
        return v
    
    @validator("alert_threshold")
    def validate_alert_threshold(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Alert threshold must be between 0 and 1")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings() 