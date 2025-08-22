#!/usr/bin/env python3
"""
ShopTrack with Real Retail Data - Uses actual inventory and sales data
"""
import pandas as pd
import json
import datetime
import random
import time
from typing import Dict, List
import os

class RealDataShopTrack:
    """ShopTrack using real retail inventory data."""
    
    def __init__(self):
        self.retail_data = None
        self.current_inventory = {}
        self.sales_data = []
        self.alerts = []
        self.load_retail_data()
        
    def load_retail_data(self):
        """Load retail data from CSV file."""
        try:
            print("📊 Loading real retail data...")
            self.retail_data = pd.read_csv('retail_data_sample.csv')
            
            # Create current inventory from the data
            for _, row in self.retail_data.iterrows():
                product_key = f"{row['Product ID']} - {row['Category']}"
                if product_key not in self.current_inventory:
                    self.current_inventory[product_key] = {
                        "product_id": row['Product ID'],
                        "category": row['Category'],
                        "region": row['Region'],
                        "stock": row['Inventory Level'],
                        "price": row['Price'],
                        "discount": row['Discount'],
                        "demand_forecast": row['Demand Forecast'],
                        "min_stock": max(10, int(row['Inventory Level'] * 0.2)),  # 20% of current stock as minimum
                        "store_id": row['Store ID']
                    }
            
            print(f"✅ Loaded {len(self.current_inventory)} products from real data")
            
        except Exception as e:
            print(f"❌ Error loading retail data: {e}")
            # Fallback to sample data
            self.create_fallback_data()
    
    def create_fallback_data(self):
        """Create fallback data if CSV loading fails."""
        print("⚠️  Using fallback data...")
        self.current_inventory = {
            "P0001 - Groceries": {"product_id": "P0001", "category": "Groceries", "stock": 231, "price": 33.5, "min_stock": 46},
            "P0002 - Toys": {"product_id": "P0002", "category": "Toys", "stock": 204, "price": 63.01, "min_stock": 41},
            "P0003 - Toys": {"product_id": "P0003", "category": "Toys", "stock": 102, "price": 27.99, "min_stock": 20},
            "P0004 - Toys": {"product_id": "P0004", "category": "Toys", "stock": 469, "price": 32.72, "min_stock": 94},
            "P0005 - Electronics": {"product_id": "P0005", "category": "Electronics", "stock": 166, "price": 73.64, "min_stock": 33}
        }
    
    def record_sale(self, items: List[Dict]) -> Dict:
        """Record a sale transaction using real product data."""
        sale_id = f"TXN-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        total = 0
        
        # Update inventory
        for item in items:
            product_key = item['product_key']
            quantity = item['quantity']
            
            if product_key in self.current_inventory:
                # Apply discount if available
                discount = self.current_inventory[product_key].get('discount', 0)
                price = self.current_inventory[product_key]['price']
                discounted_price = price * (1 - discount / 100)
                
                total += quantity * discounted_price
                self.current_inventory[product_key]['stock'] -= quantity
                
                # Check for low stock alert
                if self.current_inventory[product_key]['stock'] <= self.current_inventory[product_key]['min_stock']:
                    self.alerts.append({
                        "type": "low_stock",
                        "product": product_key,
                        "current_stock": self.current_inventory[product_key]['stock'],
                        "min_stock": self.current_inventory[product_key]['min_stock'],
                        "timestamp": datetime.datetime.now().isoformat()
                    })
        
        sale = {
            "id": sale_id,
            "items": items,
            "total": total,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.sales_data.append(sale)
        
        return sale
    
    def predict_rush_hours(self) -> List[Dict]:
        """Predict rush hours based on real sales patterns."""
        # Analyze sales by hour from real data
        hourly_sales = {}
        
        # Use real data patterns if available
        if self.retail_data is not None:
            # Group by hour and sum units sold
            self.retail_data['Hour'] = pd.to_datetime(self.retail_data['Date']).dt.hour
            hourly_patterns = self.retail_data.groupby('Hour')['Units Sold'].sum()
            
            for hour, sales in hourly_patterns.items():
                hourly_sales[hour] = sales
        else:
            # Fallback to generated patterns
            for sale in self.sales_data[-50:]:
                hour = datetime.datetime.fromisoformat(sale['timestamp']).hour
                hourly_sales[hour] = hourly_sales.get(hour, 0) + 1
        
        # Predict rush hours
        rush_hours = []
        max_sales = max(hourly_sales.values()) if hourly_sales else 1
        
        for hour in range(24):
            sales_count = hourly_sales.get(hour, 0)
            probability = sales_count / max_sales if max_sales > 0 else 0
            
            if probability > 0.3:  # Threshold for rush hour
                rush_hours.append({
                    "hour": hour,
                    "probability": probability,
                    "predicted_sales": sales_count,
                    "time_period": self.get_time_period(hour)
                })
        
        return sorted(rush_hours, key=lambda x: x['probability'], reverse=True)
    
    def get_time_period(self, hour: int) -> str:
        """Get time period description."""
        if 6 <= hour < 12:
            return "Morning"
        elif 12 <= hour < 17:
            return "Afternoon"
        elif 17 <= hour < 21:
            return "Evening"
        else:
            return "Night"
    
    def get_dashboard_data(self) -> Dict:
        """Get dashboard data using real inventory."""
        today = datetime.datetime.now().date()
        today_sales = [s for s in self.sales_data 
                      if datetime.datetime.fromisoformat(s['timestamp']).date() == today]
        
        # Calculate inventory status
        inventory_status = {}
        low_stock_count = 0
        
        for product_key, data in self.current_inventory.items():
            status = "🟢" if data['stock'] > data['min_stock'] else "🔴"
            if data['stock'] <= data['min_stock']:
                low_stock_count += 1
            
            inventory_status[product_key] = {
                "stock": data['stock'],
                "price": data['price'],
                "category": data['category'],
                "status": status,
                "min_stock": data['min_stock']
            }
        
        return {
            "total_sales_today": len(today_sales),
            "revenue_today": sum(s['total'] for s in today_sales),
            "low_stock_alerts": low_stock_count,
            "total_products": len(self.current_inventory),
            "inventory_status": inventory_status,
            "recent_sales": self.sales_data[-5:],  # Last 5 sales
            "rush_hours": self.predict_rush_hours()[:5],  # Top 5 rush hours
            "categories": self.get_category_summary()
        }
    
    def get_category_summary(self) -> Dict:
        """Get summary by product category."""
        categories = {}
        for product_key, data in self.current_inventory.items():
            category = data['category']
            if category not in categories:
                categories[category] = {
                    "total_products": 0,
                    "total_stock": 0,
                    "total_value": 0,
                    "low_stock_count": 0
                }
            
            categories[category]["total_products"] += 1
            categories[category]["total_stock"] += data['stock']
            categories[category]["total_value"] += data['stock'] * data['price']
            
            if data['stock'] <= data['min_stock']:
                categories[category]["low_stock_count"] += 1
        
        return categories
    
    def generate_realistic_sales(self):
        """Generate realistic sales based on actual inventory data."""
        print("🛍️  Generating realistic sales from retail data...")
        
        # Get list of available products
        available_products = list(self.current_inventory.keys())
        
        # Generate sales based on real patterns
        for i in range(15):  # Generate 15 sales
            # Random number of items in sale (1-3)
            num_items = random.randint(1, 3)
            items = []
            
            for _ in range(num_items):
                product_key = random.choice(available_products)
                # Quantity based on current stock (don't oversell)
                max_quantity = min(3, self.current_inventory[product_key]['stock'])
                if max_quantity > 0:
                    quantity = random.randint(1, max_quantity)
                    items.append({
                        "product_key": product_key,
                        "quantity": quantity,
                        "price": self.current_inventory[product_key]['price']
                    })
            
            if items:  # Only record sale if we have items
                sale = self.record_sale(items)
                print(f"✅ Sale {sale['id']}: ${sale['total']:.2f} ({len(items)} items)")
                time.sleep(0.2)  # Small delay for demo effect

def main():
    """Main demo function with real retail data."""
    print("🎯 ShopTrack - Real-Time Inventory & Checkout Prediction")
    print("📊 Using Real Retail Data")
    print("=" * 60)
    
    # Create ShopTrack instance with real data
    shop = RealDataShopTrack()
    
    # Generate realistic sales
    shop.generate_realistic_sales()
    
    # Get dashboard data
    dashboard = shop.get_dashboard_data()
    
    # Display results
    print("\n📊 Dashboard Summary:")
    print(f"   Total Sales Today: {dashboard['total_sales_today']}")
    print(f"   Revenue Today: ${dashboard['revenue_today']:.2f}")
    print(f"   Low Stock Alerts: {dashboard['low_stock_alerts']}")
    print(f"   Total Products: {dashboard['total_products']}")
    
    print("\n📦 Inventory Status (Sample):")
    # Show first 10 products
    for i, (product_key, data) in enumerate(dashboard['inventory_status'].items()):
        if i >= 10:  # Limit display
            break
        print(f"   {data['status']} {product_key}: {data['stock']} units (${data['price']:.2f})")
    
    print("\n📈 Category Summary:")
    for category, summary in dashboard['categories'].items():
        status = "🟢" if summary['low_stock_count'] == 0 else "🔴"
        print(f"   {status} {category}: {summary['total_products']} products, "
              f"{summary['total_stock']} units, ${summary['total_value']:.2f} value")
    
    print("\n⏰ Rush Hour Predictions:")
    for rush in dashboard['rush_hours']:
        print(f"   {rush['hour']:02d}:00 ({rush['time_period']}) - {rush['probability']:.1%} probability")
    
    print("\n💰 Recent Sales:")
    for sale in dashboard['recent_sales']:
        print(f"   {sale['id']}: ${sale['total']:.2f}")
    
    if dashboard['low_stock_alerts'] > 0:
        print(f"\n🚨 Active Alerts: {dashboard['low_stock_alerts']}")
        for alert in shop.alerts[-dashboard['low_stock_alerts']:]:
            print(f"   ⚠️  {alert['product']} is low on stock ({alert['current_stock']} units)")
    
    print("\n🎉 ShopTrack with Real Data Complete!")
    print("📈 This demonstrates:")
    print("   • Real inventory management")
    print("   • Actual product categories and pricing")
    print("   • Realistic sales patterns")
    print("   • Category-based analytics")
    print("   • Rush hour prediction based on real data")

if __name__ == "__main__":
    main() 