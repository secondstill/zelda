#!/usr/bin/env python3
"""
Test script to verify the server can start without import or route errors
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_server_imports():
    """Test if we can import the Flask app without errors"""
    try:
        print("🔍 Testing imports...")
        from app_api import app, jwt
        print("✅ Flask app imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ General error during import: {e}")
        return False

def test_route_registration():
    """Test if routes are registered without conflicts"""
    try:
        from app_api import app
        print("🔍 Testing route registration...")
        
        # Get all registered routes
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(f"{rule.rule} [{', '.join(rule.methods)}]")
        
        print(f"✅ Successfully registered {len(routes)} routes:")
        for route in sorted(routes):
            print(f"  - {route}")
        
        return True
    except Exception as e:
        print(f"❌ Route registration error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Flask server startup...")
    print("=" * 50)
    
    success = True
    
    # Test imports
    if not test_server_imports():
        success = False
    
    print()
    
    # Test route registration
    if not test_route_registration():
        success = False
    
    print("=" * 50)
    if success:
        print("✅ All tests passed! Server should start without errors.")
        print("💡 You can now run: python app_api.py")
    else:
        print("❌ Some tests failed. Check the errors above.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())