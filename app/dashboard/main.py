"""
ShopTrack Dashboard - Real-time visualization and monitoring.
"""
import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
import requests
import json
import asyncio
import threading
import time

from app.core.config import settings

# Initialize Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="ShopTrack Dashboard",
    update_title="ShopTrack - Loading..."
)

# API base URL
API_BASE_URL = f"http://localhost:8000{settings.api_v1_str}"

# Global data storage
dashboard_data = {
    "sales_summary": {},
    "inventory_status": [],
    "active_alerts": [],
    "rush_predictions": [],
    "recent_sales": []
}


def fetch_api_data(endpoint: str, params: dict = None) -> dict:
    """Fetch data from API endpoint."""
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data from {endpoint}: {e}")
        return {}


def update_dashboard_data():
    """Update dashboard data from API."""
    global dashboard_data
    
    try:
        # Fetch sales summary
        dashboard_data["sales_summary"] = fetch_api_data("sales/summary")
        
        # Fetch inventory status
        dashboard_data["inventory_status"] = fetch_api_data("inventory/status")
        
        # Fetch active alerts
        dashboard_data["active_alerts"] = fetch_api_data("alerts/active")
        
        # Fetch rush predictions
        dashboard_data["rush_predictions"] = fetch_api_data("predictions/rush-hours")
        
        # Fetch recent sales
        dashboard_data["recent_sales"] = fetch_api_data("sales/recent")
        
    except Exception as e:
        print(f"Error updating dashboard data: {e}")


# Background thread for data updates
def background_data_updater():
    """Background thread to update data every 30 seconds."""
    while True:
        update_dashboard_data()
        time.sleep(30)


# Start background thread
data_thread = threading.Thread(target=background_data_updater, daemon=True)
data_thread.start()

# Initial data load
update_dashboard_data()


# Dashboard layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("ShopTrack Dashboard", className="text-center mb-4"),
            html.Hr()
        ])
    ]),
    
    # Key Metrics Row
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Total Sales Today", className="card-title"),
                    html.H2(id="total-sales", children="0", className="text-primary"),
                    html.P("Transactions", className="card-text")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Revenue Today", className="card-title"),
                    html.H2(id="total-revenue", children="$0", className="text-success"),
                    html.P("Total Revenue", className="card-text")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Low Stock Items", className="card-title"),
                    html.H2(id="low-stock-count", children="0", className="text-warning"),
                    html.P("Items Need Restocking", className="card-text")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Active Alerts", className="card-title"),
                    html.H2(id="active-alerts-count", children="0", className="text-danger"),
                    html.P("System Alerts", className="card-text")
                ])
            ])
        ], width=3)
    ], className="mb-4"),
    
    # Charts Row
    dbc.Row([
        # Sales Chart
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Sales Trend (Last 7 Days)"),
                dbc.CardBody([
                    dcc.Graph(id="sales-chart")
                ])
            ])
        ], width=6),
        
        # Rush Hour Predictions
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Rush Hour Predictions"),
                dbc.CardBody([
                    dcc.Graph(id="rush-predictions-chart")
                ])
            ])
        ], width=6)
    ], className="mb-4"),
    
    # Inventory and Alerts Row
    dbc.Row([
        # Inventory Status
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Inventory Status"),
                dbc.CardBody([
                    html.Div(id="inventory-table")
                ])
            ])
        ], width=6),
        
        # Active Alerts
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Active Alerts"),
                dbc.CardBody([
                    html.Div(id="alerts-list")
                ])
            ])
        ], width=6)
    ], className="mb-4"),
    
    # Recent Sales
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Recent Sales"),
                dbc.CardBody([
                    html.Div(id="recent-sales-table")
                ])
            ])
        ])
    ]),
    
    # Hidden div for storing data
    html.Div(id="data-store", style={"display": "none"}),
    
    # Interval component for auto-refresh
    dcc.Interval(
        id="interval-component",
        interval=30*1000,  # 30 seconds
        n_intervals=0
    )
], fluid=True)


# Callbacks
@app.callback(
    [Output("total-sales", "children"),
     Output("total-revenue", "children"),
     Output("low-stock-count", "children"),
     Output("active-alerts-count", "children")],
    [Input("interval-component", "n_intervals")]
)
def update_metrics(n):
    """Update key metrics."""
    global dashboard_data
    
    # Calculate metrics from data
    total_sales = dashboard_data.get("sales_summary", {}).get("summary", {}).get("total_sales", 0)
    total_revenue = dashboard_data.get("sales_summary", {}).get("summary", {}).get("total_revenue", 0)
    low_stock_count = len([item for item in dashboard_data.get("inventory_status", []) 
                          if item.get("status") == "low_stock"])
    active_alerts_count = len(dashboard_data.get("active_alerts", []))
    
    return (
        str(total_sales),
        f"${total_revenue:,.2f}",
        str(low_stock_count),
        str(active_alerts_count)
    )


