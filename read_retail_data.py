#!/usr/bin/env python3
"""
Script to read and analyze the retail store inventory Excel file.
"""
import pandas as pd
import sys
import os

def analyze_retail_data():
    """Analyze the retail store inventory Excel file."""
    try:
        # Read the Excel file
        print("📊 Reading retail_store_inventory.xlsx...")
        df = pd.read_excel('retail_store_inventory.xlsx')
        
        print(f"✅ Successfully read Excel file!")
        print(f"📋 File shape: {df.shape[0]} rows, {df.shape[1]} columns")
        
        # Display column names
        print(f"\n📝 Column names:")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i}. {col}")
        
        # Display first few rows
        print(f"\n📋 First 5 rows:")
        print(df.head())
        
        # Display data types
        print(f"\n🔍 Data types:")
        print(df.dtypes)
        
        # Display basic statistics for numeric columns
        print(f"\n📈 Basic statistics:")
        print(df.describe())
        
        # Check for missing values
        print(f"\n❓ Missing values:")
        missing = df.isnull().sum()
        if missing.sum() > 0:
            print(missing[missing > 0])
        else:
            print("No missing values found!")
        
        # Save sample data for ShopTrack
        print(f"\n💾 Saving sample data for ShopTrack...")
        
        # Create a sample subset (first 100 rows) to avoid memory issues
        sample_df = df.head(100)
        sample_df.to_csv('retail_data_sample.csv', index=False)
        print(f"✅ Saved sample data to retail_data_sample.csv")
        
        return df
        
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        return None

if __name__ == "__main__":
    print("🎯 Retail Store Inventory Data Analyzer")
    print("=" * 50)
    
    # Check if file exists
    if not os.path.exists('retail_store_inventory.xlsx'):
        print("❌ retail_store_inventory.xlsx not found!")
        sys.exit(1)
    
    # Analyze the data
    df = analyze_retail_data()
    
    if df is not None:
        print(f"\n🎉 Analysis complete!")
        print(f"📊 Total records: {len(df)}")
        print(f"📋 Total columns: {len(df.columns)}")
    else:
        print("❌ Failed to analyze data") 