#!/usr/bin/env python3
"""
Quick bot startup test to verify everything works
"""

import asyncio
import sys
import os
import signal
from main import async_main, init_db, get_house_balance_display

async def test_bot_startup():
    """Test that the bot can start up properly"""
    print("🧪 Testing Bot Startup...")
    
    try:
        # Test database initialization
        print("1. Testing database initialization...")
        await init_db()
        print("✅ Database initialized successfully")
        
        # Test house balance display
        print("2. Testing house balance display...")
        display = await get_house_balance_display()
        print("✅ House balance display generated:")
        print(display)
        
        print("\n🎉 All startup tests passed!")
        print("✅ Bot is ready to run!")
        
        return True
        
    except Exception as e:
        print(f"❌ Startup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_bot_startup())
    if success:
        print("\n🚀 To start the bot, run: python main.py")
        sys.exit(0)
    else:
        print("\n❌ Fix the issues above before starting the bot")
        sys.exit(1)
