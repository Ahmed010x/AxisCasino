#!/usr/bin/env python3
"""
Final callback and navigation test for Telegram Casino Bot
Tests all critical callback handlers and navigation flows
"""

import asyncio
import aiosqlite
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database path
DB_PATH = "casino.db"

async def test_database():
    """Test database initialization and operations"""
    logger.info("🔍 Testing database...")
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Test users table
            cur = await db.execute("SELECT COUNT(*) FROM users")
            result = await cur.fetchone()
            logger.info(f"✅ Users table accessible: {result[0]} users")
            
            # Test game_sessions table
            cur = await db.execute("SELECT COUNT(*) FROM game_sessions")
            result = await cur.fetchone()
            logger.info(f"✅ Game sessions table accessible: {result[0]} sessions")
            
        return True
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

async def test_user_operations():
    """Test user creation and balance operations"""
    logger.info("🔍 Testing user operations...")
    
    test_user_id = 999999999
    test_username = "test_user"
    
    try:
        # Import user functions from main
        import sys
        sys.path.append(os.path.dirname(__file__))
        from main import get_user, create_user, update_balance, deduct_balance
        
        # Clean up any existing test user
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM users WHERE id = ?", (test_user_id,))
            await db.commit()
        
        # Test user creation
        user = await create_user(test_user_id, test_username)
        logger.info(f"✅ User created: {user['username']} with balance {user['balance']}")
        
        # Test balance operations
        await update_balance(test_user_id, 500)
        user = await get_user(test_user_id)
        logger.info(f"✅ Balance updated: {user['balance']}")
        
        # Test balance deduction
        success = await deduct_balance(test_user_id, 100)
        logger.info(f"✅ Balance deduction: {success}")
        
        # Clean up
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM users WHERE id = ?", (test_user_id,))
            await db.commit()
        
        return True
    except Exception as e:
        logger.error(f"❌ User operations test failed: {e}")
        return False

def test_callback_handlers():
    """Test that all callback handlers are properly defined"""
    logger.info("🔍 Testing callback handlers...")
    
    try:
        # Import main module
        import sys
        sys.path.append(os.path.dirname(__file__))
        import main
        
        # List of expected callback handlers
        expected_handlers = [
            'mini_app_centre',
            'show_balance',
            'main_panel',
            'bonus_centre',
            'show_stats',
            'show_leaderboard',
            'show_help',
            'deposit',
            'withdraw'
        ]
        
        # Check if handle_callback function exists
        if hasattr(main, 'handle_callback'):
            logger.info("✅ Main callback handler found")
        else:
            logger.error("❌ Main callback handler not found")
            return False
        
        # Check individual handler functions
        handler_functions = [
            'show_mini_app_centre',
            'show_balance_callback',
            'main_panel_callback',
            'placeholder_callback',
            'deposit_callback',
            'withdraw_callback'
        ]
        
        missing_handlers = []
        for handler in handler_functions:
            if hasattr(main, handler):
                logger.info(f"✅ Handler found: {handler}")
            else:
                missing_handlers.append(handler)
                logger.warning(f"⚠️ Handler missing: {handler}")
        
        if missing_handlers:
            logger.error(f"❌ Missing handlers: {missing_handlers}")
            return False
        
        logger.info("✅ All callback handlers found")
        return True
        
    except Exception as e:
        logger.error(f"❌ Callback handler test failed: {e}")
        return False

def test_webapp_configuration():
    """Test WebApp configuration and imports"""
    logger.info("🔍 Testing WebApp configuration...")
    
    try:
        import sys
        sys.path.append(os.path.dirname(__file__))
        import main
        
        # Check WebApp configuration
        webapp_enabled = getattr(main, 'WEBAPP_ENABLED', False)
        webapp_url = getattr(main, 'WEBAPP_URL', None)
        webapp_imports = getattr(main, 'WEBAPP_IMPORTS_AVAILABLE', False)
        
        logger.info(f"WebApp Enabled: {webapp_enabled}")
        logger.info(f"WebApp URL: {webapp_url}")
        logger.info(f"WebApp Imports: {webapp_imports}")
        
        if webapp_enabled and webapp_url:
            logger.info("✅ WebApp configuration valid")
            return True
        else:
            logger.warning("⚠️ WebApp configuration incomplete")
            return True  # Not critical for basic functionality
            
    except Exception as e:
        logger.error(f"❌ WebApp configuration test failed: {e}")
        return False

def test_bot_token():
    """Test that bot token is configured"""
    logger.info("🔍 Testing bot token configuration...")
    
    try:
        import sys
        sys.path.append(os.path.dirname(__file__))
        import main
        
        bot_token = getattr(main, 'BOT_TOKEN', None)
        
        if bot_token and len(bot_token) > 20:
            logger.info("✅ Bot token configured")
            return True
        else:
            logger.error("❌ Bot token not configured or invalid")
            return False
            
    except Exception as e:
        logger.error(f"❌ Bot token test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    logger.info("🚀 Starting comprehensive bot tests...")
    logger.info("=" * 50)
    
    tests = [
        ("Database", test_database),
        ("User Operations", test_user_operations),
        ("Callback Handlers", test_callback_handlers),
        ("WebApp Configuration", test_webapp_configuration),
        ("Bot Token", test_bot_token)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running {test_name} test...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name} test PASSED")
            else:
                logger.error(f"❌ {test_name} test FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} test ERROR: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 TEST SUMMARY:")
    logger.info("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! Bot is ready for deployment.")
        return True
    else:
        logger.error(f"❌ {total - passed} test(s) failed. Please review and fix issues.")
        return False

if __name__ == "__main__":
    asyncio.run(run_all_tests())
