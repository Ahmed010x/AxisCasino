#!/usr/bin/env python3
"""Quick test script to test the bot's /start command logic"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.getcwd())

from main import init_db, get_user, create_user

async def test_start_logic():
    """Test the start command logic manually"""
    print("Testing /start command logic...")
    
    # Initialize database
    await init_db()
    print("✅ Database initialized")
    
    # Test user ID (fake)
    test_user_id = 12345
    test_username = "test_user"
    
    # Check if user exists
    existing = await get_user(test_user_id)
    print(f"Existing user: {existing}")
    
    if not existing:
        # Create new user
        await create_user(test_user_id, test_username)
        print(f"✅ User created: {test_user_id} ({test_username})")
        
        # Verify creation
        new_user = await get_user(test_user_id)
        print(f"New user data: {new_user}")
    else:
        print(f"User already exists: {existing}")

if __name__ == "__main__":
    asyncio.run(test_start_logic())
