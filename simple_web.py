#!/usr/bin/env python3
"""
Simple Web Version of ShopTrack - Works without pandas
"""
import json
import datetime
import random
import csv
import math
from typing import Dict, List
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="ShopTrack", description="Real-Time Inventory & Checkout Prediction")

class MLPredictor:
    """Simple ML predictor for peak checkout times."""
    
    def __init__(self):
        self.hourly_patterns = {}
        self.seasonal_factors = {}
        self.weather_factors = {}
        self.initialize_patterns()
    
    def initialize_patterns(self):
        """Initialize prediction patterns based on retail data."""
        # Base hourly patterns (typical retail patterns)
        self.hourly_patterns = {
            6: 0.1,  7: 0.2,  8: 0.4,  9: 0.6,  10: 0.8, 11: 0.9,
            12: 1.0, 13: 0.9, 14: 0.7, 15: 0.8, 16: 0.9, 17: 1.0,
            18: 0.9, 19: 0.8, 20: 0.6, 21: 0.4, 22: 0.2, 23: 0.1,
            0: 0.05, 1: 0.02, 2: 0.01, 3: 0.01, 4: 0.01, 5: 0.05
        }
        
        # Seasonal factors
        self.seasonal_factors = {
            'Spring': 1.1, 'Summer': 1.2, 'Autumn': 1.0, 'Winter': 0.9
        }
        
        # Weather factors
        self.weather_factors = {
            'Sunny': 1.1, 'Cloudy': 1.0, 'Rainy': 0.8, 'Snowy': 0.6
        }
    
    def predict_peak_hours(self, historical_sales=None, current_weather='Sunny', current_season='Autumn') -> List[Dict]:
        """Predict peak checkout hours using ML patterns."""
        predictions = []
        
        # Get current time
        now = datetime.datetime.now()
        current_hour = now.hour
        
        # Calculate base predictions for next 24 hours
        for hour in range(24):
            # Base probability from hourly patterns
            base_prob = self.hourly_patterns.get(hour, 0.1)
            
            # Apply seasonal factor
            seasonal_factor = self.seasonal_factors.get(current_season, 1.0)
            
            # Apply weather factor
            weather_factor = self.weather_factors.get(current_weather, 1.0)
            
            # Apply time-based adjustments
            time_factor = 1.0
            if hour == 12 or hour == 17:  # Lunch and dinner rush
                time_factor = 1.3
            elif hour == 9 or hour == 15:  # Morning and afternoon peaks
                time_factor = 1.2
            elif hour >= 22 or hour <= 6:  # Late night/early morning
                time_factor = 0.3
            
            # Calculate final probability
            final_prob = base_prob * seasonal_factor * weather_factor * time_factor
            
            # Normalize to 0-1 range
            final_prob = min(1.0, max(0.0, final_prob))
            
            # Only include hours with significant probability
            if final_prob > 0.3:
                predictions.append({
                    "hour": hour,
                    "probability": final_prob,
                    "confidence": self.calculate_confidence(final_prob),
                    "time_period": self.get_time_period(hour),
                    "factors": {
                        "base_probability": base_prob,
                        "seasonal_factor": seasonal_factor,
                        "weather_factor": weather_factor,
                        "time_factor": time_factor
                    },
                    "recommendation": self.get_recommendation(final_prob, hour)
                })
        
        # Sort by probability (highest first)
        predictions.sort(key=lambda x: x['probability'], reverse=True)
        
        return predictions[:8]  # Return top 8 predictions
    
    def calculate_confidence(self, probability: float) -> str:
        """Calculate confidence level based on probability."""
        if probability >= 0.8:
            return "Very High"
        elif probability >= 0.6:
            return "High"
        elif probability >= 0.4:
            return "Medium"
        else:
            return "Low"
    
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
    
    def get_recommendation(self, probability: float, hour: int) -> str:
        """Get staffing recommendation based on prediction."""
        if probability >= 0.8:
            return "High staffing recommended"
        elif probability >= 0.6:
            return "Moderate staffing recommended"
        elif probability >= 0.4:
            return "Normal staffing sufficient"
        else:
            return "Minimal staffing needed"
    
    def update_patterns(self, new_sales_data: List[Dict]):
        """Update patterns based on new sales data (simple learning)."""
        if not new_sales_data:
            return
        
        # Simple pattern update based on recent sales
        hourly_counts = {}
        for sale in new_sales_data[-50:]:  # Last 50 sales
            try:
                hour = datetime.datetime.fromisoformat(sale['timestamp']).hour
                hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
            except:
                continue
        
        # Update patterns if we have new data
        if hourly_counts:
            max_count = max(hourly_counts.values())
            for hour, count in hourly_counts.items():
                if max_count > 0:
                    new_prob = count / max_count
                    # Blend with existing pattern (simple moving average)
                    current_prob = self.hourly_patterns.get(hour, 0.1)
                    self.hourly_patterns[hour] = (current_prob * 0.7) + (new_prob * 0.3)

