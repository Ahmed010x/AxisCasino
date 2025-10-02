#!/usr/bin/env python3
"""
Test bot startup and functionality
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_env_result = load_dotenv()
print(f"Environment loaded: {load_env_result}")

# Check if BOT_TOKEN is available
bot_token = os.getenv('BOT_TOKEN')
if not bot_token:
    print("❌ BOT_TOKEN not found in environment")
    sys.exit(1)
else:
    print(f"✅ BOT_TOKEN found: {bot_token[:10]}...")

# Import main module
try:
    import main
    print("✅ Main module imported successfully")
except ImportError as e:
    print(f"❌ Error importing main module: {e}")
    sys.exit(1)

async def test_database():
    """Test database initialization"""
    try:
        await main.init_db()
        print("✅ Database initialized successfully")
        
        # Test user creation
        test_user_id = 123456789
        user = await main.get_user(test_user_id)
        if not user:
            await main.create_user(test_user_id, "TestUser")
            user = await main.get_user(test_user_id)
            print(f"✅ Test user created: {user}")
        else:
            print(f"✅ Test user exists: {user}")
            
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

async def test_game_functions():
    """Test game logic functions"""
    try:
        # Test slots
        reels = main.generate_slot_reels()
        win_amount, result = main.calculate_slots_win(reels, 10.0)
        print(f"✅ Slots test: {reels} -> ${win_amount:.2f} ({result})")
        
        # Test blackjack
        hand = main.generate_blackjack_hand()
        value = main.calculate_hand_value(hand)
        print(f"✅ Blackjack test: {hand} -> {value}")
        
        # Test dice
        dice1, dice2 = main.roll_dice()
        print(f"✅ Dice test: {dice1}, {dice2}")
        
        return True
    except Exception as e:
        print(f"❌ Game functions error: {e}")
        return False

async def main_test():
    """Run all tests"""
    print("🚀 Starting bot functionality test...\n")
    
    db_ok = await test_database()
    game_ok = await test_game_functions()
    
    if db_ok and game_ok:
        print("\n✅ All tests passed! Bot is ready to run.")
        return True
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    asyncio.run(main_test())
