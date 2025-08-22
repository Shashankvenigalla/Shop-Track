"""
Alerts API endpoints for managing system alerts and notifications.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.alert_dispatcher import AlertDispatcher

router = APIRouter()
alert_dispatcher = AlertDispatcher()


class AlertAcknowledgeRequest(BaseModel):
    """Request model for acknowledging an alert."""
    user_id: str = Field(..., description="User ID acknowledging the alert")


class AlertResolveRequest(BaseModel):
    """Request model for resolving an alert."""
    user_id: str = Field(..., description="User ID resolving the alert")


@router.get("/active")
async def get_active_alerts(
    alert_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get active alerts.
    
    Returns currently active system alerts filtered by type and severity.
    """
    try:
        from app.models.alerts import AlertType, AlertSeverity
        
        # Convert string to enum if provided
        alert_type_enum = None
        if alert_type:
            try:
                alert_type_enum = AlertType(alert_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid alert type: {alert_type}")
        
        severity_enum = None
        if severity:
            try:
                severity_enum = AlertSeverity(severity)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        alerts = await alert_dispatcher.get_active_alerts(
            alert_type=alert_type_enum,
            severity=severity_enum,
            limit=limit
        )
        
        return {
            "alerts": alerts,
            "count": len(alerts)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active alerts: {str(e)}")


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    request: AlertAcknowledgeRequest,
    db: Session = Depends(get_db)
):
    """
    Acknowledge an alert.
    
    Marks an alert as acknowledged by a specific user.
    """
    try:
        success = await alert_dispatcher.acknowledge_alert(alert_id, request.user_id)
        
        if success:
            return {"message": "Alert acknowledged successfully"}
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    request: AlertResolveRequest,
    db: Session = Depends(get_db)
):
    """
    Resolve an alert.
    
    Marks an alert as resolved by a specific user.
    """
    try:
        success = await alert_dispatcher.resolve_alert(alert_id, request.user_id)
        
        if success:
            return {"message": "Alert resolved successfully"}
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve alert: {str(e)}")


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: int,
    request: AlertAcknowledgeRequest,
    db: Session = Depends(get_db)
):
    """
    Dismiss an alert.
    
    Marks an alert as dismissed by a specific user.
    """
    try:
        success = await alert_dispatcher.dismiss_alert(alert_id, request.user_id)
        
        if success:
            return {"message": "Alert dismissed successfully"}
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dismiss alert: {str(e)}")


@router.get("/statistics")
async def get_alert_statistics(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get alert statistics.
    
    Returns aggregated statistics about alerts for the specified time period.
    """
    try:
        if days > 365:  # Max 1 year
            days = 365
        
        statistics = await alert_dispatcher.get_alert_statistics(days)
        
        return {
            "period_days": days,
            "statistics": statistics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert statistics: {str(e)}")


@router.post("/cleanup")
async def cleanup_expired_alerts(
    db: Session = Depends(get_db)
):
    """
    Clean up expired alerts.
    
    Marks expired alerts as expired in the database.
    """
    try:
        expired_count = await alert_dispatcher.cleanup_expired_alerts()
        
        return {
            "message": f"Cleaned up {expired_count} expired alerts",
            "expired_count": expired_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup expired alerts: {str(e)}") 