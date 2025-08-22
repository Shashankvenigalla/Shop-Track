"""
Tests for Sales Logger service.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from app.services.sales_logger import SalesLogger


class TestSalesLogger:
    """Test cases for SalesLogger service."""
    
    @pytest.fixture
    def sales_logger(self):
        """Create a SalesLogger instance for testing."""
        return SalesLogger()
    
    @pytest.fixture
    def sample_sale_data(self):
        """Sample sale data for testing."""
        return {
            "cashier_id": "cashier_001",
            "customer_id": "customer_123",
            "payment_method": "card",
            "items": [
                {
                    "product_id": 1,
                    "quantity": 2,
                    "unit_price": 10.50
                },
                {
                    "product_id": 2,
                    "quantity": 1,
                    "unit_price": 25.00
                }
            ],
            "subtotal": 46.00,
            "tax_amount": 3.68,
            "discount_amount": 0.0,
            "total_amount": 49.68,
            "notes": "Test sale"
        }
    
    @pytest.mark.asyncio
    async def test_record_sale_success(self, sales_logger, sample_sale_data):
        """Test successful sale recording."""
        with patch('app.services.sales_logger.get_db_context') as mock_db:
            # Mock database session
            mock_session = Mock()
            mock_db.return_value.__enter__.return_value = mock_session
            
            # Mock product query
            mock_product = Mock()
            mock_product.id = 1
            mock_product.name = "Test Product"
            mock_product.sku = "TEST001"
            mock_product.inventory_levels = [Mock(available_quantity=10)]
            
            mock_session.query.return_value.filter.return_value.first.return_value = mock_product
            
            # Mock sale creation
            mock_sale = Mock()
            mock_sale.id = 1
            mock_sale.transaction_id = "TXN-20231201-ABC12345"
            mock_sale.total_amount = 49.68
            mock_session.add.return_value = None
            mock_session.flush.return_value = None
            mock_session.commit.return_value = None
            
            result = await sales_logger.record_sale(sample_sale_data)
            
            assert result["status"] == "completed"
            assert result["total_amount"] == 49.68
            assert result["items_count"] == 2
            assert "transaction_id" in result
    
    @pytest.mark.asyncio
    async def test_record_sale_no_items(self, sales_logger):
        """Test sale recording with no items."""
        sale_data = {
            "cashier_id": "cashier_001",
            "payment_method": "cash",
            "items": [],
            "subtotal": 0.0,
            "total_amount": 0.0
        }
        
        with pytest.raises(ValueError, match="Sale must contain at least one item"):
            await sales_logger.record_sale(sale_data)
    
    @pytest.mark.asyncio
    async def test_get_sales_summary(self, sales_logger):
        """Test getting sales summary."""
        start_date = datetime(2023, 12, 1)
        end_date = datetime(2023, 12, 31)
        
        with patch('app.services.sales_logger.get_db_context') as mock_db:
            mock_session = Mock()
            mock_db.return_value.__enter__.return_value = mock_session
            
            # Mock query results
            mock_session.query.return_value.filter.return_value.scalar.side_effect = [100, 5000.0]
            
            # Mock top products query
            mock_product_result = Mock()
            mock_product_result.product_name = "Test Product"
            mock_product_result.total_quantity = 50
            mock_product_result.total_revenue = 500.0
            mock_session.query.return_value.join.return_value.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_product_result]
            
            result = await sales_logger.get_sales_summary(start_date, end_date)
            
            assert "total_sales" in result
            assert "total_revenue" in result
            assert "average_transaction" in result
            assert "top_products" in result
    
    @pytest.mark.asyncio
    async def test_get_recent_sales(self, sales_logger):
        """Test getting recent sales."""
        with patch('app.services.sales_logger.get_db_context') as mock_db:
            mock_session = Mock()
            mock_db.return_value.__enter__.return_value = mock_session
            
            # Mock sale objects
            mock_sale = Mock()
            mock_sale.id = 1
            mock_sale.transaction_id = "TXN-20231201-ABC12345"
            mock_sale.total_amount = 49.68
            mock_sale.payment_method.value = "card"
            mock_sale.created_at = datetime.now()
            mock_sale.items = [Mock(), Mock()]
            
            mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_sale]
            
            result = await sales_logger.get_recent_sales(limit=10)
            
            assert len(result) == 1
            assert result[0]["transaction_id"] == "TXN-20231201-ABC12345"
            assert result[0]["total_amount"] == 49.68
            assert result[0]["items_count"] == 2 