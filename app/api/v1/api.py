"""
Main API router for v1 endpoints.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import sales, inventory, predictions, alerts, dashboard

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(sales.router, prefix="/sales", tags=["sales"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"]) 