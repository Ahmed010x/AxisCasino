#!/usr/bin/env python3
"""
Test script to verify the bot can initialize properly
"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up minimal environment for testing
os.environ.setdefault("BOT_TOKEN", "dummy_token_for_testing")
os.environ.setdefault("CASINO_DB", "test_casino.db")
os.environ.setdefault("DEMO_MODE", "true")

async def test_bot_initialization():
    try:
        # Import main after setting env vars
        import main
        
        # Test database initialization
        await main.init_db()
        print("✅ Database initialization successful")
        
        # Test user creation
        test_user = await main.create_user(12345, "test_user")
        if test_user:
            print("✅ User creation successful")
        
        # Test balance operations
        balance_updated = await main.update_balance(12345, 10.0)
        if balance_updated:
            print("✅ Balance update successful")
        
        # Test user retrieval
        user = await main.get_user(12345)
        if user and user['balance'] > 0:
            print("✅ User retrieval successful")
        
        print("🎉 All tests passed! Bot is ready to run.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(test_bot_initialization())
        if success:
            print("\n🚀 Bot ready for deployment!")
        else:
            print("\n💥 Bot has issues that need fixing")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Critical error: {e}")
        sys.exit(1)
