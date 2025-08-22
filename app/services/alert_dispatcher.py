"""
Alert Dispatcher service for managing and sending system alerts.
"""
import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.core.database import get_db_context
from app.core.redis_client import cache_manager
from app.models.alerts import Alert, AlertType, AlertSeverity, AlertStatus

logger = logging.getLogger(__name__)


class AlertDispatcher:
    """Service for dispatching alerts and notifications."""
    
    def __init__(self):
        self._alert_channels = {}
        self._setup_channels()
    
    def _setup_channels(self) -> None:
        """Setup alert channels (email, SMS, webhook, etc.)."""
        # In a real implementation, this would configure actual notification channels
        self._alert_channels = {
            "email": self._send_email_alert,
            "sms": self._send_sms_alert,
            "webhook": self._send_webhook_alert,
            "dashboard": self._send_dashboard_alert
        }
    
    async def create_alert(
        self,
        db: Session,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        product_id: Optional[int] = None,
        sale_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        expires_in_hours: int = 24
    ) -> Alert:
        """
        Create and dispatch a new alert.
        
        Args:
            db: Database session
            alert_type: Type of alert
            severity: Alert severity
            title: Alert title
            message: Alert message
            product_id: Optional related product ID
            sale_id: Optional related sale ID
            details: Optional additional details
            expires_in_hours: Hours until alert expires
        
        Returns:
            Created alert object
        """
        try:
            # Create alert record
            alert = Alert(
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                product_id=product_id,
                sale_id=sale_id,
                details=json.dumps(details) if details else None,
                created_by="system",
                expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
            )
            
            db.add(alert)
            db.flush()  # Get the alert ID
            
            # Dispatch alert to all channels
            await self._dispatch_alert(alert)
            
            # Cache alert for quick access
            self._cache_alert(alert)
            
            logger.info(f"Alert created: {alert.id} - {title}")
            
            return alert
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            raise
    
    async def _dispatch_alert(self, alert: Alert) -> None:
        """Dispatch alert to all configured channels."""
        try:
            # Determine which channels to use based on severity
            channels = self._get_channels_for_severity(alert.severity)
            
            # Send to each channel
            for channel_name in channels:
                if channel_name in self._alert_channels:
                    try:
                        await self._alert_channels[channel_name](alert)
                    except Exception as e:
                        logger.error(f"Failed to send alert to {channel_name}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to dispatch alert: {e}")
    
    def _get_channels_for_severity(self, severity: AlertSeverity) -> List[str]:
        """Get channels to use based on alert severity."""
        if severity == AlertSeverity.CRITICAL:
            return ["email", "sms", "webhook", "dashboard"]
        elif severity == AlertSeverity.HIGH:
            return ["email", "webhook", "dashboard"]
        elif severity == AlertSeverity.MEDIUM:
            return ["webhook", "dashboard"]
        else:  # LOW
            return ["dashboard"]
    
    async def _send_email_alert(self, alert: Alert) -> None:
        """Send alert via email."""
        # In a real implementation, this would send actual emails
        logger.info(f"Email alert sent: {alert.title}")
    
    async def _send_sms_alert(self, alert: Alert) -> None:
        """Send alert via SMS."""
        # In a real implementation, this would send actual SMS
        logger.info(f"SMS alert sent: {alert.title}")
    
    async def _send_webhook_alert(self, alert: Alert) -> None:
        """Send alert via webhook."""
        # In a real implementation, this would send HTTP requests
        logger.info(f"Webhook alert sent: {alert.title}")
    
    async def _send_dashboard_alert(self, alert: Alert) -> None:
        """Send alert to dashboard."""
        # This would typically involve WebSocket broadcasts
        logger.info(f"Dashboard alert sent: {alert.title}")
    
    def _cache_alert(self, alert: Alert) -> None:
        """Cache alert for quick access."""
        cache_key = f"alert:{alert.id}"
        cache_manager.set(cache_key, {
            "id": alert.id,
            "type": alert.alert_type.value,
            "severity": alert.severity.value,
            "title": alert.title,
            "message": alert.message,
            "created_at": alert.created_at.isoformat()
        }, ttl=3600)  # Cache for 1 hour
    
    async def get_active_alerts(
        self,
        alert_type: Optional[AlertType] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get active alerts."""
        try:
            with get_db_context() as db:
                query = db.query(Alert).filter(Alert.status == AlertStatus.ACTIVE)
                
                if alert_type:
                    query = query.filter(Alert.alert_type == alert_type)
                
                if severity:
                    query = query.filter(Alert.severity == severity)
                
                alerts = query.order_by(desc(Alert.created_at)).limit(limit).all()
                
                return [
                    {
                        "id": alert.id,
                        "type": alert.alert_type.value,
                        "severity": alert.severity.value,
                        "title": alert.title,
                        "message": alert.message,
                        "product_id": alert.product_id,
                        "sale_id": alert.sale_id,
                        "details": json.loads(alert.details) if alert.details else None,
                        "created_at": alert.created_at.isoformat(),
                        "expires_at": alert.expires_at.isoformat() if alert.expires_at else None,
                        "is_expired": alert.is_expired
                    }
                    for alert in alerts
                ]
                
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []
    
    async def acknowledge_alert(self, alert_id: int, user_id: str) -> bool:
        """Acknowledge an alert."""
        try:
            with get_db_context() as db:
                alert = db.query(Alert).filter(Alert.id == alert_id).first()
                
                if not alert:
                    return False
                
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_by = user_id
                alert.acknowledged_at = datetime.utcnow()
                
                db.commit()
                
                # Remove from cache
                cache_key = f"alert:{alert_id}"
                cache_manager.delete(cache_key)
                
                logger.info(f"Alert {alert_id} acknowledged by {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
            return False
    
    async def resolve_alert(self, alert_id: int, user_id: str) -> bool:
        """Resolve an alert."""
        try:
            with get_db_context() as db:
                alert = db.query(Alert).filter(Alert.id == alert_id).first()
                
                if not alert:
                    return False
                
                alert.status = AlertStatus.RESOLVED
                alert.resolved_by = user_id
                alert.resolved_at = datetime.utcnow()
                
                db.commit()
                
                # Remove from cache
                cache_key = f"alert:{alert_id}"
                cache_manager.delete(cache_key)
                
                logger.info(f"Alert {alert_id} resolved by {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False
    
    async def dismiss_alert(self, alert_id: int, user_id: str) -> bool:
        """Dismiss an alert."""
        try:
            with get_db_context() as db:
                alert = db.query(Alert).filter(Alert.id == alert_id).first()
                
                if not alert:
                    return False
                
                alert.status = AlertStatus.DISMISSED
                alert.acknowledged_by = user_id
                alert.acknowledged_at = datetime.utcnow()
                
                db.commit()
                
                # Remove from cache
                cache_key = f"alert:{alert_id}"
                cache_manager.delete(cache_key)
                
                logger.info(f"Alert {alert_id} dismissed by {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to dismiss alert {alert_id}: {e}")
            return False
    
    async def get_alert_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get alert statistics for the last N days."""
        try:
            with get_db_context() as db:
                start_date = datetime.utcnow() - timedelta(days=days)
                
                # Total alerts by type
                alerts_by_type = db.query(
                    Alert.alert_type,
                    func.count(Alert.id).label('count')
                ).filter(
                    Alert.created_at >= start_date
                ).group_by(Alert.alert_type).all()
                
                # Total alerts by severity
                alerts_by_severity = db.query(
                    Alert.severity,
                    func.count(Alert.id).label('count')
                ).filter(
                    Alert.created_at >= start_date
                ).group_by(Alert.severity).all()
                
                # Active alerts
                active_alerts = db.query(Alert).filter(
                    and_(
                        Alert.status == AlertStatus.ACTIVE,
                        Alert.created_at >= start_date
                    )
                ).count()
                
                # Resolved alerts
                resolved_alerts = db.query(Alert).filter(
                    and_(
                        Alert.status == AlertStatus.RESOLVED,
                        Alert.created_at >= start_date
                    )
                ).count()
                
                return {
                    "total_alerts": sum(a.count for a in alerts_by_type),
                    "active_alerts": active_alerts,
                    "resolved_alerts": resolved_alerts,
                    "by_type": {
                        alert_type.value: count
                        for alert_type, count in alerts_by_type
                    },
                    "by_severity": {
                        severity.value: count
                        for severity, count in alerts_by_severity
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get alert statistics: {e}")
            return {}
    
    async def cleanup_expired_alerts(self) -> int:
        """Clean up expired alerts."""
        try:
            with get_db_context() as db:
                # Mark expired alerts as expired
                expired_count = db.query(Alert).filter(
                    and_(
                        Alert.status == AlertStatus.ACTIVE,
                        Alert.expires_at <= datetime.utcnow()
                    )
                ).update({
                    Alert.is_expired: True
                })
                
                db.commit()
                
                logger.info(f"Marked {expired_count} alerts as expired")
                return expired_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired alerts: {e}")
            return 0 