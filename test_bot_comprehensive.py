#!/usr/bin/env python3
"""
Comprehensive bot testing script
"""

import os
import sys
import asyncio
import sqlite3
from dotenv import load_dotenv

def test_environment():
    """Test environment setup"""
    print("🔍 Testing environment...")
    load_dotenv()
    
    required_vars = ['BOT_TOKEN', 'OWNER_ID']
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing environment variables: {missing}")
        return False
    
    print("✅ Environment variables configured")
    return True

def test_database():
    """Test database connectivity and schema"""
    print("🔍 Testing database...")
    
    try:
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        
        # Check required tables
        required_tables = ['users', 'house_balance', 'game_sessions', 'transactions']
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [t for t in required_tables if t not in existing_tables]
        if missing_tables:
            print(f"❌ Missing database tables: {missing_tables}")
            return False
        
        # Check house balance
        cursor.execute('SELECT balance FROM house_balance WHERE id = 1')
        house_balance = cursor.fetchone()
        if house_balance:
            print(f"✅ House balance: ${house_balance[0]:.2f}")
        else:
            print("⚠️ No house balance record found")
        
        conn.close()
        print("✅ Database connectivity successful")
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_imports():
    """Test bot module imports"""
    print("🔍 Testing imports...")
    
    try:
        import main
        print("✅ Main module imported")
        
        # Check for key functions
        required_functions = ['get_house_balance', 'update_house_balance_on_game', 'initialize_database']
        missing_functions = []
        
        for func in required_functions:
            if not hasattr(main, func):
                missing_functions.append(func)
        
        if missing_functions:
            print(f"⚠️ Missing functions: {missing_functions}")
        else:
            print("✅ All required functions found")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

async def test_async_functions():
    """Test async functions"""
    print("🔍 Testing async functions...")
    
    try:
        import main
        
        # Test database initialization
        await main.initialize_database()
        print("✅ Database initialization successful")
        
        # Test house balance retrieval
        balance = await main.get_house_balance()
        print(f"✅ House balance retrieved: ${balance:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Async function error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting comprehensive bot tests...\n")
    
    tests = [
        ("Environment", test_environment),
        ("Database", test_database),
        ("Imports", test_imports),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} Test ---")
        if test_func():
            passed += 1
        print()
    
    # Run async tests
    print("--- Async Functions Test ---")
    try:
        if asyncio.run(test_async_functions()):
            passed += 1
        total += 1
    except Exception as e:
        print(f"❌ Async test failed: {e}")
        total += 1
    
    print(f"\n🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Bot is ready for deployment.")
        return True
    else:
        print("⚠️ Some tests failed. Please review and fix issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
