#!/usr/bin/env python3
"""
Simple test script to verify Python installation.
"""
import sys

print("🎉 Python is working!")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

# Test basic imports
try:
    import json
    print("✅ JSON module imported successfully")
except ImportError as e:
    print(f"❌ JSON module import failed: {e}")

try:
    import datetime
    print("✅ Datetime module imported successfully")
except ImportError as e:
    print(f"❌ Datetime module import failed: {e}")

print("\n🚀 Ready to run ShopTrack!") 