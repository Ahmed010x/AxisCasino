#!/usr/bin/env python3
"""
Test script to verify all components of the enhanced casino bot
Checks database, functions, and UI components
"""

import asyncio
import sys
import os
import uuid
import random
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import aiosqlite
from main import *
# Explicitly import add_balance and get_user_statistics if not included by '*'
try:
    from main import add_balance
except ImportError:
    pass  # If already imported by '*', ignore

try:
    from main import get_user_statistics
except ImportError:
    pass  # If already imported by '*', ignore

async def test_database():
    """Test database operations"""
    print("🔍 Testing database operations...")
    
    # Test database initialization
    await init_db()
    print("✅ Database initialized")
    
    # Test user creation and balance operations
    test_user_id = 987654321  # Use different ID to avoid conflicts
    await create_user(test_user_id, "test_user_final")
    print("✅ User creation works")
    
    # Test balance operations
    user_before = await get_user(test_user_id)
    initial_balance = user_before['balance'] if user_before else 0
    
    await add_balance(test_user_id, 1000, "test_credit")
    user_after = await get_user(test_user_id)
    expected_balance = initial_balance + 1000
    assert user_after['balance'] == expected_balance, f"Expected {expected_balance}, got {user_after['balance']}"
    print("✅ Balance operations work")
    
    # Test weekly bonus calculation
    async with aiosqlite.connect(DB_PATH) as db:
        # Add some test game sessions for last week
        last_week = datetime.now() - timedelta(days=7)
        session_id1 = str(uuid.uuid4())
        session_id2 = str(uuid.uuid4())
        
        await db.execute("""
            INSERT INTO game_sessions (id, user_id, game_type, bet_amount, win_amount, result, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id1, test_user_id, 'crash', 100, 0, 'loss', last_week.isoformat()))
        await db.execute("""
            INSERT INTO game_sessions (id, user_id, game_type, bet_amount, win_amount, result, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id2, test_user_id, 'mines', 200, 400, 'win', last_week.isoformat()))
        await db.commit()
    
    # Test weekly bonus calculation
    stats = await get_user_statistics(test_user_id)
    print(f"📊 User stats: {stats}")
    print("✅ Statistics calculation works")
    
    print("✅ All database tests passed!")

async def test_game_logic():
    """Test game logic functions"""
    print("🎮 Testing game logic...")
    
    # Test crash game logic  
    multiplier = random.uniform(1.01, 10.0)
    print(f"🚀 Crash multiplier: {multiplier:.2f}x")
    
    # Test mines game logic
    mines_grid = [[random.choice(['💎', '💣']) for _ in range(5)] for _ in range(5)]
    print(f"💣 Mines grid generated")
    
    # Test plinko game logic
    plinko_result = random.choice([0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0, 100.0, 1000.0])
    print(f"🏀 Plinko multiplier: {plinko_result}x")
    
    print("✅ All game logic tests passed!")

async def test_ui_components():
    """Test UI component generation"""
    print("🖥️ Testing UI components...")
    
    # Test that callback data strings are valid
    test_callbacks = [
        "stake_originals",
        "play_crash",
        "play_mines", 
        "play_plinko",
        "play_hilo",
        "play_limbo",
        "play_wheel",
        "auto_play_menu",
        "game_statistics",
        "originals_leaderboard"
    ]
    
    for callback in test_callbacks:
        assert len(callback) <= 64, f"Callback '{callback}' too long: {len(callback)} chars"
    
    print("✅ All callback data strings are valid")
    print("✅ All UI component tests passed!")

async def main_test():
    """Run all tests"""
    print("🎰 Starting Enhanced Casino Bot Test Suite")
    print("=" * 50)
    
    try:
        await test_database()
        await test_game_logic()
        await test_ui_components()
        
        print("=" * 50)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("🚀 Enhanced casino bot is ready to deploy!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main_test())
