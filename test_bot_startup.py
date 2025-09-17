#!/usr/bin/env python3
"""
Test script to verify bot startup without errors
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment
load_dotenv()
load_dotenv("env.litecoin")

def test_imports():
    """Test that all imports work correctly"""
    try:
        import main
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during import: {e}")
        return False

def test_environment():
    """Test that required environment variables are set"""
    required_vars = ["BOT_TOKEN"]
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️ Missing environment variables: {missing_vars}")
        return False
    else:
        print("✅ All required environment variables present")
        return True

async def test_database_init():
    """Test database initialization"""
    try:
        from main import init_db
        await init_db()
        print("✅ Database initialization successful")
        return True
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

async def main_test():
    """Run all tests"""
    print("🔧 Testing bot startup components...")
    
    # Test imports
    if not test_imports():
        return False
    
    # Test environment
    env_ok = test_environment()
    
    # Test database
    db_ok = await test_database_init()
    
    if env_ok and db_ok:
        print("🎉 All tests passed! Bot should deploy successfully.")
        return True
    else:
        print("❌ Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main_test())
    sys.exit(0 if success else 1)
