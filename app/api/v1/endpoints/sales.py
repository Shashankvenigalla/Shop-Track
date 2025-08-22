"""
Sales API endpoints for recording transactions and retrieving sales data.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.sales_logger import SalesLogger

router = APIRouter()
sales_logger = SalesLogger()


class SaleItemRequest(BaseModel):
    """Request model for sale item."""
    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., gt=0, description="Quantity sold")
    unit_price: float = Field(..., gt=0, description="Unit price")


class SaleRequest(BaseModel):
    """Request model for recording a sale."""
    cashier_id: str = Field(..., description="Cashier ID")
    customer_id: Optional[str] = Field(None, description="Customer ID")
    payment_method: str = Field(..., description="Payment method (cash, card, mobile, other)")
    items: List[SaleItemRequest] = Field(..., min_items=1, description="Sale items")
    subtotal: float = Field(..., gt=0, description="Subtotal amount")
    tax_amount: float = Field(0, ge=0, description="Tax amount")
    discount_amount: float = Field(0, ge=0, description="Discount amount")
    total_amount: float = Field(..., gt=0, description="Total amount")
    notes: Optional[str] = Field(None, description="Additional notes")


class SaleResponse(BaseModel):
    """Response model for sale data."""
    transaction_id: str
    sale_id: int
    status: str
    total_amount: float
    items_count: int
    created_at: datetime


@router.post("/checkout", response_model=SaleResponse)
async def record_sale(
    sale_data: SaleRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Record a new sale transaction.
    
    This endpoint records a complete sale transaction including all items,
    updates inventory levels, and triggers real-time updates.
    """
    try:
        # Convert Pydantic model to dict
        sale_dict = sale_data.dict()
        
        # Record the sale
        result = await sales_logger.record_sale(sale_dict)
        
        # Add background task for additional processing
        background_tasks.add_task(sales_logger._trigger_realtime_updates, None, [])
        
        return SaleResponse(
            transaction_id=result["transaction_id"],
            sale_id=result["sale_id"],
            status=result["status"],
            total_amount=result["total_amount"],
            items_count=result["items_count"],
            created_at=datetime.utcnow()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record sale: {str(e)}")


@router.get("/summary")
async def get_sales_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get sales summary for a date range.
    
    Returns aggregated sales data including total sales, revenue,
    average transaction value, and top selling products.
    """
    try:
        # Default to last 30 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        summary = await sales_logger.get_sales_summary(start_date, end_date)
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sales summary: {str(e)}")


@router.get("/recent")
async def get_recent_sales(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get recent sales for real-time display.
    
    Returns the most recent sales transactions for dashboard display.
    """
    try:
        if limit > 100:
            limit = 100  # Cap at 100 for performance
        
        recent_sales = await sales_logger.get_recent_sales(limit)
        
        return {
            "sales": recent_sales,
            "count": len(recent_sales)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent sales: {str(e)}")


@router.get("/transaction/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """
    Get transaction details by transaction ID.
    
    Returns detailed information about a specific sale transaction.
    """
    try:
        # Check cache first
        cache_key = f"transaction:{transaction_id}"
        cached_sale_id = sales_logger._transaction_cache.get(cache_key)
        
        if not cached_sale_id:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Get sale details from database
        from app.models.sales import Sale, SaleItem
        
        sale = db.query(Sale).filter(Sale.transaction_id == transaction_id).first()
        if not sale:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Get sale items
        items = db.query(SaleItem).filter(SaleItem.sale_id == sale.id).all()
        
        return {
            "transaction_id": sale.transaction_id,
            "sale_id": sale.id,
            "cashier_id": sale.cashier_id,
            "customer_id": sale.customer_id,
            "payment_method": sale.payment_method.value,
            "subtotal": sale.subtotal,
            "tax_amount": sale.tax_amount,
            "discount_amount": sale.discount_amount,
            "total_amount": sale.total_amount,
            "status": sale.status,
            "notes": sale.notes,
            "created_at": sale.created_at.isoformat(),
            "completed_at": sale.completed_at.isoformat() if sale.completed_at else None,
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "sku": item.sku,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price
                }
                for item in items
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transaction: {str(e)}")


@router.get("/analytics/hourly")
async def get_hourly_analytics(
    date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get hourly sales analytics for a specific date.
    
    Returns sales data aggregated by hour for trend analysis.
    """
    try:
        if not date:
            date = datetime.utcnow().date()
        
        from app.models.sales import Sale
        from sqlalchemy import func, extract
        
        # Get hourly sales for the date
        hourly_sales = db.query(
            extract('hour', Sale.created_at).label('hour'),
            func.count(Sale.id).label('transaction_count'),
            func.sum(Sale.total_amount).label('total_revenue'),
            func.avg(Sale.total_amount).label('avg_transaction_value')
        ).filter(
            func.date(Sale.created_at) == date.date(),
            Sale.status == "completed"
        ).group_by(
            extract('hour', Sale.created_at)
        ).order_by('hour').all()
        
        return {
            "date": date.date().isoformat(),
            "hourly_data": [
                {
                    "hour": int(hour),
                    "transaction_count": int(transaction_count),
                    "total_revenue": float(total_revenue or 0),
                    "avg_transaction_value": float(avg_transaction_value or 0)
                }
                for hour, transaction_count, total_revenue, avg_transaction_value in hourly_sales
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hourly analytics: {str(e)}") 