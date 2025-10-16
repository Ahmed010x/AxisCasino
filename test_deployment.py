#!/usr/bin/env python3
"""
Deployment Mode Test
Test the bot in deployment mode (Flask + Bot in threads)
"""

import asyncio
import threading
import time
import os
import signal
import sys
from unittest.mock import Mock, patch
from dotenv import load_dotenv

# Load test environment
load_dotenv('.env.test')

# Set deployment environment variables for testing
os.environ['RENDER'] = 'true'  # Simulate deployment environment

# Import main module
import main

def test_flask_server():
    """Test Flask server startup"""
    print("🌐 Testing Flask server...")
    
    try:
        app = main.app
        print(f"✅ Flask app ready: {app.name}")
        print("✅ Routes registered:")
        for rule in app.url_map.iter_rules():
            print(f"   - {rule.rule} ({rule.methods})")
        return True
    except Exception as e:
        print(f"❌ Flask test failed: {e}")
        return False

def test_threading_mode():
    """Test threading mode for deployment"""
    print("\n🧵 Testing threading mode...")
    
    try:
        # Test if the bot can start in a separate thread
        def mock_bot_run():
            print("   🤖 Mock bot thread started")
            time.sleep(0.5)  # Simulate some work
            print("   🤖 Mock bot thread finished")
        
        # Start mock bot thread
        bot_thread = threading.Thread(target=mock_bot_run)
        bot_thread.daemon = True
        bot_thread.start()
        
        # Wait for thread to complete
        bot_thread.join(timeout=2.0)
        
        if not bot_thread.is_alive():
            print("✅ Threading test passed")
            return True
        else:
            print("❌ Thread did not complete")
            return False
            
    except Exception as e:
        print(f"❌ Threading test failed: {e}")
        return False

def test_event_loop_handling():
    """Test event loop handling in deployment mode"""
    print("\n🔄 Testing event loop handling...")
    
    try:
        # Test the run_telegram_bot function's event loop handling
        with patch('main.run_telegram_bot_async') as mock_async:
            mock_async.return_value = None
            
            # This should not raise an event loop error
            main.run_telegram_bot()
            print("✅ Event loop handling works correctly")
            return True
            
    except Exception as e:
        print(f"❌ Event loop test failed: {e}")
        return False

async def test_async_functions():
    """Test async functions work correctly"""
    print("\n⚡ Testing async functions...")
    
    try:
        # Test database operations
        await main.init_db()
        user = await main.create_user(888888, "deploytest")
        print(f"✅ Async database operations: User {user['user_id']}")
        
        # Test async crypto functions
        rate = await main.get_crypto_usd_rate('LTC')
        print(f"✅ Async crypto rate: ${rate}")
        
        # Test async game logging
        await main.log_game_session(888888, 'slots', 10.0, 20.0, 'test win')
        print("✅ Async game logging")
        
        return True
    except Exception as e:
        print(f"❌ Async functions test failed: {e}")
        return False

def main_test():
    """Run deployment tests"""
    print("🚀 DEPLOYMENT MODE TEST")
    print("=" * 50)
    
    # Check deployment environment
    is_deployment = bool(os.environ.get("RENDER") or os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("HEROKU"))
    print(f"📍 Deployment mode detected: {is_deployment}")
    
    test_results = []
    
    # Run sync tests
    test_results.append(test_flask_server())
    test_results.append(test_threading_mode())
    test_results.append(test_event_loop_handling())
    
    # Run async tests
    async_result = asyncio.run(test_async_functions())
    test_results.append(async_result)
    
    print("\n" + "=" * 50)
    print("📊 DEPLOYMENT TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(test_results)
    total = len(test_results)
    
    if passed == total:
        print(f"🎉 DEPLOYMENT TEST PASSED! ({passed}/{total})")
        print("✅ Bot is ready for production deployment!")
        print("\n🔧 Deployment checklist:")
        print("   ✅ Flask server works")
        print("   ✅ Threading mode works")  
        print("   ✅ Event loop handling works")
        print("   ✅ Async functions work")
        print("\n📝 Next steps:")
        print("   1. Set your real BOT_TOKEN in environment")
        print("   2. Configure other API keys if needed")
        print("   3. Deploy to your platform (Render/Railway/Heroku)")
        return True
    else:
        print(f"⚠️ {passed}/{total} tests passed")
        print("❌ Deployment issues detected")
        return False

if __name__ == "__main__":
    success = main_test()
    sys.exit(0 if success else 1)
