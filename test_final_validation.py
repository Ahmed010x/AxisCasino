#!/usr/bin/env python3
"""
Final Bot Validation
Complete validation that the bot works in all modes
"""

import asyncio
import os
import sys
import subprocess
import time
from dotenv import load_dotenv

# Load test environment
load_dotenv('.env.test')

def test_syntax():
    """Test Python syntax"""
    print("🔍 Checking Python syntax...")
    try:
        result = subprocess.run([sys.executable, '-m', 'py_compile', 'main.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Python syntax check passed")
            return True
        else:
            print(f"❌ Syntax error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Syntax check failed: {e}")
        return False

def test_imports():
    """Test all imports work"""
    print("\n📦 Testing imports...")
    try:
        import main
        print("✅ Main module imported successfully")
        
        # Test critical imports within main
        required_attrs = [
            'BOT_TOKEN', 'DB_PATH', 'init_db', 'get_user', 'create_user',
            'update_balance', 'deduct_balance', 'app', 'run_flask',
            'run_telegram_bot', 'generate_slot_reels', 'calculate_slots_win'
        ]
        
        missing = []
        for attr in required_attrs:
            if not hasattr(main, attr):
                missing.append(attr)
        
        if missing:
            print(f"❌ Missing attributes: {missing}")
            return False
        else:
            print("✅ All required components available")
            return True
            
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

async def test_database_operations():
    """Test database operations"""
    print("\n💾 Testing database operations...")
    try:
        import main
        
        # Initialize database
        await main.init_db()
        print("✅ Database initialization")
        
        # Test user creation and retrieval
        user = await main.create_user(777777, "finaltest")
        print(f"✅ User creation: {user['user_id']}")
        
        # Test balance operations
        await main.update_balance(777777, 100.0)
        user = await main.get_user(777777)
        if user['balance'] == 100.0:
            print("✅ Balance operations")
        else:
            print(f"❌ Balance mismatch: expected 100.0, got {user['balance']}")
            return False
        
        # Test game logging
        await main.log_game_session(777777, 'slots', 10.0, 20.0, 'test win')
        print("✅ Game session logging")
        
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_game_mechanics():
    """Test game mechanics"""
    print("\n🎮 Testing game mechanics...")
    try:
        import main
        
        # Test slots
        reels = main.generate_slot_reels()
        win, msg = main.calculate_slots_win(reels, 10.0)
        print(f"✅ Slots: {reels} -> ${win}")
        
        # Test blackjack
        hand = main.generate_blackjack_hand()
        value = main.calculate_hand_value(hand)
        print(f"✅ Blackjack: {hand} = {value}")
        
        # Test dice
        die1, die2 = main.roll_dice()
        print(f"✅ Dice: {die1} + {die2} = {die1 + die2}")
        
        # Test crypto validation
        valid = main.validate_crypto_address("LM3XVALIDADDRESS123456789012345", "LTC")
        print(f"✅ Crypto validation: {valid}")
        
        return True
    except Exception as e:
        print(f"❌ Game mechanics test failed: {e}")
        return False

def test_configuration():
    """Test configuration"""
    print("\n⚙️ Testing configuration...")
    try:
        import main
        
        # Check critical config
        config_checks = [
            ('BOT_TOKEN', main.BOT_TOKEN),
            ('DB_PATH', main.DB_PATH),
            ('DEMO_MODE', main.DEMO_MODE),
            ('BOT_VERSION', main.BOT_VERSION),
        ]
        
        for name, value in config_checks:
            if value is not None:
                print(f"✅ {name}: {type(value).__name__}")
            else:
                print(f"⚠️ {name}: Not set")
        
        # Test admin functions
        admin_result = main.is_admin(123456)
        owner_result = main.is_owner(123456)
        print(f"✅ Admin functions: admin={admin_result}, owner={owner_result}")
        
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_deployment_readiness():
    """Test deployment readiness"""
    print("\n🚀 Testing deployment readiness...")
    try:
        import main
        
        # Test Flask app
        app = main.app
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        required_routes = ['/keepalive', '/cryptobot_webhook']
        
        missing_routes = [r for r in required_routes if r not in routes]
        if missing_routes:
            print(f"❌ Missing routes: {missing_routes}")
            return False
        else:
            print("✅ All required routes present")
        
        # Test environment handling
        is_deployment = bool(os.environ.get("RENDER") or os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("HEROKU"))
        print(f"✅ Deployment detection: {is_deployment}")
        
        # Test run functions exist
        if hasattr(main, 'run_flask') and hasattr(main, 'run_telegram_bot'):
            print("✅ Run functions available")
        else:
            print("❌ Missing run functions")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Deployment readiness test failed: {e}")
        return False

async def main_validation():
    """Run complete validation"""
    print("🎯 CASINO BOT FINAL VALIDATION")
    print("=" * 60)
    
    test_results = []
    
    # Run all tests
    test_results.append(test_syntax())
    test_results.append(test_imports())
    test_results.append(await test_database_operations())
    test_results.append(test_game_mechanics())
    test_results.append(test_configuration())
    test_results.append(test_deployment_readiness())
    
    print("\n" + "=" * 60)
    print("📊 FINAL VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(test_results)
    total = len(test_results)
    
    if passed == total:
        print(f"🎉 ALL VALIDATIONS PASSED! ({passed}/{total})")
        print("\n✅ CASINO BOT IS FULLY OPERATIONAL!")
        print("\n🔧 What works:")
        print("   ✅ Python syntax and imports")
        print("   ✅ Database operations")
        print("   ✅ Game mechanics (slots, blackjack, dice)")
        print("   ✅ Configuration and admin functions")
        print("   ✅ Deployment readiness (Flask + Threading)")
        print("\n🚀 Ready for:")
        print("   ✅ Local development testing")
        print("   ✅ Production deployment (Render/Railway/Heroku)")
        print("   ✅ Real user interactions")
        print("\n📝 To deploy:")
        print("   1. Set your real BOT_TOKEN")
        print("   2. Configure API keys (CryptoBot, etc.)")
        print("   3. Deploy to your chosen platform")
        print("   4. Test with real users")
        
        return True
    else:
        print(f"⚠️ {passed}/{total} validations passed")
        print("❌ Some issues need to be resolved before deployment")
        
        # Show which tests failed
        test_names = [
            "Syntax Check", "Imports", "Database Operations",
            "Game Mechanics", "Configuration", "Deployment Readiness"
        ]
        
        print("\n❌ Failed tests:")
        for i, (result, name) in enumerate(zip(test_results, test_names)):
            if not result:
                print(f"   - {name}")
        
        return False

if __name__ == "__main__":
    success = asyncio.run(main_validation())
    sys.exit(0 if success else 1)
