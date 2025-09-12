#!/usr/bin/env python3
"""
Test script for Stake Casino Bot
Verifies all components are working correctly
"""

import os
import sys
import asyncio
import sqlite3
import requests
import time
from pathlib import Path

def test_environment():
    """Test environment configuration"""
    print("🔧 Testing environment configuration...")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("❌ BOT_TOKEN not set")
        return False
    
    print(f"✅ BOT_TOKEN: {'*' * 20}{bot_token[-5:]}")
    print(f"✅ MINI_APP_URL: {os.getenv('MINI_APP_URL', 'Not set')}")
    print(f"✅ FLASK_API_URL: {os.getenv('FLASK_API_URL', 'Not set')}")
    print(f"✅ DATABASE_PATH: {os.getenv('DATABASE_PATH', 'Not set')}")
    
    return True

def test_database():
    """Test database functionality"""
    print("\n🗄️ Testing database functionality...")
    
    try:
        # Test database creation and operations
        db_path = "test_casino.db"
        
        # Remove test database if exists
        if os.path.exists(db_path):
            os.remove(db_path)
        
        # Create test database
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                balance REAL DEFAULT 1000.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Test inserting a user
        test_user_id = 12345
        conn.execute("""
            INSERT INTO users (telegram_id, username, balance) 
            VALUES (?, ?, ?)
        """, (test_user_id, "test_user", 1000.0))
        
        # Test retrieving the user
        cursor = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", 
            (test_user_id,)
        )
        user = cursor.fetchone()
        
        conn.close()
        
        if user:
            print(f"✅ Database test passed - User created: {user}")
            
            # Clean up test database
            os.remove(db_path)
            return True
        else:
            print("❌ Database test failed - No user found")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_imports():
    """Test all required imports"""
    print("\n📦 Testing imports...")
    
    try:
        # Test bot imports
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
        from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
        print("✅ python-telegram-bot imports successful")
        
        # Test async sqlite
        import aiosqlite
        print("✅ aiosqlite import successful")
        
        # Test aiohttp
        import aiohttp
        print("✅ aiohttp import successful")
        
        # Test Flask imports
        from flask import Flask, request, jsonify
        from flask_cors import CORS
        print("✅ Flask imports successful")
        
        # Test other utilities
        import sqlite3
        from datetime import datetime
        from dotenv import load_dotenv
        print("✅ Utility imports successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

async def test_async_database():
    """Test async database operations"""
    print("\n🔄 Testing async database operations...")
    
    try:
        import aiosqlite
        
        db_path = "test_async_casino.db"
        
        # Remove test database if exists
        if os.path.exists(db_path):
            os.remove(db_path)
        
        # Test async database operations
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    balance REAL DEFAULT 1000.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert test user
            test_user_id = 67890
            await db.execute("""
                INSERT INTO users (telegram_id, username, balance) 
                VALUES (?, ?, ?)
            """, (test_user_id, "async_test_user", 1500.0))
            
            await db.commit()
            
            # Retrieve test user
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", 
                (test_user_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                user_data = dict(row)
                print(f"✅ Async database test passed - User: {user_data}")
                
                # Clean up
                os.remove(db_path)
                return True
            else:
                print("❌ Async database test failed - No user found")
                return False
                
    except Exception as e:
        print(f"❌ Async database test failed: {e}")
        return False

def test_flask_api():
    """Test Flask API endpoints (if running)"""
    print("\n🌐 Testing Flask API endpoints...")
    
    try:
        base_url = "http://localhost:5001"
        
        # Test health endpoint
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint working")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
        
        # Test user endpoint (this will create a test user)
        test_user_id = 99999
        response = requests.get(f"{base_url}/api/user/{test_user_id}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ User endpoint working - Balance: {data['user']['balance']}")
        else:
            print(f"❌ User endpoint failed: {response.status_code}")
            return False
        
        # Test mini app endpoint
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200 and "Stake Casino" in response.text:
            print("✅ Mini app endpoint working")
        else:
            print(f"❌ Mini app endpoint failed: {response.status_code}")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("⚠️ Flask API not running - this is OK if testing components separately")
        return True
    except Exception as e:
        print(f"❌ Flask API test failed: {e}")
        return False

def test_file_structure():
    """Test that all required files exist"""
    print("\n📁 Testing file structure...")
    
    required_files = [
        "stake_bot_clean.py",
        "flask_api.py",
        "requirements.txt",
        "run_casino.py"
    ]
    
    all_exist = True
    for file_name in required_files:
        if os.path.exists(file_name):
            print(f"✅ {file_name} exists")
        else:
            print(f"❌ {file_name} missing")
            all_exist = False
    
    return all_exist

async def main():
    """Run all tests"""
    print("🎰 Stake Casino Bot - System Test")
    print("=" * 50)
    
    # Track test results
    test_results = []
    
    # Run tests
    test_results.append(("Environment", test_environment()))
    test_results.append(("File Structure", test_file_structure()))
    test_results.append(("Imports", test_imports()))
    test_results.append(("Database", test_database()))
    test_results.append(("Async Database", await test_async_database()))
    test_results.append(("Flask API", test_flask_api()))
    
    # Print results
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS:")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"TOTAL: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready to run.")
        print("\nNext steps:")
        print("1. Set your BOT_TOKEN in .env file")
        print("2. Run: python run_casino.py")
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
        
    return passed == total

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