class SimpleWebShopTrack:
    """Simple web version of ShopTrack."""
    
    def __init__(self):
        self.current_inventory = {}
        self.sales_data = []
        self.alerts = []
        self.ml_predictor = MLPredictor()
        self.load_sample_data()
        
    def load_sample_data(self):
        """Load sample data without pandas."""
        try:
            # Create sample inventory based on your retail data structure
            self.current_inventory = {
                "P0001 - Groceries": {"product_id": "P0001", "category": "Groceries", "stock": 231, "price": 33.5, "min_stock": 46, "region": "North"},
                "P0002 - Toys": {"product_id": "P0002", "category": "Toys", "stock": 204, "price": 63.01, "min_stock": 41, "region": "South"},
                "P0003 - Toys": {"product_id": "P0003", "category": "Toys", "stock": 102, "price": 27.99, "min_stock": 20, "region": "West"},
                "P0004 - Toys": {"product_id": "P0004", "category": "Toys", "stock": 469, "price": 32.72, "min_stock": 94, "region": "North"},
                "P0005 - Electronics": {"product_id": "P0005", "category": "Electronics", "stock": 166, "price": 73.64, "min_stock": 33, "region": "East"},
                "P0006 - Groceries": {"product_id": "P0006", "category": "Groceries", "stock": 138, "price": 76.83, "min_stock": 28, "region": "South"},
                "P0007 - Furniture": {"product_id": "P0007", "category": "Furniture", "stock": 359, "price": 34.16, "min_stock": 72, "region": "East"},
                "P0008 - Clothing": {"product_id": "P0008", "category": "Clothing", "stock": 380, "price": 97.99, "min_stock": 76, "region": "North"},
                "P0009 - Electronics": {"product_id": "P0009", "category": "Electronics", "stock": 183, "price": 20.74, "min_stock": 37, "region": "West"},
                "P0010 - Toys": {"product_id": "P0010", "category": "Toys", "stock": 108, "price": 59.99, "min_stock": 22, "region": "South"}
            }
            print(f"✅ Loaded {len(self.current_inventory)} sample products")
        except Exception as e:
            print(f"❌ Error loading data: {e}")
    
    def record_sale(self, items: List[Dict]) -> Dict:
        """Record a sale transaction."""
        sale_id = f"TXN-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        total = 0
        
        for item in items:
            product_key = item['product_key']
            quantity = item['quantity']
            
            if product_key in self.current_inventory:
                price = self.current_inventory[product_key]['price']
                total += quantity * price
                self.current_inventory[product_key]['stock'] -= quantity
                
                # Check for low stock alert
                if self.current_inventory[product_key]['stock'] <= self.current_inventory[product_key]['min_stock']:
                    self.alerts.append({
                        "type": "low_stock",
                        "product": product_key,
                        "current_stock": self.current_inventory[product_key]['stock'],
                        "timestamp": datetime.datetime.now().isoformat()
                    })
        
        sale = {
            "id": sale_id,
            "items": items,
            "total": total,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.sales_data.append(sale)
        
        # Update ML patterns with new sale data
        self.ml_predictor.update_patterns(self.sales_data)
        
        return sale
    
    def get_dashboard_data(self) -> Dict:
        """Get dashboard data."""
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
        
        # Get ML predictions
        peak_predictions = self.ml_predictor.predict_peak_hours(
            historical_sales=self.sales_data,
            current_weather='Sunny',  # Could be made dynamic
            current_season='Autumn'   # Could be made dynamic
        )
        
        return {
            "total_sales_today": len(today_sales),
            "revenue_today": sum(s['total'] for s in today_sales),
            "low_stock_alerts": low_stock_count,
            "total_products": len(self.current_inventory),
            "inventory_status": inventory_status,
            "recent_sales": self.sales_data[-5:],
            "categories": self.get_category_summary(),
            "peak_predictions": peak_predictions,
            "ml_insights": self.get_ml_insights()
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
    
    def get_ml_insights(self) -> Dict:
        """Get ML insights and recommendations."""
        now = datetime.datetime.now()
        current_hour = now.hour
        
        # Get current prediction
        current_prediction = None
        peak_predictions = self.ml_predictor.predict_peak_hours(self.sales_data)
        
        for pred in peak_predictions:
            if pred['hour'] == current_hour:
                current_prediction = pred
                break
        
        return {
            "current_hour": current_hour,
            "current_prediction": current_prediction,
            "next_peak_hour": peak_predictions[0] if peak_predictions else None,
            "total_predictions": len(peak_predictions),
            "model_confidence": "High" if len(self.sales_data) > 10 else "Medium",
            "recommendations": self.get_staffing_recommendations(peak_predictions)
        }
    
    def get_staffing_recommendations(self, predictions: List[Dict]) -> List[str]:
        """Get staffing recommendations based on predictions."""
        recommendations = []
        
        if not predictions:
            return ["No peak hours predicted"]
        
        # Current hour recommendation
        now = datetime.datetime.now()
        current_hour = now.hour
        
        for pred in predictions:
            if pred['hour'] == current_hour:
                if pred['probability'] >= 0.7:
                    recommendations.append(f"🚨 HIGH RUSH NOW: {pred['recommendation']}")
                elif pred['probability'] >= 0.5:
                    recommendations.append(f"⚠️ Moderate activity: {pred['recommendation']}")
                else:
                    recommendations.append(f"✅ Normal activity: {pred['recommendation']}")
                break
        
        # Next peak recommendation
        if predictions:
            next_peak = predictions[0]
            if next_peak['hour'] != current_hour:
                time_diff = next_peak['hour'] - current_hour
                if time_diff < 0:
                    time_diff += 24
                
                if time_diff <= 2:
                    recommendations.append(f"⏰ Peak in {time_diff} hour(s): {next_peak['recommendation']}")
                else:
                    recommendations.append(f"📅 Next peak at {next_peak['hour']:02d}:00 ({next_peak['time_period']})")
        
        return recommendations

# Create global instance
shop_track = SimpleWebShopTrack()

@app.get("/", response_class=HTMLResponse)
async def root():
    """Main dashboard page."""
    dashboard = shop_track.get_dashboard_data()
    
    # Generate product options for the sale form
    product_options = ""
    for product_key, data in shop_track.current_inventory.items():
        if data['stock'] > 0:  # Only show products with stock
            product_options += f'<option value="{product_key}">{product_key} - ${data["price"]:.2f} (Stock: {data["stock"]})</option>'
    
    # Generate peak predictions HTML
    peak_predictions_html = ""
    for pred in dashboard['peak_predictions']:
        confidence_color = {
            "Very High": "#28a745",
            "High": "#17a2b8", 
            "Medium": "#ffc107",
            "Low": "#dc3545"
        }.get(pred['confidence'], "#6c757d")
        
        peak_predictions_html += f"""
        <div class="prediction-item" style="border-left: 4px solid {confidence_color}; padding: 10px; margin: 5px 0; background: #f8f9fa;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>{pred['hour']:02d}:00 ({pred['time_period']})</strong>
                    <br><small>Confidence: {pred['confidence']}</small>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 1.2em; font-weight: bold; color: {confidence_color};">
                        {pred['probability']:.1%}
                    </div>
                    <small>{pred['recommendation']}</small>
                </div>
            </div>
        </div>
        """
    
    # Generate ML insights HTML
    ml_insights_html = ""
    for rec in dashboard['ml_insights']['recommendations']:
        ml_insights_html += f'<div class="alert" style="margin: 5px 0;">{rec}</div>'
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ShopTrack Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }}
            .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
            .stat-number {{ font-size: 2em; font-weight: bold; color: #667eea; }}
            .section {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            .inventory-item {{ display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #eee; }}
            .category-item {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .sale-item {{ background: #e8f5e8; padding: 10px; margin: 5px 0; border-radius: 5px; }}
            .alert {{ background: #ffe6e6; padding: 10px; margin: 5px 0; border-radius: 5px; color: #d63031; }}
            .prediction-item {{ border-radius: 5px; }}
            button {{ background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }}
            button:hover {{ background: #5a6fd8; }}
            .sale-form {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; }}
            .form-group {{ margin-bottom: 15px; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            select, input {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
            .item-row {{ display: flex; gap: 10px; margin-bottom: 10px; }}
            .item-row select {{ flex: 2; }}
            .item-row input {{ flex: 1; }}
            .remove-btn {{ background: #dc3545; padding: 8px 12px; }}
            .add-btn {{ background: #28a745; }}
            .submit-btn {{ background: #007bff; width: 100%; padding: 12px; font-size: 16px; }}
            .tabs {{ display: flex; margin-bottom: 20px; }}
            .tab {{ flex: 1; padding: 10px; text-align: center; background: #ddd; cursor: pointer; }}
            .tab.active {{ background: #667eea; color: white; }}
            .tab-content {{ display: none; }}
            .tab-content.active {{ display: block; }}
            .ml-section {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 10px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 ShopTrack Dashboard</h1>
                <p>Real-Time Inventory & Checkout Prediction with ML</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{dashboard['total_sales_today']}</div>
                    <div>Sales Today</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${dashboard['revenue_today']:.2f}</div>
                    <div>Revenue Today</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{dashboard['low_stock_alerts']}</div>
                    <div>Low Stock Alerts</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{dashboard['total_products']}</div>
                    <div>Total Products</div>
                </div>
            </div>
            
            <div class="tabs">
                <div class="tab active" onclick="showTab('dashboard')">📊 Dashboard</div>
                <div class="tab" onclick="showTab('predictions')">🤖 ML Predictions</div>
                <div class="tab" onclick="showTab('create-sale')">🛍️ Create Sale</div>
                <div class="tab" onclick="showTab('inventory')">📦 Inventory</div>
            </div>
            
            <div id="dashboard" class="tab-content active">
                <div class="section">
                    <h2>📦 Inventory Status</h2>
                    {''.join([f'<div class="inventory-item"><span>{data["status"]} {product}</span><span>{data["stock"]} units (${data["price"]:.2f})</span></div>' for product, data in list(dashboard['inventory_status'].items())[:10]])}
                </div>
                
                <div class="section">
                    <h2>📈 Category Summary</h2>
                    {''.join([f'<div class="category-item"><strong>{category}</strong>: {summary["total_products"]} products, {summary["total_stock"]} units, ${summary["total_value"]:.2f} value</div>' for category, summary in dashboard['categories'].items()])}
                </div>
                
                <div class="section">
                    <h2>💰 Recent Sales</h2>
                    {''.join([f'<div class="sale-item">{sale["id"]}: ${sale["total"]:.2f}</div>' for sale in dashboard['recent_sales']])}
                </div>
                
                <div class="section">
                    <h2>🚨 Active Alerts</h2>
                    {''.join([f'<div class="alert">⚠️ {alert["product"]} is low on stock ({alert["current_stock"]} units)</div>' for alert in shop_track.alerts[-dashboard['low_stock_alerts']:]]) if dashboard['low_stock_alerts'] > 0 else '<p>No active alerts</p>'}
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <button onclick="location.reload()">🔄 Refresh Dashboard</button>
                    <button onclick="generateSale()">🎲 Generate Random Sale</button>
                </div>
            </div>
            
            <div id="predictions" class="tab-content">
                <div class="ml-section">
                    <h2>🤖 ML-Powered Peak Checkout Predictions</h2>
                    <p>AI-driven insights for optimal staffing and customer experience</p>
                </div>
                
                <div class="section">
                    <h2>⏰ Peak Hour Predictions (Next 24 Hours)</h2>
                    {peak_predictions_html}
                </div>
                
                <div class="section">
                    <h2>💡 Smart Recommendations</h2>
                    {ml_insights_html}
                </div>
                
                <div class="section">
                    <h2>📊 ML Model Insights</h2>
                    <div class="category-item">
                        <strong>Model Confidence:</strong> {dashboard['ml_insights']['model_confidence']}<br>
                        <strong>Total Predictions:</strong> {dashboard['ml_insights']['total_predictions']}<br>
                        <strong>Current Hour:</strong> {dashboard['ml_insights']['current_hour']:02d}:00<br>
                        <strong>Data Points:</strong> {len(shop_track.sales_data)} sales analyzed
                    </div>
                </div>
            </div>
            
            <div id="create-sale" class="tab-content">
                <div class="sale-form">
                    <h2>🛍️ Create New Sale</h2>
                    <form id="saleForm" onsubmit="createSale(event)">
                        <div id="items-container">
                            <div class="item-row">
                                <select name="product" required>
                                    <option value="">Select Product</option>
                                    {product_options}
                                </select>
                                <input type="number" name="quantity" placeholder="Qty" min="1" required>
                                <button type="button" class="remove-btn" onclick="removeItem(this)" style="display: none;">❌</button>
                            </div>
                        </div>
                        <button type="button" class="add-btn" onclick="addItem()">➕ Add Item</button>
                        <button type="submit" class="submit-btn">💳 Complete Sale</button>
                    </form>
                </div>
            </div>
            
            <div id="inventory" class="tab-content">
                <div class="section">
                    <h2>📦 Full Inventory Status</h2>
                    {''.join([f'<div class="inventory-item"><span>{data["status"]} {product}</span><span>{data["stock"]} units (${data["price"]:.2f}) - Min: {data["min_stock"]}</span></div>' for product, data in dashboard['inventory_status'].items()])}
                </div>
            </div>
        </div>
        
        <script>
            function showTab(tabName) {{
                // Hide all tab contents
                document.querySelectorAll('.tab-content').forEach(content => {{
                    content.classList.remove('active');
                }});
                
                // Remove active class from all tabs
                document.querySelectorAll('.tab').forEach(tab => {{
                    tab.classList.remove('active');
                }});
                
                // Show selected tab content
                document.getElementById(tabName).classList.add('active');
                
                // Add active class to clicked tab
                event.target.classList.add('active');
            }}
            
            function generateSale() {{
                fetch('/api/generate-sale', {{method: 'POST'}})
                    .then(response => response.json())
                    .then(data => {{
                        alert('Random sale generated: $' + data.total.toFixed(2));
                        location.reload();
                    }});
            }}
            
            function addItem() {{
                const container = document.getElementById('items-container');
                const newRow = document.createElement('div');
                newRow.className = 'item-row';
                newRow.innerHTML = `
                    <select name="product" required>
                        <option value="">Select Product</option>
                        {product_options}
                    </select>
                    <input type="number" name="quantity" placeholder="Qty" min="1" required>
                    <button type="button" class="remove-btn" onclick="removeItem(this)">❌</button>
                `;
                container.appendChild(newRow);
                
                // Show remove buttons if more than one item
                if (container.children.length > 1) {{
                    document.querySelectorAll('.remove-btn').forEach(btn => {{
                        btn.style.display = 'block';
                    }});
                }}
            }}
            
            function removeItem(button) {{
                const container = document.getElementById('items-container');
                button.parentElement.remove();
                
                // Hide remove buttons if only one item left
                if (container.children.length === 1) {{
                    document.querySelectorAll('.remove-btn').forEach(btn => {{
                        btn.style.display = 'none';
                    }});
                }}
            }}
            
            function createSale(event) {{
                event.preventDefault();
                
                const formData = new FormData(event.target);
                const items = [];
                
                // Get all product-quantity pairs
                const products = formData.getAll('product');
                const quantities = formData.getAll('quantity');
                
                for (let i = 0; i < products.length; i++) {{
                    if (products[i] && quantities[i]) {{
                        items.push({{
                            product_key: products[i],
                            quantity: parseInt(quantities[i])
                        }});
                    }}
                }}
                
                if (items.length === 0) {{
                    alert('Please select at least one product');
                    return;
                }}
                
                fetch('/api/create-sale', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{items: items}})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        alert('Sale created successfully: $' + data.total.toFixed(2));
                        location.reload();
                    }} else {{
                        alert('Error: ' + data.error);
                    }}
                }})
                .catch(error => {{
                    alert('Error creating sale: ' + error);
                }});
            }}
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

@app.get("/api/dashboard")
async def get_dashboard():
    """Get dashboard data as JSON."""
    return shop_track.get_dashboard_data()

@app.get("/api/predictions")
async def get_predictions():
    """Get ML predictions."""
    predictions = shop_track.ml_predictor.predict_peak_hours(shop_track.sales_data)
    return {
        "predictions": predictions,
        "insights": shop_track.get_ml_insights(),
        "model_info": {
            "total_sales_analyzed": len(shop_track.sales_data),
            "confidence": "High" if len(shop_track.sales_data) > 10 else "Medium"
        }
    }

@app.post("/api/generate-sale")
async def generate_sale():
    """Generate a random sale."""
    available_products = list(shop_track.current_inventory.keys())
    num_items = random.randint(1, 3)
    items = []
    
    for _ in range(num_items):
        product_key = random.choice(available_products)
        max_quantity = min(3, shop_track.current_inventory[product_key]['stock'])
        if max_quantity > 0:
            quantity = random.randint(1, max_quantity)
            items.append({
                "product_key": product_key,
                "quantity": quantity,
                "price": shop_track.current_inventory[product_key]['price']
            })
    
    if items:
        sale = shop_track.record_sale(items)
        return {"success": True, "sale": sale, "total": sale['total']}
    else:
        raise HTTPException(status_code=400, detail="No items available for sale")

@app.post("/api/create-sale")
async def create_sale(items_data: dict):
    """Create a sale with user-selected items."""
    try:
        items = items_data.get('items', [])
        
        if not items:
            return {"success": False, "error": "No items provided"}
        
        # Validate items
        for item in items:
            product_key = item.get('product_key')
            quantity = item.get('quantity', 0)
            
            if not product_key or product_key not in shop_track.current_inventory:
                return {"success": False, "error": f"Invalid product: {product_key}"}
            
            if quantity <= 0:
                return {"success": False, "error": f"Invalid quantity for {product_key}"}
            
            if quantity > shop_track.current_inventory[product_key]['stock']:
                return {"success": False, "error": f"Insufficient stock for {product_key}"}
        
        # Create the sale
        sale = shop_track.record_sale(items)
        return {"success": True, "sale": sale, "total": sale['total']}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/inventory")
async def get_inventory():
    """Get current inventory."""
    return shop_track.current_inventory

@app.get("/api/sales")
async def get_sales():
    """Get recent sales."""
    return shop_track.sales_data[-10:]  # Last 10 sales

if __name__ == "__main__":
    print("🚀 Starting ShopTrack Web Server...")
    print("📊 Dashboard: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔍 Health: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 