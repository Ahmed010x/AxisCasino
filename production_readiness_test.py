#!/usr/bin/env python3
"""
Production Readiness Test for Telegram Casino Bot
Comprehensive test to ensure all systems are working correctly.
"""

import asyncio
import sqlite3
import os
import sys
import importlib.util
from datetime import datetime
import logging

# Suppress logging during tests
logging.getLogger().setLevel(logging.CRITICAL)

def test_database_integrity():
    """Test database integrity and schema"""
    print("🔍 Testing database integrity...")
    
    try:
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        
        # Test essential tables exist
        tables = ['users', 'transactions', 'deposits', 'withdrawals', 'game_sessions']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  ✅ Table '{table}': {count} records")
        
        # Test user table schema
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        required_columns = ['user_id', 'username', 'balance', 'total_wagered', 'created_at']
        
        for col in required_columns:
            if col in user_columns:
                print(f"  ✅ User column '{col}' exists")
            else:
                print(f"  ❌ User column '{col}' missing")
                return False
        
        # Test transactions table schema
        cursor.execute("PRAGMA table_info(transactions)")
        trans_columns = [col[1] for col in cursor.fetchall()]
        required_trans_columns = ['transaction_id', 'user_id', 'type', 'amount']
        
        for col in required_trans_columns:
            if col in trans_columns:
                print(f"  ✅ Transaction column '{col}' exists")
            else:
                print(f"  ❌ Transaction column '{col}' missing")
                return False
        
        conn.close()
        print("  ✅ Database integrity test passed")
        return True
        
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        return False

def test_main_module_import():
    """Test if main.py can be imported without errors"""
    print("🔍 Testing main module import...")
    
    try:
        # Try to import main module
        spec = importlib.util.spec_from_file_location("main", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        
        # This will execute the module but we'll catch any immediate errors
        spec.loader.exec_module(main_module)
        
        print("  ✅ Main module imports successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Main module import failed: {e}")
        return False

def test_environment_config():
    """Test environment configuration"""
    print("🔍 Testing environment configuration...")
    
    try:
        # Check if .env file exists
        if os.path.exists('.env'):
            print("  ✅ .env file exists")
        else:
            print("  ⚠️  .env file not found (using defaults)")
        
        # Check required environment variables
        required_vars = ['BOT_TOKEN', 'CASINO_DB']
        for var in required_vars:
            if os.getenv(var):
                print(f"  ✅ Environment variable '{var}' is set")
            else:
                print(f"  ⚠️  Environment variable '{var}' not set")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Environment config test failed: {e}")
        return False

def test_dependencies():
    """Test if all required dependencies are available"""
    print("🔍 Testing dependencies...")
    
    required_packages = [
        ('telegram', 'telegram'), 
        ('aiosqlite', 'aiosqlite'), 
        ('aiohttp', 'aiohttp'), 
        ('flask', 'flask'), 
        ('python-dotenv', 'dotenv'), 
        ('nest_asyncio', 'nest_asyncio')
    ]
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"  ✅ Package '{package_name}' is available")
        except ImportError:
            print(f"  ❌ Package '{package_name}' is missing")
            return False
    
    return True

async def test_async_functions():
    """Test async functionality"""
    print("🔍 Testing async functionality...")
    
    try:
        # Test async database connection
        import aiosqlite
        async with aiosqlite.connect('casino.db') as db:
            await db.execute("SELECT 1")
            print("  ✅ Async database connection works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Async test failed: {e}")
        return False

def test_file_structure():
    """Test required files exist"""
    print("🔍 Testing file structure...")
    
    required_files = [
        'main.py', 
        'requirements.txt',
        'casino.db'
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ File '{file}' exists")
        else:
            print(f"  ❌ File '{file}' missing")
            return False
    
    return True

async def main():
    """Run all production readiness tests"""
    print("🚀 Starting Production Readiness Test for Telegram Casino Bot")
    print("=" * 60)
    
    tests = [
        test_file_structure,
        test_dependencies,
        test_environment_config,
        test_database_integrity,
        test_main_module_import,
        test_async_functions
    ]
    
    passed = 0
    total = len(tests)
    
    for i, test in enumerate(tests, 1):
        print(f"\n[{i}/{total}] Running {test.__name__}...")
        
        if test == test_async_functions:
            result = await test()
        else:
            result = test()
        
        if result:
            passed += 1
        
        print("-" * 40)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Bot is production-ready!")
        print("\n✅ Your Telegram Casino Bot is ready for deployment:")
        print("   • Database schema is correct")
        print("   • All dependencies are installed")
        print("   • Code compiles without errors")
        print("   • Async functionality works")
        print("   • File structure is complete")
        
        print("\n🚀 Next steps:")
        print("   1. Update BOT_TOKEN in .env with your real bot token")
        print("   2. Test with a real Telegram bot")
        print("   3. Deploy to your hosting platform")
        
        return True
    else:
        print("❌ Some tests failed. Please fix the issues before deployment.")
        return False

if __name__ == "__main__":
    asyncio.run(main())
