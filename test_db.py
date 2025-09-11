#!/usr/bin/env python3
"""
Test script to verify database functionality
"""

import asyncio
import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.database.db import init_db
from bot.database.user import create_user, get_user, update_balance


async def test_database():
    """Test database operations."""
    print("🧪 Testing database functionality...")
    
    try:
        # Initialize database
        await init_db()
        print("✅ Database initialized successfully")
        
        # Create test user
        test_user_id = 12345
        test_username = "test_user"
        
        await create_user(test_user_id, test_username)
        print("✅ Test user created")
        
        # Get user
        user = await get_user(test_user_id)
        if user:
            print(f"✅ User retrieved: {user['username']}, Balance: {user['balance']}")
        
        # Update balance
        await update_balance(test_user_id, 2000)
        user = await get_user(test_user_id)
        print(f"✅ Balance updated: {user['balance']}")
        
        print("\n🎉 All database tests passed!")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    asyncio.run(test_database())
