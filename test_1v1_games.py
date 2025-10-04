#!/usr/bin/env python3
"""
Test script for 1v1 Basketball and Dice games

This script tests the new 1v1 functionality for both games.
"""

import asyncio
import sys
import os
import sqlite3
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.games.basketball import play_basketball_1v1
from bot.games.dice import play_dice_1v1

# Mock database setup for testing
DB_PATH = "test_casino.db"

async def setup_test_db():
    """Create a test database with a test user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            games_played INTEGER DEFAULT 0,
            total_wagered REAL DEFAULT 0.0,
            total_won REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create game_sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game_type TEXT NOT NULL,
            bet_amount REAL NOT NULL,
            win_amount REAL DEFAULT 0.0,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    
    # Insert test user with balance
    cursor.execute("""
        INSERT OR REPLACE INTO users 
        (user_id, username, balance, games_played, total_wagered) 
        VALUES (12345, 'test_user', 100.0, 0, 0.0)
    """)
    
    conn.commit()
    conn.close()
    print("✅ Test database setup complete")

def cleanup_test_db():
    """Remove test database."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("🗑️ Test database cleaned up")

async def test_basketball_1v1():
    """Test basketball 1v1 game functionality."""
    print("\n🏀 Testing Basketball 1v1 Game...")
    
    # Test with different bet amounts
    test_cases = [10.0, 25.0, 50.0]
    
    for bet_amount in test_cases:
        print(f"\n💰 Testing bet: ${bet_amount:.2f}")
        
        try:
            result = await play_basketball_1v1(12345, bet_amount)
            
            print(f"🎯 Player Score: {result['player_score']}")
            print(f"🤖 Bot Score: {result['bot_score']}")
            print(f"🏆 Winner: {'PLAYER' if result['player_won'] else 'BOT'}")
            print(f"💵 Bet Amount: ${result['bet_amount']:.2f}")
            print(f"🎉 Win Amount: ${result['win_amount']:.2f}")
            print(f"📊 Net Result: ${result['net_result']:+.2f}")
            print(f"📈 New Balance: ${result['new_balance']:.2f}")
            print(f"🎮 Total Rounds: {result['total_rounds']}")
            
            # Show round details
            print(f"\n📝 Round-by-round breakdown:")
            for round_data in result['game_log']:
                print(f"Round {round_data['round']}: "
                      f"Player {round_data['player_result']} (+{round_data['player_points']}) | "
                      f"Bot {round_data['bot_result']} (+{round_data['bot_points']}) | "
                      f"Score: {round_data['player_score']}-{round_data['bot_score']}")
            
            print(f"✅ Basketball test passed!")
            
        except Exception as e:
            print(f"❌ Basketball test failed: {e}")
            return False
    
    return True

async def test_dice_1v1():
    """Test dice 1v1 game functionality."""
    print("\n🎲 Testing Dice 1v1 Game...")
    
    # Test with different bet amounts
    test_cases = [5.0, 15.0, 30.0]
    
    for bet_amount in test_cases:
        print(f"\n💰 Testing bet: ${bet_amount:.2f}")
        
        try:
            result = await play_dice_1v1(12345, bet_amount)
            
            print(f"🎯 Player Wins: {result['player_wins']}")
            print(f"🤖 Bot Wins: {result['bot_wins']}")
            print(f"🏆 Winner: {'PLAYER' if result['player_won'] else 'BOT'}")
            print(f"💵 Bet Amount: ${result['bet_amount']:.2f}")
            print(f"🎉 Win Amount: ${result['win_amount']:.2f}")
            print(f"📊 Net Result: ${result['net_result']:+.2f}")
            print(f"📈 New Balance: ${result['new_balance']:.2f}")
            print(f"🎮 Total Rounds: {result['total_rounds']}")
            
            # Show round details
            print(f"\n📝 Round-by-round breakdown:")
            for round_data in result['game_log']:
                dice1_str = f"[{round_data['player_dice'][0]},{round_data['player_dice'][1]}]"
                dice2_str = f"[{round_data['bot_dice'][0]},{round_data['bot_dice'][1]}]"
                print(f"Round {round_data['round']}: "
                      f"Player {dice1_str}={round_data['player_total']} | "
                      f"Bot {dice2_str}={round_data['bot_total']} | "
                      f"Winner: {round_data['round_winner']} | "
                      f"Score: {round_data['player_wins']}-{round_data['bot_wins']}")
            
            print(f"✅ Dice test passed!")
            
        except Exception as e:
            print(f"❌ Dice test failed: {e}")
            return False
    
    return True

async def test_game_statistics():
    """Test that game statistics are being recorded properly."""
    print("\n📊 Testing Game Statistics...")
    
    # Check if games were recorded in database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM game_sessions WHERE game_type IN ('basketball_1v1', 'dice_1v1')")
    game_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT game_type, COUNT(*) FROM game_sessions GROUP BY game_type")
    game_types = cursor.fetchall()
    
    cursor.execute("SELECT balance FROM users WHERE user_id = 12345")
    final_balance = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"🎮 Total 1v1 games recorded: {game_count}")
    print(f"📈 Game breakdown:")
    for game_type, count in game_types:
        print(f"  - {game_type}: {count} games")
    print(f"💰 Final user balance: ${final_balance:.2f}")
    
    if game_count > 0:
        print("✅ Game statistics test passed!")
        return True
    else:
        print("❌ Game statistics test failed!")
        return False

async def main():
    """Run all 1v1 game tests."""
    print("🎮 Starting 1v1 Games Test Suite...")
    print("="*50)
    
    # Setup test environment
    await setup_test_db()
    
    try:
        # Run tests
        basketball_success = await test_basketball_1v1()
        dice_success = await test_dice_1v1()
        stats_success = await test_game_statistics()
        
        # Results
        print("\n" + "="*50)
        print("🎯 TEST RESULTS:")
        print(f"🏀 Basketball 1v1: {'✅ PASS' if basketball_success else '❌ FAIL'}")
        print(f"🎲 Dice 1v1: {'✅ PASS' if dice_success else '❌ FAIL'}")
        print(f"📊 Statistics: {'✅ PASS' if stats_success else '❌ FAIL'}")
        
        if all([basketball_success, dice_success, stats_success]):
            print("\n🎉 ALL TESTS PASSED! 1v1 games are working correctly!")
            return True
        else:
            print("\n❌ SOME TESTS FAILED! Check the output above.")
            return False
            
    finally:
        # Cleanup
        cleanup_test_db()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