@app.callback(
    Output("sales-chart", "figure"),
    [Input("interval-component", "n_intervals")]
)
def update_sales_chart(n):
    """Update sales trend chart."""
    global dashboard_data
    
    # Create sample data for demonstration
    dates = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq='D')
    sales_data = [10, 15, 12, 18, 20, 16, 14]  # Sample data
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=sales_data,
        mode='lines+markers',
        name='Daily Sales',
        line=dict(color='blue', width=2),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title="Sales Trend (Last 7 Days)",
        xaxis_title="Date",
        yaxis_title="Number of Sales",
        height=400,
        showlegend=False
    )
    
    return fig


@app.callback(
    Output("rush-predictions-chart", "figure"),
    [Input("interval-component", "n_intervals")]
)
def update_rush_predictions_chart(n):
    """Update rush hour predictions chart."""
    global dashboard_data
    
    predictions = dashboard_data.get("rush_predictions", [])
    
    if not predictions:
        # Create sample data
        hours = list(range(24))
        probabilities = [0.1, 0.2, 0.1, 0.05, 0.05, 0.1, 0.3, 0.6, 0.8, 0.7, 0.5, 0.4,
                        0.3, 0.2, 0.1, 0.1, 0.2, 0.4, 0.6, 0.8, 0.9, 0.7, 0.4, 0.2]
    else:
        hours = [pred.get("hour", 0) for pred in predictions]
        probabilities = [pred.get("rush_probability", 0) for pred in predictions]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=hours,
        y=probabilities,
        name='Rush Probability',
        marker_color='red'
    ))
    
    fig.update_layout(
        title="Rush Hour Predictions (Next 24 Hours)",
        xaxis_title="Hour of Day",
        yaxis_title="Rush Probability",
        height=400,
        showlegend=False
    )
    
    return fig


@app.callback(
    Output("inventory-table", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_inventory_table(n):
    """Update inventory status table."""
    global dashboard_data
    
    inventory_items = dashboard_data.get("inventory_status", [])
    
    if not inventory_items:
        return html.P("No inventory data available")
    
    # Create table rows
    rows = []
    for item in inventory_items[:10]:  # Show top 10 items
        status_color = {
            "normal": "success",
            "low_stock": "warning",
            "out_of_stock": "danger",
            "reorder_needed": "info"
        }.get(item.get("status", "normal"), "secondary")
        
        rows.append(dbc.Row([
            dbc.Col(item.get("name", "Unknown"), width=4),
            dbc.Col(str(item.get("available_quantity", 0)), width=2),
            dbc.Col(str(item.get("min_stock_level", 0)), width=2),
            dbc.Col(dbc.Badge(item.get("status", "normal"), color=status_color), width=2),
            dbc.Col(f"${item.get('selling_price', 0):.2f}", width=2)
        ], className="mb-2"))
    
    return html.Div([
        dbc.Row([
            dbc.Col("Product", width=4, className="font-weight-bold"),
            dbc.Col("Available", width=2, className="font-weight-bold"),
            dbc.Col("Min Level", width=2, className="font-weight-bold"),
            dbc.Col("Status", width=2, className="font-weight-bold"),
            dbc.Col("Price", width=2, className="font-weight-bold")
        ], className="mb-3"),
        *rows
    ])


@app.callback(
    Output("alerts-list", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_alerts_list(n):
    """Update active alerts list."""
    global dashboard_data
    
    alerts = dashboard_data.get("active_alerts", [])
    
    if not alerts:
        return html.P("No active alerts")
    
    alert_cards = []
    for alert in alerts[:5]:  # Show top 5 alerts
        severity_color = {
            "low": "info",
            "medium": "warning",
            "high": "danger",
            "critical": "danger"
        }.get(alert.get("severity", "low"), "secondary")
        
        alert_cards.append(dbc.Alert([
            html.H6(alert.get("title", "Alert"), className="alert-heading"),
            html.P(alert.get("message", ""), className="mb-0"),
            html.Small(alert.get("created_at", ""), className="text-muted")
        ], color=severity_color, className="mb-2"))
    
    return html.Div(alert_cards)


@app.callback(
    Output("recent-sales-table", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_recent_sales_table(n):
    """Update recent sales table."""
    global dashboard_data
    
    recent_sales = dashboard_data.get("recent_sales", {}).get("sales", [])
    
    if not recent_sales:
        return html.P("No recent sales data")
    
    # Create table rows
    rows = []
    for sale in recent_sales[:10]:  # Show top 10 sales
        rows.append(dbc.Row([
            dbc.Col(sale.get("transaction_id", "Unknown"), width=3),
            dbc.Col(f"${sale.get('total_amount', 0):.2f}", width=2),
            dbc.Col(sale.get("payment_method", "Unknown"), width=2),
            dbc.Col(str(sale.get("items_count", 0)), width=2),
            dbc.Col(sale.get("created_at", "Unknown")[:19], width=3)
        ], className="mb-2"))
    
    return html.Div([
        dbc.Row([
            dbc.Col("Transaction ID", width=3, className="font-weight-bold"),
            dbc.Col("Amount", width=2, className="font-weight-bold"),
            dbc.Col("Payment", width=2, className="font-weight-bold"),
            dbc.Col("Items", width=2, className="font-weight-bold"),
            dbc.Col("Time", width=3, className="font-weight-bold")
        ], className="mb-3"),
        *rows
    ])


if __name__ == "__main__":
    app.run_server(
        debug=True,
        host=settings.dashboard_host,
        port=settings.dashboard_port
    ) 