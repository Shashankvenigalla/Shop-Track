#!/usr/bin/env python3
"""
Simplified ShopTrack Demo - Works with basic Python installation
"""
import json
import datetime
import random
import time
from typing import Dict, List

class SimpleShopTrack:
    """Simplified version of ShopTrack for demonstration."""
    
    def __init__(self):
        self.sales_data = []
        self.inventory = {
            "Milk": {"stock": 50, "price": 3.99, "min_stock": 10},
            "Bread": {"stock": 30, "price": 4.50, "min_stock": 15},
            "Coffee": {"stock": 25, "price": 12.99, "min_stock": 8},
            "Soap": {"stock": 40, "price": 6.99, "min_stock": 20},
            "Water": {"stock": 100, "price": 1.99, "min_stock": 25}
        }
        self.alerts = []
        
    def record_sale(self, items: List[Dict]) -> Dict:
        """Record a sale transaction."""
        sale_id = f"TXN-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        total = sum(item['quantity'] * item['price'] for item in items)
        
        # Update inventory
        for item in items:
            product = item['product']
            quantity = item['quantity']
            self.inventory[product]['stock'] -= quantity
            
            # Check for low stock alert
            if self.inventory[product]['stock'] <= self.inventory[product]['min_stock']:
                self.alerts.append({
                    "type": "low_stock",
                    "product": product,
                    "current_stock": self.inventory[product]['stock'],
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
        """Simple rush hour prediction based on historical data."""
        # Analyze sales by hour
        hourly_sales = {}
        for sale in self.sales_data[-50:]:  # Last 50 sales
            hour = datetime.datetime.fromisoformat(sale['timestamp']).hour
            hourly_sales[hour] = hourly_sales.get(hour, 0) + 1
        
        # Predict rush hours (hours with most sales)
        rush_hours = []
        for hour in range(24):
            sales_count = hourly_sales.get(hour, 0)
            probability = min(sales_count / 10, 1.0)  # Normalize to 0-1
            if probability > 0.3:  # Threshold for rush hour
                rush_hours.append({
                    "hour": hour,
                    "probability": probability,
                    "predicted_sales": sales_count
                })
        
        return sorted(rush_hours, key=lambda x: x['probability'], reverse=True)
    
    def get_dashboard_data(self) -> Dict:
        """Get dashboard data for display."""
        today = datetime.datetime.now().date()
        today_sales = [s for s in self.sales_data 
                      if datetime.datetime.fromisoformat(s['timestamp']).date() == today]
        
        return {
            "total_sales_today": len(today_sales),
            "revenue_today": sum(s['total'] for s in today_sales),
            "low_stock_alerts": len([a for a in self.alerts if a['type'] == 'low_stock']),
            "inventory_status": self.inventory,
            "recent_sales": self.sales_data[-5:],  # Last 5 sales
            "rush_hours": self.predict_rush_hours()[:5]  # Top 5 rush hours
        }
    
    def generate_sample_data(self):
        """Generate sample sales data for demonstration."""
        products = list(self.inventory.keys())
        
        print("🛍️  Generating sample sales data...")
        for i in range(20):
            # Random sale
            num_items = random.randint(1, 3)
            items = []
            for _ in range(num_items):
                product = random.choice(products)
                quantity = random.randint(1, 3)
                price = self.inventory[product]['price']
                items.append({
                    "product": product,
                    "quantity": quantity,
                    "price": price
                })
            
            sale = self.record_sale(items)
            print(f"✅ Sale {sale['id']}: ${sale['total']:.2f}")
            time.sleep(0.1)  # Small delay for demo effect

def main():
    """Main demo function."""
    print("🎯 ShopTrack - Real-Time Inventory & Checkout Prediction")
    print("=" * 60)
    print("🚀 Starting simplified demo...")
    
    # Create ShopTrack instance
    shop = SimpleShopTrack()
    
    # Generate sample data
    shop.generate_sample_data()
    
    # Get dashboard data
    dashboard = shop.get_dashboard_data()
    
    # Display results
    print("\n📊 Dashboard Summary:")
    print(f"   Total Sales Today: {dashboard['total_sales_today']}")
    print(f"   Revenue Today: ${dashboard['revenue_today']:.2f}")
    print(f"   Low Stock Alerts: {dashboard['low_stock_alerts']}")
    
    print("\n📦 Inventory Status:")
    for product, data in dashboard['inventory_status'].items():
        status = "🟢" if data['stock'] > data['min_stock'] else "🔴"
        print(f"   {status} {product}: {data['stock']} units (${data['price']})")
    
    print("\n⏰ Rush Hour Predictions:")
    for rush in dashboard['rush_hours']:
        print(f"   {rush['hour']:02d}:00 - {rush['probability']:.1%} probability")
    
    print("\n💰 Recent Sales:")
    for sale in dashboard['recent_sales']:
        print(f"   {sale['id']}: ${sale['total']:.2f}")
    
    if dashboard['low_stock_alerts'] > 0:
        print(f"\n🚨 Active Alerts: {dashboard['low_stock_alerts']}")
        for alert in shop.alerts[-dashboard['low_stock_alerts']:]:
            print(f"   ⚠️  {alert['product']} is low on stock ({alert['current_stock']} units)")
    
    print("\n🎉 ShopTrack Demo Complete!")
    print("📈 This demonstrates the core features:")
    print("   • Real-time sales tracking")
    print("   • Inventory management")
    print("   • Rush hour prediction")
    print("   • Alert system")
    print("   • Dashboard analytics")

if __name__ == "__main__":
    main() 