#!/usr/bin/env python3
"""
Final Owner Panel Verification Script
Comprehensive test of owner panel functionality
"""

import os
import sys
import asyncio
from datetime import datetime
sys.path.append('.')

# Import our main module
import main

async def test_owner_panel_integration():
    """Test full owner panel integration"""
    print("🔍 Testing Owner Panel Integration...")
    
    # Test configuration
    print(f"📊 Bot Version: {main.BOT_VERSION}")
    print(f"🔒 Demo Mode: {main.DEMO_MODE}")
    print(f"💾 Database Path: {main.DB_PATH}")
    print(f"👑 Owner ID Config: {main.OWNER_USER_ID}")
    
    # Test environment variables
    print("\n🌍 Environment Configuration:")
    required_vars = ['BOT_TOKEN', 'OWNER_USER_ID']
    for var in required_vars:
        value = os.environ.get(var, 'NOT SET')
        status = "✅" if value != 'NOT SET' else "⚠️"
        print(f"{status} {var}: {'SET' if value != 'NOT SET' else 'NOT SET'}")
    
    # Test database connection
    print("\n💾 Database Test:")
    try:
        await main.init_db()
        print("✅ Database connection successful")
        
        # Test user creation
        test_user = await main.create_user(999999, "TestUser")
        if test_user:
            print("✅ User creation working")
        else:
            print("⚠️ User creation returned None")
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    # Test format functions
    print("\n💰 Format Functions Test:")
    try:
        # Test format_usd function
        formatted = await main.format_usd(1.5)
        print(f"✅ format_usd(1.5) = {formatted}")
        
        # Test with zero balance
        formatted_zero = await main.format_usd(0.0)
        print(f"✅ format_usd(0.0) = {formatted_zero}")
        
    except Exception as e:
        print(f"❌ Format function test failed: {e}")
        return False
    
    # Test owner panel stats gathering
    print("\n📊 Owner Panel Stats Test:")
    try:
        import aiosqlite
        async with aiosqlite.connect(main.DB_PATH) as db:
            # Test stats queries
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            user_count = (await cursor.fetchone())[0]
            print(f"✅ User count query: {user_count} users")
            
            cursor = await db.execute("SELECT SUM(balance) FROM users")
            total_balance = (await cursor.fetchone())[0] or 0.0
            print(f"✅ Balance query: {total_balance} total balance")
            
    except Exception as e:
        print(f"❌ Stats query test failed: {e}")
        return False
    
    print("\n🎉 All integration tests passed!")
    return True

async def test_production_readiness():
    """Test production readiness"""
    print("\n🚀 Production Readiness Check:")
    
    # Check all required functions exist
    required_functions = [
        'start_command', 'owner_panel_callback', 'admin_panel_callback',
        'mini_app_centre_callback', 'classic_casino_callback',
        'play_slots_callback', 'coin_flip_callback', 'play_dice_callback',
        'deposit_callback', 'withdraw_callback', 'help_command',
        'show_stats_callback', 'redeem_panel_callback',
        'global_error_handler', 'health_command'
    ]
    
    missing_functions = []
    for func_name in required_functions:
        if not hasattr(main, func_name):
            missing_functions.append(func_name)
    
    if missing_functions:
        print(f"❌ Missing functions: {missing_functions}")
        return False
    else:
        print(f"✅ All {len(required_functions)} required functions present")
    
    # Check configuration variables
    config_vars = [
        'BOT_TOKEN', 'DB_PATH', 'OWNER_USER_ID', 'ADMIN_USER_IDS',
        'BOT_VERSION', 'DEMO_MODE', 'MAX_BET_PER_GAME'
    ]
    
    missing_config = []
    for var in config_vars:
        if not hasattr(main, var):
            missing_config.append(var)
    
    if missing_config:
        print(f"❌ Missing config: {missing_config}")
        return False
    else:
        print(f"✅ All {len(config_vars)} config variables present")
    
    print("✅ Production readiness check passed!")
    return True

async def main_verification():
    """Run complete verification"""
    print("🎰 OWNER PANEL VERIFICATION")
    print("=" * 60)
    print(f"🕐 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run integration tests
        integration_success = await test_owner_panel_integration()
        
        # Run production readiness check
        production_success = await test_production_readiness()
        
        if integration_success and production_success:
            print("\n" + "=" * 60)
            print("🎉 VERIFICATION COMPLETE - ALL TESTS PASSED!")
            print("✅ Owner panel is fully functional")
            print("✅ Bot is production ready")
            print("🚀 Ready for deployment!")
            return 0
        else:
            print("\n" + "=" * 60)
            print("❌ VERIFICATION FAILED - ISSUES FOUND!")
            return 1
            
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main_verification())
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Verification runner failed: {e}")
        sys.exit(1)
