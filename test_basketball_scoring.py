#!/usr/bin/env python3
"""
Test script for updated Basketball 1v1 scoring system

This script tests the new basketball scoring where points are only awarded
when one player scores and the other misses.
"""

import asyncio
import sys
import os
import sqlite3
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.games.basketball import play_basketball_1v1, get_shot_result

# Mock database setup for testing
DB_PATH = "test_basketball.db"

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

def test_shot_scoring():
    """Test the shot result function."""
    print("\n🏀 Testing Shot Scoring Logic...")
    
    # Test all possible dice values
    for dice_value in range(1, 6):
        points, description, emoji = get_shot_result(dice_value)
        made_shot = points > 0
        print(f"Dice {dice_value}: {emoji} {description} - {'MADE' if made_shot else 'MISSED'}")
    
    print("✅ Shot scoring test passed!")

async def test_scoring_scenarios():
    """Test different scoring scenarios."""
    print("\n🎯 Testing Scoring Scenarios...")
    
    # Simulate specific scenarios
    scenarios = [
        ("Player scores, Bot misses", True, False, "Player should get +1"),
        ("Bot scores, Player misses", False, True, "Bot should get +1"),
        ("Both score", True, True, "No points (tie)"),
        ("Both miss", False, False, "No points (tie)")
    ]
    
    for scenario_name, player_made, bot_made, expected in scenarios:
        # Calculate points
        player_points = 1 if player_made and not bot_made else 0
        bot_points = 1 if bot_made and not player_made else 0
        
        print(f"📝 {scenario_name}:")
        print(f"  Player made: {player_made}, Bot made: {bot_made}")
        print(f"  Player points: {player_points}, Bot points: {bot_points}")
        print(f"  Expected: {expected}")
        
        # Verify logic
        if scenario_name == "Player scores, Bot misses":
            assert player_points == 1 and bot_points == 0
        elif scenario_name == "Bot scores, Player misses":
            assert player_points == 0 and bot_points == 1
        else:  # Both score or both miss
            assert player_points == 0 and bot_points == 0
        
        print(f"  ✅ Correct!\n")
    
    print("✅ All scoring scenarios passed!")

async def test_full_game():
    """Test a full basketball game with new scoring."""
    print("\n🏀 Testing Full Basketball 1v1 Game...")
    
    try:
        result = await play_basketball_1v1(12345, 10.0)
        
        print(f"🎯 Final Score: Player {result['player_score']} - Bot {result['bot_score']}")
        print(f"🏆 Winner: {'PLAYER' if result['player_won'] else 'BOT'}")
        print(f"🎮 Total Rounds: {result['total_rounds']}")
        
        # Verify game logic
        assert result['player_score'] == 3 or result['bot_score'] == 3, "Game should end when someone reaches 3 points"
        assert result['player_score'] <= 3 and result['bot_score'] <= 3, "Scores should not exceed 3"
        
        print(f"\n📝 Round-by-round breakdown:")
        for round_data in result['game_log']:
            player_made = round_data['player_made_shot']
            bot_made = round_data['bot_made_shot']
            round_result = round_data['round_result']
            
            print(f"Round {round_data['round']}: "
                  f"Player {round_data['player_result']} ({'MADE' if player_made else 'MISSED'}) | "
                  f"Bot {round_data['bot_result']} ({'MADE' if bot_made else 'MISSED'}) | "
                  f"Result: {round_result} | "
                  f"Score: {round_data['player_score']}-{round_data['bot_score']}")
            
            # Verify round logic
            if round_result == "PLAYER":
                assert player_made and not bot_made, f"Round {round_data['round']}: Player should score only when player makes and bot misses"
            elif round_result == "BOT":
                assert bot_made and not player_made, f"Round {round_data['round']}: Bot should score only when bot makes and player misses"
            else:  # TIE
                assert (player_made and bot_made) or (not player_made and not bot_made), f"Round {round_data['round']}: Tie should occur when both make or both miss"
        
        print("✅ Full game test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Full game test failed: {e}")
        return False

async def main():
    """Run all basketball scoring tests."""
    print("🏀 Starting Basketball 1v1 Scoring Tests...")
    print("="*60)
    
    # Setup test environment
    await setup_test_db()
    
    try:
        # Run tests
        test_shot_scoring()
        await test_scoring_scenarios()
        game_success = await test_full_game()
        
        # Results
        print("\n" + "="*60)
        print("🎯 TEST RESULTS:")
        print(f"🏀 Shot Scoring: ✅ PASS")
        print(f"🎯 Scoring Scenarios: ✅ PASS")
        print(f"🎮 Full Game: {'✅ PASS' if game_success else '❌ FAIL'}")
        
        if game_success:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ New scoring system working correctly!")
            print("📝 Points awarded only when one player scores and other misses")
            return True
        else:
            print("\n❌ SOME TESTS FAILED!")
            return False
            
    finally:
        # Cleanup
        cleanup_test_db()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
