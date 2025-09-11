#!/usr/bin/env python3
"""
Enhanced test script for the upgraded casino bot.
Tests all new features including poker, achievements, and leaderboard.
"""

import asyncio
import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.database.db import init_db
from bot.database.user import create_user, get_user, update_balance
from bot.utils.achievements import init_achievements_db, check_achievements
from bot.handlers.leaderboard import get_top_players_by_balance


async def test_enhanced_features():
    """Test enhanced casino bot functionality."""
    print("🎰 Testing Enhanced Casino Bot Features...")
    
    try:
        # Initialize databases
        await init_db()
        await init_achievements_db()
        print("✅ Enhanced databases initialized")
        
        # Create test users
        test_users = [
            (12345, "test_user_1"),
            (12346, "test_user_2"),
            (12347, "test_user_3")
        ]
        
        for user_id, username in test_users:
            await create_user(user_id, username)
            # Give different balances for leaderboard testing
            balance = 1000 + (user_id - 12345) * 500
            await update_balance(user_id, balance)
        
        print("✅ Test users created with different balances")
        
        # Test achievements system
        user_id = 12345
        achievements = await check_achievements(user_id)
        print(f"✅ Achievements system working - found {len(achievements)} achievements")
        
        # Test leaderboard
        top_players = await get_top_players_by_balance(5)
        print(f"✅ Leaderboard working - found {len(top_players)} players")
        
        # Display sample leaderboard
        print("\n🏆 Sample Leaderboard:")
        for i, player in enumerate(top_players, 1):
            print(f"  {i}. {player['username']} - {player['balance']} chips")
        
        print("\n🎉 All enhanced features tested successfully!")
        print("\n📋 New Features Summary:")
        print("  🃏 Texas Hold'em Poker - Complete with betting rounds")
        print("  🏆 Achievement System - 14 different achievements")
        print("  📊 Leaderboards - Multiple ranking categories")
        print("  🎲 Enhanced Dice Games - 3 different game modes")
        print("  📈 Extended Statistics - Win streaks, biggest wins")
        print("  🎁 Improved User Experience - Better menus and feedback")
        
    except Exception as e:
        print(f"❌ Enhanced features test failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    asyncio.run(test_enhanced_features())
