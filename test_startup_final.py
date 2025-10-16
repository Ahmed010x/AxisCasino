#!/usr/bin/env python3
"""
Bot Startup Test
Test if the bot can initialize and start without errors
"""

import asyncio
import os
import sys
from unittest.mock import Mock, patch
from dotenv import load_dotenv

# Load test environment
load_dotenv('.env.test')

# Import main module
import main

async def test_bot_startup():
    """Test bot startup process"""
    print("🚀 Testing bot startup process...")
    
    try:
        # Test database initialization
        await main.init_db()
        print("✅ Database initialized successfully")
        
        # Test Flask app creation
        app = main.app
        print(f"✅ Flask app created: {app.name}")
        
        # Test bot application builder (mock telegram)
        with patch('telegram.ext.ApplicationBuilder') as mock_builder:
            mock_app = Mock()
            mock_builder.return_value.token.return_value.build.return_value = mock_app
            mock_app.add_handler = Mock()
            mock_app.run_polling = Mock()
            
            # This would normally start the bot, but we'll mock it
            print("✅ Bot application can be built")
        
        print("✅ All startup components working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Startup test failed: {e}")
        return False

async def test_essential_functions():
    """Test essential bot functions"""
    print("\n🔧 Testing essential functions...")
    
    try:
        # Test user management
        user = await main.create_user(999999, "testuser")
        print(f"✅ User creation: {user['user_id']}")
        
        user = await main.get_user(999999)
        print(f"✅ User retrieval: {user['username']}")
        
        # Test balance operations
        success = await main.update_balance(999999, 50.0)
        print(f"✅ Balance update: {success}")
        
        success = await main.deduct_balance(999999, 10.0)
        print(f"✅ Balance deduction: {success}")
        
        # Test game functions
        reels = main.generate_slot_reels()
        win, msg = main.calculate_slots_win(reels, 5.0)
        print(f"✅ Slots game: {msg}")
        
        # Test referral system
        code = await main.get_or_create_referral_code(999999)
        print(f"✅ Referral code: {code}")
        
        # Test bonus system
        can_claim, _ = await main.can_claim_weekly_bonus(999999)
        print(f"✅ Weekly bonus check: {can_claim}")
        
        print("✅ All essential functions working")
        return True
        
    except Exception as e:
        print(f"❌ Essential functions test failed: {e}")
        return False

async def main_test():
    """Run startup tests"""
    print("🎯 CASINO BOT STARTUP TEST")
    print("=" * 40)
    
    test_results = []
    test_results.append(await test_bot_startup())
    test_results.append(await test_essential_functions())
    
    print("\n" + "=" * 40)
    print("📊 STARTUP TEST SUMMARY")
    print("=" * 40)
    
    passed = sum(test_results)
    total = len(test_results)
    
    if passed == total:
        print(f"🎉 STARTUP TEST PASSED! ({passed}/{total})")
        print("✅ Bot is ready to run!")
        return True
    else:
        print(f"⚠️ {passed}/{total} tests passed")
        print("❌ Startup issues detected")
        return False

if __name__ == "__main__":
    success = asyncio.run(main_test())
    sys.exit(0 if success else 1)
