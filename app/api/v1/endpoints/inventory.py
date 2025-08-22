"""
Inventory API endpoints for managing inventory and stock levels.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.inventory_monitor import InventoryMonitor

router = APIRouter()
inventory_monitor = InventoryMonitor()


class StockUpdateRequest(BaseModel):
    """Request model for updating stock levels."""
    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., description="Quantity to add/subtract")
    movement_type: str = Field(..., description="Type of movement (purchase, sale, adjustment, return, damaged, expired)")
    reference_id: Optional[str] = Field(None, description="Reference ID")
    reference_type: Optional[str] = Field(None, description="Reference type")
    notes: Optional[str] = Field(None, description="Additional notes")


@router.get("/status")
async def get_inventory_status(
    product_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get current inventory status for all products or a specific product.
    
    Returns detailed inventory information including current stock levels,
    minimum levels, and status indicators.
    """
    try:
        inventory_status = await inventory_monitor.get_inventory_status(product_id)
        return inventory_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get inventory status: {str(e)}")


@router.put("/update")
async def update_stock_level(
    stock_update: StockUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update stock level for a product.
    
    This endpoint updates inventory levels and creates stock movement records.
    """
    try:
        from app.models.inventory import StockMovementType
        
        # Validate movement type
        try:
            movement_type = StockMovementType(stock_update.movement_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid movement type: {stock_update.movement_type}")
        
        result = await inventory_monitor.update_stock_level(
            db=db,
            product_id=stock_update.product_id,
            quantity=stock_update.quantity,
            movement_type=movement_type,
            reference_id=stock_update.reference_id,
            reference_type=stock_update.reference_type,
            notes=stock_update.notes
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update stock level: {str(e)}")


@router.get("/low-stock")
async def get_low_stock_products(
    threshold: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get products with low stock levels.
    
    Returns products that are running low on stock and may need restocking.
    """
    try:
        low_stock_products = await inventory_monitor.get_low_stock_products(threshold)
        return {
            "products": low_stock_products,
            "count": len(low_stock_products)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get low stock products: {str(e)}")


@router.get("/movements")
async def get_stock_movements(
    product_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get stock movement history.
    
    Returns historical stock movements for tracking inventory changes.
    """
    try:
        if limit > 500:
            limit = 500  # Cap for performance
        
        movements = await inventory_monitor.get_stock_movements(
            product_id=product_id,
            limit=limit
        )
        
        return {
            "movements": movements,
            "count": len(movements)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stock movements: {str(e)}") 