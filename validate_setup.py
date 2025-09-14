#!/usr/bin/env python3
"""
Quick validation script for GameForge application setup.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all modules can be imported correctly."""
    print("🧪 Testing module imports...")
    
    try:
        from gameforge.core.config import get_settings
        print("✅ Config module imported successfully")
        
        from gameforge.core.health import HealthChecker
        print("✅ Health checker module imported successfully")
        
        from gameforge.api.v1 import api_router
        print("✅ API router imported successfully")
        
        from gameforge.app import app
        print("✅ Main app imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config():
    """Test configuration loading."""
    print("\n🔧 Testing configuration...")
    
    try:
        from gameforge.core.config import get_settings
        settings = get_settings()
        
        print(f"✅ Environment: {settings.environment}")
        print(f"✅ Database URL: {settings.database_url}")
        print(f"✅ Redis URL: {settings.redis_url}")
        print(f"✅ Workers: {settings.workers}")
        
        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_health_checker():
    """Test health checker initialization."""
    print("\n🏥 Testing health checker...")
    
    try:
        from gameforge.core.health import HealthChecker
        health_checker = HealthChecker()
        
        print("✅ Health checker created successfully")
        return True
    except Exception as e:
        print(f"❌ Health checker test failed: {e}")
        return False

def test_app_creation():
    """Test FastAPI app creation."""
    print("\n🚀 Testing FastAPI app creation...")
    
    try:
        from gameforge.app import create_app
        app = create_app()
        
        print("✅ FastAPI app created successfully")
        print(f"✅ App title: {app.title}")
        print(f"✅ App version: {app.version}")
        
        # Check if routes are registered
        routes = [route.path for route in app.routes]
        expected_routes = ["/health", "/health/detailed", "/ready", "/live", "/info"]
        
        for route in expected_routes:
            if route in routes:
                print(f"✅ Route {route} found")
            else:
                print(f"⚠️  Route {route} not found")
        
        return True
    except Exception as e:
        print(f"❌ App creation test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🎮 GameForge Application Setup Validation")
    print("=" * 50)
    
    all_passed = True
    
    # Run tests
    tests = [
        test_imports,
        test_config,
        test_health_checker,
        test_app_creation
    ]
    
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! GameForge application is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())