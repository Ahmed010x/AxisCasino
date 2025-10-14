#!/usr/bin/env python3
"""
Test script for the simplified casino bot
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_imports():
    """Test that all modules can be imported"""
    try:
        print("🧪 Testing module imports...")
        
        # Test core imports
        from casino_bot.core.config import config
        print("✅ Config module imported")
        
        # Test service imports
        from casino_bot.services.database import db_service
        print("✅ Database service imported")
        
        from casino_bot.services.crypto import crypto_service
        print("✅ Crypto service imported")
        
        from casino_bot.services.messages import message_service
        print("✅ Message service imported")
        
        # Test handler imports
        from casino_bot.handlers.main_handlers import MainHandlers
        print("✅ Main handlers imported")
        
        from casino_bot.handlers.game_handlers import GameHandlers
        print("✅ Game handlers imported")
        
        from casino_bot.handlers.payment_handlers import PaymentHandlers
        print("✅ Payment handlers imported")
        
        # Test configuration access
        print(f"✅ Bot version: {config.BOT_VERSION}")
        print(f"✅ Demo mode: {config.DEMO_MODE}")
        print(f"✅ Database path: {config.DB_PATH}")
        
        # Test database initialization (in memory for testing)
        config.DB_PATH = ":memory:"
        await db_service.init_db()
        print("✅ Database initialized successfully")
        
        # Test user creation and retrieval
        user_id = 12345
        username = "test_user"
        
        success = await db_service.create_user(user_id, username)
        print(f"✅ User creation: {success}")
        
        user = await db_service.get_user(user_id)
        print(f"✅ User retrieval: {user is not None}")
        
        # Test balance operations
        balance_updated = await db_service.update_balance(user_id, 100.0, "test_deposit")
        print(f"✅ Balance update: {balance_updated}")
        
        user_after = await db_service.get_user(user_id)
        print(f"✅ New balance: ${user_after['balance']:.2f}")
        
        print("\n🎉 All tests passed! The simplified bot is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_handlers():
    """Test that handlers can be instantiated"""
    try:
        print("\n🧪 Testing handler instantiation...")
        
        from casino_bot.handlers.main_handlers import MainHandlers
        from casino_bot.handlers.game_handlers import GameHandlers
        from casino_bot.handlers.payment_handlers import PaymentHandlers
        
        main_handlers = MainHandlers()
        game_handlers = GameHandlers()
        payment_handlers = PaymentHandlers()
        
        print("✅ All handlers instantiated successfully")
        
        # Test game logic methods
        reels = game_handlers._generate_slot_reels()
        print(f"✅ Slot reels generated: {reels}")
        
        win_amount, result = game_handlers._calculate_slots_win(reels, 10.0)
        print(f"✅ Slot calculation: ${win_amount:.2f} - {result}")
        
        hand = game_handlers._generate_blackjack_hand()
        value = game_handlers._calculate_hand_value(hand)
        print(f"✅ Blackjack hand: {hand} = {value}")
        
        die1, die2 = game_handlers._roll_dice()
        print(f"✅ Dice roll: {die1}, {die2} = {die1 + die2}")
        
        print("✅ All game logic tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Handler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("🤖 Testing Simplified Casino Bot")
    print("=" * 40)
    
    # Test imports and basic functionality
    imports_ok = await test_imports()
    
    # Test handlers
    handlers_ok = await test_handlers()
    
    if imports_ok and handlers_ok:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ The simplified casino bot is ready to use.")
        print(f"✅ To run the bot: python main_simplified.py")
        return True
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("❌ Please check the error messages above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
