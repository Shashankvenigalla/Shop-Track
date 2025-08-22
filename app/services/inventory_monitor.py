"""
Inventory Monitor service for tracking and updating stock levels.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db_context
from app.core.redis_client import cache_manager
from app.models.inventory import Product, InventoryLevel, StockMovement, StockMovementType, ProductCategory
from app.models.alerts import Alert, AlertType, AlertSeverity, AlertStatus
from app.services.alert_dispatcher import AlertDispatcher

logger = logging.getLogger(__name__)


class InventoryMonitor:
    """Service for monitoring and updating inventory levels in real-time."""
    
    def __init__(self):
        self.alert_dispatcher = AlertDispatcher()
        self._stock_cache = {}
    
    async def update_stock_level(
        self, 
        db: Session,
        product_id: int, 
        quantity: int, 
        movement_type: StockMovementType,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        user_id: Optional[str] = None,
        notes: Optional[str] = None,
        location_id: str = "main"
    ) -> Dict[str, Any]:
        """
        Update stock level for a product.
        
        Args:
            db: Database session
            product_id: Product ID
            quantity: Quantity to add/subtract (positive for additions, negative for reductions)
            movement_type: Type of stock movement
            reference_id: Optional reference ID (sale ID, purchase order ID, etc.)
            reference_type: Optional reference type
            user_id: Optional user ID who made the change
            notes: Optional notes
            location_id: Location ID (default: "main")
        
        Returns:
            Dict containing updated inventory information
        """
        try:
            # Get product and current inventory level
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                raise ValueError(f"Product {product_id} not found")
            
            # Get or create inventory level
            inventory_level = db.query(InventoryLevel).filter(
                and_(
                    InventoryLevel.product_id == product_id,
                    InventoryLevel.location_id == location_id
                )
            ).first()
            
            if not inventory_level:
                inventory_level = InventoryLevel(
                    product_id=product_id,
                    current_quantity=0,
                    reserved_quantity=0,
                    available_quantity=0,
                    location_id=location_id
                )
                db.add(inventory_level)
                db.flush()
            
            # Store previous quantities
            previous_quantity = inventory_level.current_quantity
            previous_available = inventory_level.available_quantity
            
            # Update quantities
            inventory_level.current_quantity += quantity
            inventory_level.available_quantity = inventory_level.current_quantity - inventory_level.reserved_quantity
            
            # Ensure quantities don't go negative
            if inventory_level.current_quantity < 0:
                inventory_level.current_quantity = 0
                inventory_level.available_quantity = 0
                logger.warning(f"Stock level for product {product_id} would go negative, set to 0")
            
            # Create stock movement record
            stock_movement = StockMovement(
                product_id=product_id,
                movement_type=movement_type,
                quantity=quantity,
                previous_quantity=previous_quantity,
                new_quantity=inventory_level.current_quantity,
                reference_id=reference_id,
                reference_type=reference_type,
                user_id=user_id,
                notes=notes,
                location_id=location_id
            )
            db.add(stock_movement)
            
            # Update cache
            self._update_stock_cache(product_id, inventory_level)
            
            # Check for alerts
            await self._check_stock_alerts(db, product, inventory_level, previous_available)
            
            logger.info(f"Stock updated for product {product_id}: {previous_quantity} -> {inventory_level.current_quantity}")
            
            return {
                "product_id": product_id,
                "product_name": product.name,
                "previous_quantity": previous_quantity,
                "new_quantity": inventory_level.current_quantity,
                "available_quantity": inventory_level.available_quantity,
                "movement_type": movement_type.value,
                "quantity_changed": quantity
            }
            
        except Exception as e:
            logger.error(f"Failed to update stock level for product {product_id}: {e}")
            raise
    
    async def get_inventory_status(self, product_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get current inventory status for all products or a specific product."""
        with get_db_context() as db:
            query = db.query(Product, InventoryLevel).join(InventoryLevel)
            
            if product_id:
                query = query.filter(Product.id == product_id)
            
            results = query.filter(Product.is_tracked == True).all()
            
            inventory_status = []
            for product, inventory in results:
                status = {
                    "product_id": product.id,
                    "sku": product.sku,
                    "name": product.name,
                    "category": product.category.value,
                    "current_quantity": inventory.current_quantity,
                    "reserved_quantity": inventory.reserved_quantity,
                    "available_quantity": inventory.available_quantity,
                    "min_stock_level": product.min_stock_level,
                    "reorder_point": product.reorder_point,
                    "max_stock_level": product.max_stock_level,
                    "location_id": inventory.location_id,
                    "last_updated": inventory.updated_at.isoformat(),
                    "status": self._get_stock_status(product, inventory)
                }
                inventory_status.append(status)
            
            return inventory_status
    
    def _get_stock_status(self, product: Product, inventory: InventoryLevel) -> str:
        """Determine stock status based on current levels."""
        if inventory.available_quantity <= 0:
            return "out_of_stock"
        elif inventory.available_quantity <= product.min_stock_level:
            return "low_stock"
        elif inventory.available_quantity <= product.reorder_point:
            return "reorder_needed"
        elif inventory.available_quantity >= product.max_stock_level:
            return "overstocked"
        else:
            return "normal"
    
    async def get_low_stock_products(self, threshold: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get products with low stock levels."""
        with get_db_context() as db:
            query = db.query(Product, InventoryLevel).join(InventoryLevel)
            
            if threshold:
                query = query.filter(InventoryLevel.available_quantity <= threshold)
            else:
                query = query.filter(InventoryLevel.available_quantity <= Product.min_stock_level)
            
            results = query.filter(Product.is_tracked == True).all()
            
            return [
                {
                    "product_id": product.id,
                    "sku": product.sku,
                    "name": product.name,
                    "current_quantity": inventory.available_quantity,
                    "min_stock_level": product.min_stock_level,
                    "reorder_point": product.reorder_point,
                    "days_of_stock": self._calculate_days_of_stock(product.id, inventory.available_quantity)
                }
                for product, inventory in results
            ]
    
    async def _calculate_days_of_stock(self, product_id: int, current_quantity: int) -> float:
        """Calculate days of stock remaining based on recent sales."""
        with get_db_context() as db:
            # Get average daily sales for the last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            daily_sales = db.query(
                func.date(StockMovement.created_at).label('date'),
                func.sum(func.abs(StockMovement.quantity)).label('daily_quantity')
            ).filter(
                and_(
                    StockMovement.product_id == product_id,
                    StockMovement.movement_type == StockMovementType.SALE,
                    StockMovement.created_at >= thirty_days_ago
                )
            ).group_by(func.date(StockMovement.created_at)).all()
            
            if not daily_sales:
                return float('inf')  # No sales data
            
            total_quantity = sum(daily.daily_quantity for daily in daily_sales)
            avg_daily_sales = total_quantity / len(daily_sales)
            
            if avg_daily_sales <= 0:
                return float('inf')
            
            return current_quantity / avg_daily_sales
    
    async def _check_stock_alerts(self, db: Session, product: Product, inventory: InventoryLevel, previous_available: int) -> None:
        """Check and create stock-related alerts."""
        try:
            # Check for out of stock
            if inventory.available_quantity <= 0 and previous_available > 0:
                await self.alert_dispatcher.create_alert(
                    db=db,
                    alert_type=AlertType.OUT_OF_STOCK,
                    severity=AlertSeverity.HIGH,
                    title=f"Product Out of Stock: {product.name}",
                    message=f"Product {product.name} (SKU: {product.sku}) is now out of stock.",
                    product_id=product.id,
                    details={
                        "sku": product.sku,
                        "previous_quantity": previous_available,
                        "current_quantity": inventory.available_quantity
                    }
                )
            
            # Check for low stock
            elif inventory.available_quantity <= product.min_stock_level and previous_available > product.min_stock_level:
                await self.alert_dispatcher.create_alert(
                    db=db,
                    alert_type=AlertType.LOW_STOCK,
                    severity=AlertSeverity.MEDIUM,
                    title=f"Low Stock Alert: {product.name}",
                    message=f"Product {product.name} (SKU: {product.sku}) is running low on stock. Current: {inventory.available_quantity}, Min: {product.min_stock_level}",
                    product_id=product.id,
                    details={
                        "sku": product.sku,
                        "current_quantity": inventory.available_quantity,
                        "min_stock_level": product.min_stock_level,
                        "reorder_point": product.reorder_point
                    }
                )
            
            # Check for reorder point
            elif inventory.available_quantity <= product.reorder_point and previous_available > product.reorder_point:
                await self.alert_dispatcher.create_alert(
                    db=db,
                    alert_type=AlertType.LOW_STOCK,
                    severity=AlertSeverity.LOW,
                    title=f"Reorder Point Reached: {product.name}",
                    message=f"Product {product.name} (SKU: {product.sku}) has reached reorder point. Consider restocking.",
                    product_id=product.id,
                    details={
                        "sku": product.sku,
                        "current_quantity": inventory.available_quantity,
                        "reorder_point": product.reorder_point
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to check stock alerts for product {product.id}: {e}")
    
    def _update_stock_cache(self, product_id: int, inventory: InventoryLevel) -> None:
        """Update stock cache for quick access."""
        cache_key = f"stock:{product_id}"
        cache_manager.set(cache_key, {
            "current_quantity": inventory.current_quantity,
            "available_quantity": inventory.available_quantity,
            "updated_at": datetime.utcnow().isoformat()
        }, ttl=300)  # Cache for 5 minutes
    
    async def get_stock_movements(
        self, 
        product_id: Optional[int] = None, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get stock movement history."""
        with get_db_context() as db:
            query = db.query(StockMovement).join(Product)
            
            if product_id:
                query = query.filter(StockMovement.product_id == product_id)
            
            if start_date:
                query = query.filter(StockMovement.created_at >= start_date)
            
            if end_date:
                query = query.filter(StockMovement.created_at <= end_date)
            
            movements = query.order_by(desc(StockMovement.created_at)).limit(limit).all()
            
            return [
                {
                    "id": movement.id,
                    "product_id": movement.product_id,
                    "product_name": movement.product.name,
                    "movement_type": movement.movement_type.value,
                    "quantity": movement.quantity,
                    "previous_quantity": movement.previous_quantity,
                    "new_quantity": movement.new_quantity,
                    "reference_id": movement.reference_id,
                    "reference_type": movement.reference_type,
                    "user_id": movement.user_id,
                    "notes": movement.notes,
                    "created_at": movement.created_at.isoformat()
                }
                for movement in movements
            ] 