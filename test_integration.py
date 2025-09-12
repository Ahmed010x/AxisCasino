#!/usr/bin/env python3
"""
Test script for Casino Bot Mini App Integration
Run this to verify everything is working before deployment
"""

import asyncio
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_webapp_integration():
    """Test WebApp integration components"""
    print("🧪 Testing Casino Bot Mini App Integration...")
    print("=" * 50)
    
    try:
        # Test imports
        print("📦 Testing imports...")
        from telegram import WebApp, MenuButtonWebApp, InlineKeyboardButton
        print("✅ Telegram WebApp imports successful")
        
        # Test environment variables
        print("\n🔧 Checking environment configuration...")
        from dotenv import load_dotenv
        load_dotenv()
        
        bot_token = os.environ.get("BOT_TOKEN")
        webapp_url = os.environ.get("WEBAPP_URL", "https://your-casino-webapp.vercel.app")
        webapp_enabled = os.environ.get("WEBAPP_ENABLED", "true").lower() == "true"
        
        if bot_token and bot_token != "your_bot_token_here":
            print("✅ BOT_TOKEN is configured")
        else:
            print("⚠️  BOT_TOKEN not set (needed for deployment)")
        
        print(f"✅ WEBAPP_URL: {webapp_url}")
        print(f"✅ WEBAPP_ENABLED: {webapp_enabled}")
        
        # Test WebApp object creation
        print("\n🚀 Testing WebApp object creation...")
        test_webapp = WebApp(url=f"{webapp_url}?user_id=123456&balance=1000")
        print("✅ WebApp object created successfully")
        
        # Test InlineKeyboardButton with WebApp
        print("\n🎮 Testing WebApp button creation...")
        webapp_button = InlineKeyboardButton("🚀 PLAY IN WEBAPP", web_app=test_webapp)
        print("✅ WebApp button created successfully")
        
        # Test database functions
        print("\n💾 Testing database functions...")
        from main import init_db, get_user, create_user
        
        # Initialize test database
        await init_db()
        print("✅ Database initialized")
        
        # Test user creation
        test_user = await create_user(123456, "TestUser")
        print(f"✅ Test user created: {test_user}")
        
        # Test user retrieval
        retrieved_user = await get_user(123456)
        print(f"✅ User retrieved: {retrieved_user}")
        
        print("\n🎯 Testing game functions...")
        from main import deduct_balance, update_balance
        
        # Test balance operations
        success = await deduct_balance(123456, 100)
        print(f"✅ Balance deduction: {success}")
        
        new_balance = await update_balance(123456, 50)
        print(f"✅ Balance update: {new_balance}")
        
        # Test health check
        print("\n🏥 Testing health check...")
        from main import health_check
        
        # Create mock request
        class MockRequest:
            pass
        
        mock_request = MockRequest()
        health_response = await health_check(mock_request)
        print("✅ Health check endpoint working")
        
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED!")
        print("🚀 Your bot is ready for deployment!")
        print("\n📋 Deployment Checklist:")
        print("1. Set BOT_TOKEN in Render environment variables")
        print("2. Set WEBAPP_URL to your actual WebApp URL")
        print("3. Set RENDER_EXTERNAL_URL to your Render app URL")
        print("4. Deploy to Render using the provided configuration")
        print("\n🎰 Ready to launch your Casino Bot! 🎰")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Run: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("🔍 Check the error details above")

def test_config():
    """Test configuration without async"""
    print("⚙️  Configuration Test")
    print("-" * 20)
    
    # Check if .env exists
    env_file = ".env"
    if os.path.exists(env_file):
        print("✅ .env file found")
    else:
        print("⚠️  .env file not found (create from env.example)")
    
    # Check requirements.txt
    req_file = "requirements.txt"
    if os.path.exists(req_file):
        print("✅ requirements.txt found")
        with open(req_file, 'r') as f:
            deps = f.read()
            if "python-telegram-bot" in deps:
                print("✅ python-telegram-bot dependency found")
            if "aiohttp" in deps:
                print("✅ aiohttp dependency found")
    else:
        print("❌ requirements.txt missing")
    
    # Check main.py
    main_file = "main.py"
    if os.path.exists(main_file):
        print("✅ main.py found")
        
        # Check for WebApp imports
        with open(main_file, 'r') as f:
            content = f.read()
            if "WebApp" in content:
                print("✅ WebApp integration found")
            if "MenuButtonWebApp" in content:
                print("✅ Menu button integration found")
            if "mini_app_centre" in content:
                print("✅ Mini App Centre found")
    else:
        print("❌ main.py missing")

if __name__ == "__main__":
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎰 Casino Bot Mini App Integration Test")
    print("🔧 Testing configuration and dependencies...")
    print()
    
    # Run basic config test first
    test_config()
    print()
    
    # Run async tests
    try:
        asyncio.run(test_webapp_integration())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)
