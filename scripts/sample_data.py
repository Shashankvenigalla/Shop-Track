#!/usr/bin/env python3
"""
Sample data population script for ShopTrack.
Creates sample products, inventory, and sales data for testing and demonstration.
"""
import sys
import os
from datetime import datetime, timedelta
import random

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import get_db_context, init_db
from app.models.inventory import Product, InventoryLevel, ProductCategory
from app.models.sales import Sale, SaleItem, PaymentMethod
from app.services.sales_logger import SalesLogger
from app.services.inventory_monitor import InventoryMonitor


def create_sample_products():
    """Create sample products in the database."""
    sample_products = [
        {
            "sku": "MILK001",
            "name": "Fresh Whole Milk",
            "description": "Fresh whole milk from local dairy",
            "category": ProductCategory.FOOD,
            "cost_price": 2.50,
            "selling_price": 3.99,
            "min_stock_level": 20,
            "max_stock_level": 100,
            "reorder_point": 30
        },
        {
            "sku": "BREAD001",
            "name": "Artisan Sourdough Bread",
            "description": "Fresh baked artisan sourdough bread",
            "category": ProductCategory.FOOD,
            "cost_price": 1.80,
            "selling_price": 4.50,
            "min_stock_level": 15,
            "max_stock_level": 50,
            "reorder_point": 25
        },
        {
            "sku": "COFFEE001",
            "name": "Premium Coffee Beans",
            "description": "Premium arabica coffee beans",
            "category": ProductCategory.BEVERAGES,
            "cost_price": 8.00,
            "selling_price": 12.99,
            "min_stock_level": 10,
            "max_stock_level": 40,
            "reorder_point": 15
        },
        {
            "sku": "SOAP001",
            "name": "Natural Hand Soap",
            "description": "Natural hand soap with essential oils",
            "category": ProductCategory.PERSONAL_CARE,
            "cost_price": 3.50,
            "selling_price": 6.99,
            "min_stock_level": 25,
            "max_stock_level": 80,
            "reorder_point": 35
        },
        {
            "sku": "CLEAN001",
            "name": "All-Purpose Cleaner",
            "description": "Eco-friendly all-purpose cleaner",
            "category": ProductCategory.HOUSEHOLD,
            "cost_price": 4.20,
            "selling_price": 8.50,
            "min_stock_level": 12,
            "max_stock_level": 60,
            "reorder_point": 20
        },
        {
            "sku": "SNACK001",
            "name": "Organic Trail Mix",
            "description": "Organic trail mix with nuts and dried fruits",
            "category": ProductCategory.FOOD,
            "cost_price": 5.00,
            "selling_price": 9.99,
            "min_stock_level": 8,
            "max_stock_level": 30,
            "reorder_point": 12
        },
        {
            "sku": "WATER001",
            "name": "Spring Water",
            "description": "Natural spring water in bottles",
            "category": ProductCategory.BEVERAGES,
            "cost_price": 0.80,
            "selling_price": 1.99,
            "min_stock_level": 50,
            "max_stock_level": 200,
            "reorder_point": 75
        },
        {
            "sku": "BATTERY001",
            "name": "AA Batteries (Pack of 4)",
            "description": "Long-lasting AA batteries",
            "category": ProductCategory.ELECTRONICS,
            "cost_price": 2.50,
            "selling_price": 5.99,
            "min_stock_level": 30,
            "max_stock_level": 100,
            "reorder_point": 40
        }
    ]
    
    with get_db_context() as db:
        for product_data in sample_products:
            # Check if product already exists
            existing_product = db.query(Product).filter(Product.sku == product_data["sku"]).first()
            if existing_product:
                print(f"Product {product_data['sku']} already exists, skipping...")
                continue
            
            # Create product
            product = Product(**product_data)
            db.add(product)
            db.flush()  # Get the product ID
            
            # Create initial inventory level
            initial_quantity = random.randint(
                product_data["min_stock_level"],
                product_data["max_stock_level"]
            )
            
            inventory_level = InventoryLevel(
                product_id=product.id,
                current_quantity=initial_quantity,
                reserved_quantity=0,
                available_quantity=initial_quantity,
                location_id="main"
            )
            db.add(inventory_level)
            
            print(f"Created product: {product.name} (SKU: {product.sku}) - Initial stock: {initial_quantity}")
        
        db.commit()
        print(f"✅ Created {len(sample_products)} sample products")


