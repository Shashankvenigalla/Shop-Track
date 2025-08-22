"""
Sales Logger service for recording real-time POS transactions.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import uuid

from app.core.database import get_db_context
from app.core.redis_client import cache_manager
from app.models.sales import Sale, SaleItem, PaymentMethod
from app.models.inventory import Product, StockMovement, StockMovementType
from app.services.inventory_monitor import InventoryMonitor

logger = logging.getLogger(__name__)


class SalesLogger:
    """Service for logging sales transactions in real-time."""
    
    def __init__(self):
        self.inventory_monitor = InventoryMonitor()
        self._transaction_cache = {}
    
    async def record_sale(self, sale_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record a new sale transaction.
        
        Args:
            sale_data: Dictionary containing sale information
                - cashier_id: str
                - customer_id: Optional[str]
                - payment_method: str
                - items: List[Dict] with product_id, quantity, unit_price
                - subtotal: float
                - tax_amount: float
                - discount_amount: float
                - total_amount: float
                - notes: Optional[str]
        
        Returns:
            Dict containing the created sale information
        """
        try:
            # Generate transaction ID
            transaction_id = f"TXN-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            
            # Validate and process items
            items = sale_data.get('items', [])
            if not items:
                raise ValueError("Sale must contain at least one item")
            
            # Check inventory availability
            await self._validate_inventory(items)
            
            # Record the sale
            with get_db_context() as db:
                # Create sale record
                sale = Sale(
                    transaction_id=transaction_id,
                    cashier_id=sale_data['cashier_id'],
                    customer_id=sale_data.get('customer_id'),
                    payment_method=PaymentMethod(sale_data['payment_method']),
                    subtotal=sale_data['subtotal'],
                    tax_amount=sale_data.get('tax_amount', 0.0),
                    discount_amount=sale_data.get('discount_amount', 0.0),
                    total_amount=sale_data['total_amount'],
                    notes=sale_data.get('notes'),
                    completed_at=datetime.utcnow()
                )
                
                db.add(sale)
                db.flush()  # Get the sale ID
                
                # Create sale items and update inventory
                sale_items = []
                for item_data in items:
                    product = db.query(Product).filter(Product.id == item_data['product_id']).first()
                    if not product:
                        raise ValueError(f"Product {item_data['product_id']} not found")
                    
                    # Create sale item
                    sale_item = SaleItem(
                        sale_id=sale.id,
                        product_id=item_data['product_id'],
                        product_name=product.name,
                        sku=product.sku,
                        quantity=item_data['quantity'],
                        unit_price=item_data['unit_price'],
                        total_price=item_data['quantity'] * item_data['unit_price']
                    )
                    sale_items.append(sale_item)
                    db.add(sale_item)
                    
                    # Update inventory
                    await self.inventory_monitor.update_stock_level(
                        db, 
                        product_id=item_data['product_id'],
                        quantity=-item_data['quantity'],
                        movement_type=StockMovementType.SALE,
                        reference_id=str(sale.id),
                        reference_type="sale"
                    )
                
                db.commit()
                
                # Cache transaction for quick access
                self._cache_transaction(transaction_id, sale.id)
                
                # Trigger real-time updates
                await self._trigger_realtime_updates(sale, sale_items)
                
                logger.info(f"Sale recorded successfully: {transaction_id}")
                
                return {
                    "transaction_id": transaction_id,
                    "sale_id": sale.id,
                    "status": "completed",
                    "total_amount": sale.total_amount,
                    "items_count": len(sale_items)
                }
                
        except Exception as e:
            logger.error(f"Failed to record sale: {e}")
            raise
    
    async def _validate_inventory(self, items: List[Dict[str, Any]]) -> None:
        """Validate that all items have sufficient inventory."""
        with get_db_context() as db:
            for item in items:
                product_id = item['product_id']
                quantity = item['quantity']
                
                # Check current inventory level
                inventory_level = db.query(Product).filter(
                    Product.id == product_id,
                    Product.is_tracked == True
                ).first()
                
                if not inventory_level:
                    raise ValueError(f"Product {product_id} not found or not tracked")
                
                # Check if sufficient stock available
                if inventory_level.inventory_levels and inventory_level.inventory_levels[0].available_quantity < quantity:
                    raise ValueError(f"Insufficient stock for product {product_id}")
    
    def _cache_transaction(self, transaction_id: str, sale_id: int) -> None:
        """Cache transaction for quick access."""
        cache_key = f"transaction:{transaction_id}"
        cache_manager.set(cache_key, sale_id, ttl=3600)  # Cache for 1 hour
    
    async def _trigger_realtime_updates(self, sale: Sale, sale_items: List[SaleItem]) -> None:
        """Trigger real-time updates for dashboards and other services."""
        # This would typically involve WebSocket broadcasts or message queue publishing
        # For now, we'll just log the event
        logger.info(f"Real-time update triggered for sale {sale.transaction_id}")
    
    async def get_sales_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get sales summary for a date range."""
        with get_db_context() as db:
            # Get total sales
            total_sales = db.query(func.count(Sale.id)).filter(
                and_(
                    Sale.created_at >= start_date,
                    Sale.created_at <= end_date,
                    Sale.status == "completed"
                )
            ).scalar()
            
            # Get total revenue
            total_revenue = db.query(func.sum(Sale.total_amount)).filter(
                and_(
                    Sale.created_at >= start_date,
                    Sale.created_at <= end_date,
                    Sale.status == "completed"
                )
            ).scalar() or 0.0
            
            # Get average transaction value
            avg_transaction = total_revenue / total_sales if total_sales > 0 else 0.0
            
            # Get top selling products
            top_products = db.query(
                SaleItem.product_name,
                func.sum(SaleItem.quantity).label('total_quantity'),
                func.sum(SaleItem.total_price).label('total_revenue')
            ).join(Sale).filter(
                and_(
                    Sale.created_at >= start_date,
                    Sale.created_at <= end_date,
                    Sale.status == "completed"
                )
            ).group_by(SaleItem.product_name).order_by(
                func.sum(SaleItem.quantity).desc()
            ).limit(10).all()
            
            return {
                "total_sales": total_sales,
                "total_revenue": total_revenue,
                "average_transaction": avg_transaction,
                "top_products": [
                    {
                        "product_name": p.product_name,
                        "total_quantity": p.total_quantity,
                        "total_revenue": p.total_revenue
                    }
                    for p in top_products
                ]
            }
    
    async def get_recent_sales(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent sales for real-time display."""
        with get_db_context() as db:
            recent_sales = db.query(Sale).filter(
                Sale.status == "completed"
            ).order_by(Sale.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": sale.id,
                    "transaction_id": sale.transaction_id,
                    "total_amount": sale.total_amount,
                    "payment_method": sale.payment_method.value,
                    "created_at": sale.created_at.isoformat(),
                    "items_count": len(sale.items)
                }
                for sale in recent_sales
            ] 