"""
Main FastAPI application for ShopTrack.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.core.database import init_db, check_db_connection
from app.core.redis_client import check_redis_connection
from app.api.v1.api import api_router
from app.services.sales_logger import SalesLogger
from app.services.inventory_monitor import InventoryMonitor
from app.services.rush_predictor import RushPredictor
from app.services.alert_dispatcher import AlertDispatcher

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting ShopTrack application...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Check connections
    if not check_db_connection():
        logger.error("Database connection check failed")
        raise RuntimeError("Database connection failed")
    
    if not check_redis_connection():
        logger.error("Redis connection check failed")
        raise RuntimeError("Redis connection failed")
    
    logger.info("ShopTrack application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ShopTrack application...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Real-Time Inventory & Checkout Prediction for Small Retail",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include API routes
app.include_router(api_router, prefix=settings.api_v1_str)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to ShopTrack",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "database": "connected" if check_db_connection() else "disconnected",
        "redis": "connected" if check_redis_connection() else "disconnected"
    }
    
    if health_status["database"] == "disconnected" or health_status["redis"] == "disconnected":
        health_status["status"] = "unhealthy"
        return JSONResponse(status_code=503, content=health_status)
    
    return health_status


@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint."""
    # In a real implementation, this would return Prometheus metrics
    return {
        "uptime": "running",
        "version": "1.0.0"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 