def create_sample_sales():
    """Create sample sales data for the last 30 days."""
    sales_logger = SalesLogger()
    
    # Get sample products
    with get_db_context() as db:
        products = db.query(Product).all()
        if not products:
            print("❌ No products found. Please create products first.")
            return
    
    # Create sales for the last 30 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    total_sales = 0
    
    for day in range(30):
        sale_date = start_date + timedelta(days=day)
        
        # Generate 5-15 sales per day
        daily_sales = random.randint(5, 15)
        
        for sale_num in range(daily_sales):
            # Random sale time during business hours (8 AM - 8 PM)
            sale_hour = random.randint(8, 20)
            sale_minute = random.randint(0, 59)
            sale_time = sale_date.replace(hour=sale_hour, minute=sale_minute)
            
            # Create sale data
            items = []
            subtotal = 0.0
            
            # 1-4 items per sale
            num_items = random.randint(1, 4)
            selected_products = random.sample(products, min(num_items, len(products)))
            
            for product in selected_products:
                quantity = random.randint(1, 3)
                unit_price = product.selling_price
                item_total = quantity * unit_price
                
                items.append({
                    "product_id": product.id,
                    "quantity": quantity,
                    "unit_price": unit_price
                })
                subtotal += item_total
            
            # Calculate taxes and total
            tax_amount = subtotal * 0.08  # 8% tax
            total_amount = subtotal + tax_amount
            
            sale_data = {
                "cashier_id": f"cashier_{random.randint(1, 3):03d}",
                "customer_id": f"customer_{random.randint(1, 100):03d}",
                "payment_method": random.choice(["cash", "card", "mobile"]),
                "items": items,
                "subtotal": subtotal,
                "tax_amount": tax_amount,
                "discount_amount": 0.0,
                "total_amount": total_amount,
                "notes": f"Sample sale from {sale_date.strftime('%Y-%m-%d')}"
            }
            
            try:
                # Record the sale
                result = await sales_logger.record_sale(sale_data)
                total_sales += 1
                
                if total_sales % 50 == 0:
                    print(f"Created {total_sales} sales...")
                    
            except Exception as e:
                print(f"Error creating sale: {e}")
                continue
    
    print(f"✅ Created {total_sales} sample sales over the last 30 days")


def create_sample_alerts():
    """Create sample alerts for demonstration."""
    from app.services.alert_dispatcher import AlertDispatcher
    from app.models.alerts import AlertType, AlertSeverity
    
    alert_dispatcher = AlertDispatcher()
    
    # Get some products to create alerts for
    with get_db_context() as db:
        products = db.query(Product).limit(3).all()
        
        for i, product in enumerate(products):
            # Create different types of alerts
            alert_types = [
                (AlertType.LOW_STOCK, AlertSeverity.MEDIUM, f"Low stock alert for {product.name}"),
                (AlertType.RUSH_HOUR, AlertSeverity.LOW, f"Rush hour predicted for {product.name}"),
                (AlertType.SYSTEM_ERROR, AlertSeverity.HIGH, f"System error related to {product.name}")
            ]
            
            alert_type, severity, message = alert_types[i % len(alert_types)]
            
            await alert_dispatcher.create_alert(
                db=db,
                alert_type=alert_type,
                severity=severity,
                title=f"Sample Alert: {product.name}",
                message=message,
                product_id=product.id,
                details={
                    "product_sku": product.sku,
                    "current_stock": random.randint(1, 10),
                    "threshold": product.min_stock_level
                }
            )
    
    print("✅ Created sample alerts")


async def main():
    """Main function to populate sample data."""
    print("🎯 ShopTrack Sample Data Population")
    print("=" * 50)
    
    try:
        # Initialize database
        print("📊 Initializing database...")
        init_db()
        
        # Create sample products
        print("\n🛍️  Creating sample products...")
        create_sample_products()
        
        # Create sample sales
        print("\n💰 Creating sample sales...")
        await create_sample_sales()
        
        # Create sample alerts
        print("\n🚨 Creating sample alerts...")
        await create_sample_alerts()
        
        print("\n🎉 Sample data population completed successfully!")
        print("\n📊 You can now:")
        print("   - View the dashboard at http://localhost:8050")
        print("   - Check the API at http://localhost:8000/docs")
        print("   - Test the ML predictions")
        
    except Exception as e:
        print(f"❌ Error populating sample data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 