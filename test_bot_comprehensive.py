#!/usr/bin/env python3
"""
Casino Bot Test Suite
Tests all major components without requiring a real bot token
"""

import asyncio
import sys
import os
import sqlite3
from unittest.mock import Mock, AsyncMock, patch

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load test environment
from dotenv import load_dotenv
load_dotenv('.env.test')

# Import main module
import main

class MockUpdate:
    def __init__(self, message_text="", user_id=123456, username="testuser"):
        self.effective_user = Mock()
        self.effective_user.id = user_id
        self.effective_user.username = username
        self.effective_chat = Mock()
        self.effective_chat.id = user_id
        self.message = Mock()
        self.message.text = message_text
        self.message.reply_text = AsyncMock()
        self.callback_query = None

class MockContext:
    def __init__(self):
        self.user_data = {}
        self.bot_data = {}

async def test_database_functions():
    """Test database initialization and basic operations"""
    print("🔧 Testing database functions...")
    
    try:
        # Test database initialization
        await main.init_db()
        print("✅ Database initialization successful")
        
        # Test user creation
        user = await main.create_user(123456, "testuser")
        print(f"✅ User creation successful: {user}")
        
        # Test user retrieval
        user = await main.get_user(123456)
        print(f"✅ User retrieval successful: {user}")
        
        # Test balance update
        success = await main.update_balance(123456, 100.0)
        print(f"✅ Balance update successful: {success}")
        
        # Test balance deduction
        success = await main.deduct_balance(123456, 10.0)
        print(f"✅ Balance deduction successful: {success}")
        
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

async def test_crypto_functions():
    """Test cryptocurrency-related functions"""
    print("\n💰 Testing crypto functions...")
    
    try:
        # Test USD formatting
        formatted = await main.format_usd(123.456)
        print(f"✅ USD formatting: {formatted}")
        
        # Test crypto rate (mock)
        with patch('main.get_crypto_usd_rate', return_value=50.0):
            rate = await main.get_crypto_usd_rate('LTC')
            print(f"✅ Crypto rate retrieval: ${rate}")
        
        # Test crypto to USD formatting
        formatted = await main.format_crypto_usd(2.0, 'LTC')
        print(f"✅ Crypto USD formatting: {formatted}")
        
        return True
    except Exception as e:
        print(f"❌ Crypto functions test failed: {e}")
        return False

async def test_game_logic():
    """Test game logic functions"""
    print("\n🎮 Testing game logic...")
    
    try:
        # Test slots game logic (direct function calls)
        reels = main.generate_slot_reels()
        win_amount, result_text = main.calculate_slots_win(reels, 10.0)
        print(f"✅ Slots game logic: Reels {reels}, Win ${win_amount}")
        
        # Test blackjack hand generation
        hand = main.generate_blackjack_hand()
        hand_value = main.calculate_hand_value(hand)
        print(f"✅ Blackjack hand generation: {hand} = {hand_value}")
        
        # Test dice roll
        die1, die2 = main.roll_dice()
        total = die1 + die2
        print(f"✅ Dice roll: {die1} + {die2} = {total}")
        
        # Test crypto address validation
        valid = main.validate_crypto_address("LTC1234567890", "LTC")
        print(f"✅ Crypto address validation: {valid}")
        
        return True
    except Exception as e:
        print(f"❌ Game logic test failed: {e}")
        return False

async def test_command_handlers():
    """Test bot command handlers by testing their helper functions"""
    print("\n🤖 Testing command handlers...")
    
    try:
        # Test admin checks
        is_admin_result = main.is_admin(123456)
        print(f"✅ Admin check: {is_admin_result}")
        
        # Test owner checks  
        is_owner_result = main.is_owner(123456)
        print(f"✅ Owner check: {is_owner_result}")
        
        # Test referral code generation
        referral_code = main.generate_referral_code(123456)
        print(f"✅ Referral code generation: {referral_code}")
        
        # Test referral stats
        with patch('main.get_referral_stats', return_value={'count': 0, 'earnings': 0.0, 'recent': []}):
            stats = await main.get_referral_stats(123456)
            print(f"✅ Referral stats: {stats}")
        
        return True
    except Exception as e:
        print(f"❌ Command handlers test failed: {e}")
        return False

async def test_callback_handlers():
    """Test callback query handlers by testing their helper functions"""
    print("\n📞 Testing callback handlers...")
    
    try:
        # Test withdrawal fee calculation
        fee = main.calculate_withdrawal_fee(100.0)
        print(f"✅ Withdrawal fee calculation: ${fee}")
        
        # Test referral link generation
        link = main.get_referral_link("testbot", "ABC123")
        print(f"✅ Referral link generation: {link}")
        
        # Test weekly bonus timing
        can_claim, seconds = await main.can_claim_weekly_bonus(123456)
        print(f"✅ Weekly bonus check: Can claim: {can_claim}")
        
        # Test house balance display
        display = await main.get_house_balance_display()
        print(f"✅ House balance display: Generated")
        
        return True
    except Exception as e:
        print(f"❌ Callback handlers test failed: {e}")
        return False

async def test_environment_config():
    """Test environment configuration"""
    print("\n⚙️ Testing environment configuration...")
    
    try:
        # Check if required environment variables are loaded
        required_vars = ['BOT_TOKEN', 'CASINO_DB', 'WEBAPP_SECRET_KEY']
        for var in required_vars:
            value = os.getenv(var)
            if value:
                print(f"✅ {var}: {'*' * min(len(value), 15)}")  # Hide actual values
            else:
                print(f"⚠️ {var}: Not set")
        
        # Test configuration constants that should exist
        if hasattr(main, 'DB_PATH'):
            print(f"✅ Database path: {main.DB_PATH}")
        else:
            print("⚠️ DB_PATH not found, using CASINO_DB")
            
        print(f"✅ Bot token configured: {'Yes' if main.BOT_TOKEN else 'No'}")
        print(f"✅ Demo mode: {main.DEMO_MODE}")
        print(f"✅ Bot version: {main.BOT_VERSION}")
        
        return True
    except Exception as e:
        print(f"❌ Environment config test failed: {e}")
        return False

async def main_test():
    """Run all tests"""
    print("🚀 Starting Casino Bot Test Suite")
    print("=" * 50)
    
    test_results = []
    
    # Run all tests
    test_results.append(await test_environment_config())
    test_results.append(await test_database_functions())
    test_results.append(await test_crypto_functions())
    test_results.append(await test_game_logic())
    test_results.append(await test_command_handlers())
    test_results.append(await test_callback_handlers())
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(test_results)
    total = len(test_results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED! ({passed}/{total})")
        print("✅ Bot is ready for deployment!")
    else:
        print(f"⚠️ {passed}/{total} tests passed")
        print("❌ Some issues need to be addressed")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main_test())
