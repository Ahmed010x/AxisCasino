#!/usr/bin/env python3
"""
Verification script for the weekly bonus system implementation
"""
import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the weekly bonus function
from main import weekly_bonus_callback, get_user, init_db, DB_PATH
import aiosqlite
from datetime import datetime, timedelta

class MockUpdate:
    def __init__(self, user_id):
        self.callback_query = MockQuery(user_id)
        
class MockQuery:
    def __init__(self, user_id):
        self.from_user = MockUser(user_id)
        self.data = "weekly_bonus"
        
    async def answer(self, text="", show_alert=False):
        print(f"Bot response: {text}")
        return True
        
    async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
        print("=" * 60)
        print("WEEKLY BONUS UI RESPONSE:")
        print("=" * 60)
        print(text)
        print("=" * 60)
        return True

class MockUser:
    def __init__(self, user_id):
        self.id = user_id

async def test_weekly_bonus_system():
    print("🧪 Testing Weekly Bonus System")
    print("=" * 50)
    
    # Initialize database
    await init_db()
    
    # Test with our test user
    test_user_id = 12345
    
    print(f"Testing weekly bonus for user {test_user_id}...")
    
    # Check user exists
    user = await get_user(test_user_id)
    if not user:
        print(f"❌ Test user {test_user_id} not found!")
        return
    
    print(f"✅ User found: {user['username']} with balance {user['balance']}")
    
    # Create mock update object
    mock_update = MockUpdate(test_user_id)
    mock_context = None
    
    # Test the weekly bonus callback
    print("\n🎁 Testing weekly bonus callback...")
    
    try:
        await weekly_bonus_callback(mock_update, mock_context)
        print("✅ Weekly bonus callback executed successfully!")
    except Exception as e:
        print(f"❌ Error in weekly bonus callback: {e}")
        import traceback
        traceback.print_exc()
        
    # Check user balance after bonus
    user_after = await get_user(test_user_id)
    if user_after:
        print(f"\n💰 User balance after bonus: {user_after['balance']}")
        print(f"📈 Balance change: {user_after['balance'] - user['balance']}")
    
    print("\n✅ Weekly bonus system test completed!")

async def check_database_schema():
    print("\n🔍 Checking database schema...")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if weekly_bonus_claimed field exists
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = await cursor.fetchall()
        
        column_names = [col[1] for col in columns]
        print(f"User table columns: {column_names}")
        
        if 'weekly_bonus_claimed' in column_names:
            print("✅ weekly_bonus_claimed column exists")
        else:
            print("❌ weekly_bonus_claimed column missing")
            
        # Check game_sessions table
        cursor = await db.execute("PRAGMA table_info(game_sessions)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        print(f"Game sessions columns: {column_names}")
        
        # Check test data
        cursor = await db.execute("SELECT COUNT(*) FROM game_sessions WHERE user_id = ?", (12345,))
        bet_count = (await cursor.fetchone())[0]
        print(f"Test user has {bet_count} game sessions")

async def main():
    print("🎰 Weekly Bonus System Verification")
    print("=" * 50)
    
    await check_database_schema()
    await test_weekly_bonus_system()

if __name__ == "__main__":
    asyncio.run(main())
