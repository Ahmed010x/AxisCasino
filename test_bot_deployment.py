#!/usr/bin/env python3
"""
Test script to verify bot deployment readiness
"""
import os
import sys
import asyncio
import importlib.util
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported"""
    print("🔍 Testing imports...")
    
    required_modules = [
        'telegram',
        'aiosqlite', 
        'aiohttp',
        'dotenv',
        'nest_asyncio'
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            return False
    
    return True

def test_env_files():
    """Test that environment files exist"""
    print("\n🔍 Testing environment files...")
    
    env_files = ['.env', 'env.litecoin']
    for file in env_files:
        if os.path.exists(file):
            print(f"✅ {file} exists")
        else:
            print(f"⚠️ {file} missing")
    
    return True

def test_bot_token():
    """Test that BOT_TOKEN is available"""
    print("\n🔍 Testing BOT_TOKEN...")
    
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv("env.litecoin")
    
    bot_token = os.environ.get("BOT_TOKEN")
    if bot_token:
        print(f"✅ BOT_TOKEN is set (length: {len(bot_token)})")
        return True
    else:
        print("❌ BOT_TOKEN not found in environment")
        return False

async def test_database():
    """Test database initialization"""
    print("\n🔍 Testing database...")
    
    try:
        import aiosqlite
        
        # Test database connection
        async with aiosqlite.connect("test_casino.db") as db:
            await db.execute("SELECT 1")
            print("✅ Database connection successful")
        
        # Clean up test database
        if os.path.exists("test_casino.db"):
            os.remove("test_casino.db")
            
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_main_py_syntax():
    """Test that main.py has valid syntax"""
    print("\n🔍 Testing main.py syntax...")
    
    try:
        spec = importlib.util.spec_from_file_location("main", "main.py")
        if spec is None:
            print("❌ Could not load main.py")
            return False
        
        # Try to compile the module
        with open("main.py", "r") as f:
            code = f.read()
        
        compile(code, "main.py", "exec")
        print("✅ main.py syntax is valid")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in main.py: {e}")
        return False
    except Exception as e:
        print(f"❌ Error loading main.py: {e}")
        return False

async def main():
    """Run all deployment tests"""
    print("🎰 Casino Bot Deployment Test\n")
    
    tests = [
        ("Import Test", test_imports),
        ("Environment Files", test_env_files), 
        ("BOT_TOKEN Check", test_bot_token),
        ("Main.py Syntax", test_main_py_syntax),
        ("Database Test", test_database),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print(f"\n{'='*50}")
    print(f"DEPLOYMENT TEST RESULTS")
    print('='*50)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Bot is ready for deployment!")
        return True
    else:
        print("⚠️ Some tests failed - Please fix issues before deployment")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
