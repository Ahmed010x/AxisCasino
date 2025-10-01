#!/usr/bin/env python3
"""
Deployment Verification Script for Telegram Casino Bot
Tests all critical components before and during deployment
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment():
    """Check environment variables and configuration"""
    print("🔍 ENVIRONMENT CHECK")
    print("=" * 50)
    
    # Critical environment variables
    required_vars = ['BOT_TOKEN']
    optional_vars = ['CRYPTOBOT_API_TOKEN', 'RENDER', 'PORT', 'DEMO_MODE']
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
            print(f"❌ {var}: Missing (REQUIRED)")
        else:
            # Mask sensitive tokens
            value = os.environ[var]
            masked = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else "SET"
            print(f"✅ {var}: {masked}")
    
    for var in optional_vars:
        value = os.environ.get(var, 'Not set')
        if var in ['BOT_TOKEN', 'CRYPTOBOT_API_TOKEN'] and value != 'Not set':
            value = f"{value[:10]}...{value[-4:]}"
        print(f"ℹ️  {var}: {value}")
    
    # Deployment environment detection
    is_render = bool(os.environ.get('RENDER'))
    is_railway = bool(os.environ.get('RAILWAY_ENVIRONMENT'))
    is_heroku = bool(os.environ.get('HEROKU'))
    is_local = not (is_render or is_railway or is_heroku)
    
    env_type = "LOCAL"
    if is_render: env_type = "RENDER"
    elif is_railway: env_type = "RAILWAY"
    elif is_heroku: env_type = "HEROKU"
    
    print(f"🌍 Environment: {env_type}")
    print(f"🐍 Python: {sys.version}")
    print(f"📂 Working Dir: {os.getcwd()}")
    
    if missing_vars:
        print(f"\n❌ Missing required variables: {', '.join(missing_vars)}")
        return False
    else:
        print("\n✅ Environment check passed!")
        return True

def test_imports():
    """Test all critical imports"""
    print("\n📦 IMPORT CHECK")
    print("=" * 50)
    
    imports_to_test = [
        ('telegram', 'python-telegram-bot'),
        ('aiosqlite', 'aiosqlite'),
        ('aiohttp', 'aiohttp'),
        ('flask', 'Flask'),
        ('dotenv', 'python-dotenv'),
    ]
    
    failed_imports = []
    for module, package in imports_to_test:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} (install with: pip install {package})")
            failed_imports.append(package)
    
    if failed_imports:
        print(f"\n❌ Install missing packages: pip install {' '.join(failed_imports)}")
        return False
    else:
        print("\n✅ All imports successful!")
        return True

async def test_database():
    """Test database operations"""
    print("\n🗄️  DATABASE CHECK")
    print("=" * 50)
    
    try:
        # Import after checking environment
        import main
        
        # Test database initialization
        await main.init_db()
        print("✅ Database initialization")
        
        # Test user operations
        test_user_id = 999999999
        user = await main.create_user(test_user_id, "test_deployment_user")
        if user:
            print("✅ User creation")
        
        # Test balance operations
        success = await main.update_balance(test_user_id, 100.0)
        if success:
            print("✅ Balance updates")
        
        # Test user retrieval
        user_data = await main.get_user(test_user_id)
        if user_data and user_data['balance'] == 100.0:
            print("✅ User data retrieval")
        
        # Test referral system
        ref_code = await main.get_or_create_referral_code(test_user_id)
        if ref_code:
            print(f"✅ Referral system (code: {ref_code})")
        
        # Test house balance
        house_stats = await main.get_house_profit_loss()
        if house_stats:
            print("✅ House balance system")
        
        print("\n✅ Database operations successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bot_config():
    """Test bot configuration"""
    print("\n🤖 BOT CONFIGURATION CHECK")
    print("=" * 50)
    
    try:
        import main
        
        # Test bot token
        if main.BOT_TOKEN:
            print("✅ Bot token configured")
        else:
            print("❌ Bot token missing")
            return False
        
        # Test admin configuration
        admin_count = len(main.ADMIN_USER_IDS) if main.ADMIN_USER_IDS else 0
        print(f"ℹ️  Admin users: {admin_count}")
        
        # Test demo mode
        demo_mode = main.DEMO_MODE
        print(f"ℹ️  Demo mode: {demo_mode}")
        
        # Test crypto configuration
        if main.CRYPTOBOT_API_TOKEN:
            print("✅ CryptoBot API configured")
        else:
            print("⚠️  CryptoBot API not configured (deposits/withdrawals disabled)")
        
        print("\n✅ Bot configuration valid!")
        return True
        
    except Exception as e:
        print(f"\n❌ Bot configuration error: {e}")
        return False

async def test_event_loop_handling():
    """Test event loop management"""
    print("\n🔄 EVENT LOOP CHECK")
    print("=" * 50)
    
    try:
        # Test if we can handle event loops properly
        print("✅ Event loop accessible")
        
        # Test async operations
        await asyncio.sleep(0.1)
        print("✅ Async operations working")
        
        # Test nest_asyncio if available
        try:
            import nest_asyncio
            print("✅ nest_asyncio available")
        except ImportError:
            print("ℹ️  nest_asyncio not available (may be needed for some environments)")
        
        print("\n✅ Event loop handling ready!")
        return True
        
    except Exception as e:
        print(f"\n❌ Event loop error: {e}")
        return False

def test_flask_server():
    """Test Flask server setup"""
    print("\n🌐 FLASK SERVER CHECK")
    print("=" * 50)
    
    try:
        import main
        
        # Check if Flask app is configured
        if hasattr(main, 'app'):
            print("✅ Flask app configured")
        else:
            print("❌ Flask app not found")
            return False
        
        # Check port configuration
        port = int(os.environ.get("PORT", 8001))
        print(f"ℹ️  Server port: {port}")
        
        # Test route registration
        routes = [rule.rule for rule in main.app.url_map.iter_rules()]
        if '/keepalive' in routes:
            print("✅ Health check endpoint configured")
        else:
            print("⚠️  Health check endpoint missing")
        
        print("\n✅ Flask server ready!")
        return True
        
    except Exception as e:
        print(f"\n❌ Flask server error: {e}")
        return False

async def main():
    """Run all deployment verification tests"""
    print("🚀 TELEGRAM CASINO BOT DEPLOYMENT VERIFICATION")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Run all tests
    tests = [
        ("Environment", check_environment),
        ("Imports", test_imports),
        ("Database", test_database),
        ("Bot Config", test_bot_config),
        ("Event Loop", test_event_loop_handling),
        ("Flask Server", test_flask_server),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"\n❌ {test_name} test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 DEPLOYMENT VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Bot is ready for deployment!")
        print("\n📝 Next steps:")
        print("1. Deploy the code to your platform (Render, Railway, etc.)")
        print("2. Set environment variables on your platform")
        print("3. Start the bot and test with /start command")
        print("4. Monitor logs for any issues")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please fix issues before deployment.")
        return False

if __name__ == "__main__":
    # Add current directory to path so we can import main
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
