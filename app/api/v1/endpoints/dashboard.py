"""
Dashboard API endpoints for aggregated dashboard data.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.sales_logger import SalesLogger
from app.services.inventory_monitor import InventoryMonitor
from app.services.rush_predictor import RushPredictor
from app.services.alert_dispatcher import AlertDispatcher

router = APIRouter()
sales_logger = SalesLogger()
inventory_monitor = InventoryMonitor()
rush_predictor = RushPredictor()
alert_dispatcher = AlertDispatcher()


@router.get("/overview")
async def get_dashboard_overview(
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard overview.
    
    Returns aggregated data for all dashboard components including
    sales metrics, inventory status, alerts, and predictions.
    """
    try:
        # Get sales summary for today
        today = datetime.utcnow().date()
        start_date = datetime.combine(today, datetime.min.time())
        end_date = datetime.combine(today, datetime.max.time())
        
        sales_summary = await sales_logger.get_sales_summary(start_date, end_date)
        
        # Get inventory status
        inventory_status = await inventory_monitor.get_inventory_status()
        
        # Get low stock products
        low_stock_products = await inventory_monitor.get_low_stock_products()
        
        # Get active alerts
        active_alerts = await alert_dispatcher.get_active_alerts(limit=10)
        
        # Get rush predictions for next 24 hours
        rush_predictions = await rush_predictor.get_rush_predictions(hours_ahead=24)
        
        # Get recent sales
        recent_sales = await sales_logger.get_recent_sales(limit=10)
        
        return {
            "sales": {
                "today_summary": sales_summary,
                "recent_sales": recent_sales
            },
            "inventory": {
                "status": inventory_status,
                "low_stock_count": len(low_stock_products),
                "low_stock_products": low_stock_products[:5]  # Top 5
            },
            "alerts": {
                "active_count": len(active_alerts),
                "recent_alerts": active_alerts[:5]  # Top 5
            },
            "predictions": {
                "rush_hours": rush_predictions,
                "next_rush_hour": _find_next_rush_hour(rush_predictions)
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard overview: {str(e)}")


@router.get("/metrics")
async def get_dashboard_metrics(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get key performance metrics.
    
    Returns key business metrics for the specified time period.
    """
    try:
        if days > 365:  # Max 1 year
            days = 365
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get sales summary
        sales_summary = await sales_logger.get_sales_summary(start_date, end_date)
        
        # Get inventory metrics
        inventory_status = await inventory_monitor.get_inventory_status()
        
        # Calculate inventory metrics
        total_products = len(inventory_status)
        low_stock_count = len([item for item in inventory_status if item.get("status") == "low_stock"])
        out_of_stock_count = len([item for item in inventory_status if item.get("status") == "out_of_stock"])
        
        # Get alert statistics
        alert_stats = await alert_dispatcher.get_alert_statistics(days)
        
        return {
            "period": {
                "days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "sales_metrics": {
                "total_sales": sales_summary.get("total_sales", 0),
                "total_revenue": sales_summary.get("total_revenue", 0),
                "average_transaction": sales_summary.get("average_transaction", 0),
                "top_products": sales_summary.get("top_products", [])[:5]
            },
            "inventory_metrics": {
                "total_products": total_products,
                "low_stock_count": low_stock_count,
                "out_of_stock_count": out_of_stock_count,
                "low_stock_percentage": (low_stock_count / total_products * 100) if total_products > 0 else 0
            },
            "alert_metrics": alert_stats,
            "calculated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard metrics: {str(e)}")


@router.get("/trends")
async def get_dashboard_trends(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get trend data for charts and visualizations.
    
    Returns time-series data for sales, inventory, and other key metrics.
    """
    try:
        if days > 365:  # Max 1 year
            days = 365
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get daily sales data
        daily_sales = await _get_daily_sales_data(start_date, end_date, db)
        
        # Get inventory trends
        inventory_trends = await _get_inventory_trends(start_date, end_date, db)
        
        # Get alert trends
        alert_trends = await _get_alert_trends(start_date, end_date, db)
        
        return {
            "period": {
                "days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "sales_trends": daily_sales,
            "inventory_trends": inventory_trends,
            "alert_trends": alert_trends
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard trends: {str(e)}")


def _find_next_rush_hour(predictions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the next predicted rush hour."""
    if not predictions:
        return None
    
    current_hour = datetime.utcnow().hour
    future_rush_hours = [
        pred for pred in predictions
        if pred.get("rush_probability", 0) > 0.7 and
        pred.get("hour", 0) > current_hour
    ]
    
    if future_rush_hours:
        return min(future_rush_hours, key=lambda x: x.get("hour", 0))
    
    return None


async def _get_daily_sales_data(start_date: datetime, end_date: datetime, db: Session) -> List[Dict[str, Any]]:
    """Get daily sales data for trend analysis."""
    try:
        from app.models.sales import Sale
        from sqlalchemy import func, extract
        
        daily_sales = db.query(
            func.date(Sale.created_at).label('date'),
            func.count(Sale.id).label('transaction_count'),
            func.sum(Sale.total_amount).label('total_revenue'),
            func.avg(Sale.total_amount).label('avg_transaction_value')
        ).filter(
            Sale.created_at >= start_date,
            Sale.created_at <= end_date,
            Sale.status == "completed"
        ).group_by(
            func.date(Sale.created_at)
        ).order_by(
            func.date(Sale.created_at)
        ).all()
        
        return [
            {
                "date": str(sale.date),
                "transaction_count": int(sale.transaction_count),
                "total_revenue": float(sale.total_revenue or 0),
                "avg_transaction_value": float(sale.avg_transaction_value or 0)
            }
            for sale in daily_sales
        ]
        
    except Exception as e:
        print(f"Error getting daily sales data: {e}")
        return []


async def _get_inventory_trends(start_date: datetime, end_date: datetime, db: Session) -> List[Dict[str, Any]]:
    """Get inventory trends data."""
    try:
        from app.models.inventory import StockMovement, StockMovementType
        from sqlalchemy import func
        
        # Get daily stock movements
        daily_movements = db.query(
            func.date(StockMovement.created_at).label('date'),
            func.count(StockMovement.id).label('movement_count'),
            func.sum(func.abs(StockMovement.quantity)).label('total_quantity')
        ).filter(
            StockMovement.created_at >= start_date,
            StockMovement.created_at <= end_date
        ).group_by(
            func.date(StockMovement.created_at)
        ).order_by(
            func.date(StockMovement.created_at)
        ).all()
        
        return [
            {
                "date": str(movement.date),
                "movement_count": int(movement.movement_count),
                "total_quantity": int(movement.total_quantity or 0)
            }
            for movement in daily_movements
        ]
        
    except Exception as e:
        print(f"Error getting inventory trends: {e}")
        return []


async def _get_alert_trends(start_date: datetime, end_date: datetime, db: Session) -> List[Dict[str, Any]]:
    """Get alert trends data."""
    try:
        from app.models.alerts import Alert
        from sqlalchemy import func
        
        # Get daily alerts
        daily_alerts = db.query(
            func.date(Alert.created_at).label('date'),
            func.count(Alert.id).label('alert_count')
        ).filter(
            Alert.created_at >= start_date,
            Alert.created_at <= end_date
        ).group_by(
            func.date(Alert.created_at)
        ).order_by(
            func.date(Alert.created_at)
        ).all()
        
        return [
            {
                "date": str(alert.date),
                "alert_count": int(alert.alert_count)
            }
            for alert in daily_alerts
        ]
        
    except Exception as e:
        print(f"Error getting alert trends: {e}")
        return [] 