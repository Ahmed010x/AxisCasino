#!/usr/bin/env python3
"""
Simple test to verify the bot components work without event loop issues.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_bot_components():
    """Test that all bot components can be imported and initialized."""
    print("Testing bot components...")
    
    # Test database initialization
    from bot.database.db import init_db
    from bot.utils.achievements import init_achievements_db
    
    try:
        await init_db()
        await init_achievements_db()
        print("✅ Database initialization successful")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
    
    # Test user operations
    from bot.database.user import create_user, get_user
    
    try:
        # Test user creation
        result = await create_user(12345, "test_user")
        if result:
            user = await get_user(12345)
            if user:
                print(f"✅ User operations successful: {user['username']}")
            else:
                print("❌ User retrieval failed")
                return False
        else:
            print("❌ User creation failed")
            return False
    except Exception as e:
        print(f"❌ User operations failed: {e}")
        return False
    
    # Test game imports
    try:
        from bot.games.slots import calculate_win
        from bot.games.blackjack import BlackjackGame
        from bot.games.roulette import spin_wheel, check_bet_win
        from bot.games.dice import roll_dice, get_dice_emoji
        from bot.games.poker import PokerGame
        print("✅ All game modules imported successfully")
    except Exception as e:
        print(f"❌ Game import failed: {e}")
        return False
    
    # Test handler imports
    try:
        from bot.handlers.start import start, help_command
        from bot.handlers.account import balance, daily_bonus, stats
        from bot.handlers.games import slots, blackjack, roulette, dice, poker, achievements
        from bot.handlers.leaderboard import leaderboard_command
        from bot.handlers.callbacks import button_callback
        from bot.handlers.payment_handlers import payments_menu
        print("✅ All handler modules imported successfully")
    except Exception as e:
        print(f"❌ Handler import failed: {e}")
        return False
    
    print("✅ All components working correctly!")
    return True

if __name__ == '__main__':
    # Check if bot token is set
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token or bot_token == 'your_telegram_bot_token_here':
        print("❌ BOT_TOKEN not set or using placeholder value")
        print("Please set a real bot token in .env file")
    else:
        print(f"✅ BOT_TOKEN is set (length: {len(bot_token)})")
    
    # Run component tests
    try:
        result = asyncio.run(test_bot_components())
        if result:
            print("\n🎉 All tests passed! Bot should work correctly.")
            print("To run the bot:")
            print('1. Make sure your bot token is correct in .env file')
            print('2. Run: python main.py')
            print('3. If you get event loop errors, try running in a fresh terminal')
        else:
            print("\n❌ Some tests failed. Please fix the issues above.")
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
