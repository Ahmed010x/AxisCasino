#!/usr/bin/env python3
"""
Test script for weekly bonus functionality
"""
import asyncio
import aiosqlite
from datetime import datetime, timedelta
import uuid

DB_PATH = "casino.db"

async def create_test_bets():
    """Create some test bets for last week to test weekly bonus calculation"""
    
    # Calculate last week
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())  # Monday of current week
    last_week_start = week_start - timedelta(days=7)
    last_week_end = week_start
    
    print(f"Current time: {now}")
    print(f"Last week start: {last_week_start}")
    print(f"Last week end: {last_week_end}")
    
    test_user_id = 12345  # Test user ID
    
    # Create test bets for last week
    test_bets = [
        (100, "slots", last_week_start + timedelta(days=1)),
        (50, "blackjack", last_week_start + timedelta(days=2)),
        (75, "roulette", last_week_start + timedelta(days=3)),
        (200, "slots", last_week_start + timedelta(days=4)),
        (25, "dice", last_week_start + timedelta(days=5)),
    ]
    
    total_bets = sum(bet[0] for bet in test_bets)
    expected_bonus = int(total_bets * 0.05)  # 5%
    
    print(f"\nCreating test bets for user {test_user_id}:")
    print(f"Total bet amount: {total_bets}")
    print(f"Expected 5% bonus: {expected_bonus}")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # First, ensure the user exists
        await db.execute("""
            INSERT OR IGNORE INTO users (id, username, balance, total_wagered, total_won, games_played, 
                                       vip_level, created_at, last_active, is_banned, referrer_id, 
                                       daily_bonus_claimed, weekly_bonus_claimed, security_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (test_user_id, "test_user", 1000, 0, 0, 0, 0, 
              now.isoformat(), now.isoformat(), 0, None, '', '', 1))
        
        # Create test game sessions for last week
        for bet_amount, game_type, bet_time in test_bets:
            session_id = str(uuid.uuid4())
            await db.execute("""
                INSERT INTO game_sessions 
                (id, user_id, game_type, bet_amount, win_amount, multiplier, result, game_data, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, test_user_id, game_type, bet_amount, 0, 0, "loss", None, bet_time.isoformat()))
            print(f"  - {game_type}: {bet_amount} chips on {bet_time.strftime('%Y-%m-%d')}")
        
        await db.commit()
    
    print(f"\nTest data created successfully!")
    print(f"You can now test the weekly bonus with user ID {test_user_id}")

async def check_weekly_bonus_calculation():
    """Test the weekly bonus calculation logic"""
    test_user_id = 12345
    
    # Calculate last week
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())  # Monday of current week
    last_week_start = week_start - timedelta(days=7)
    last_week_end = week_start
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT COALESCE(SUM(bet_amount), 0) as total_bets
            FROM game_sessions 
            WHERE user_id = ? 
            AND timestamp >= ? 
            AND timestamp < ?
        """, (test_user_id, last_week_start.isoformat(), last_week_end.isoformat()))
        
        result = await cursor.fetchone()
        total_weekly_bets = result[0] if result else 0
    
    bonus_amount = int(total_weekly_bets * 0.05)  # 5%
    
    print(f"\nWeekly bonus calculation test:")
    print(f"User ID: {test_user_id}")
    print(f"Period: {last_week_start.strftime('%Y-%m-%d')} to {last_week_end.strftime('%Y-%m-%d')}")
    print(f"Total bets found: {total_weekly_bets}")
    print(f"5% bonus amount: {bonus_amount}")
    
    return bonus_amount

async def main():
    print("Testing Weekly Bonus System")
    print("=" * 40)
    
    await create_test_bets()
    await check_weekly_bonus_calculation()
    
    print(f"\nTest completed! You can now test the weekly bonus in Telegram.")

if __name__ == "__main__":
    asyncio.run(main())
