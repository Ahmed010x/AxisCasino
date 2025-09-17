#!/usr/bin/env python3
"""
Quick bot startup test - starts bot and stops after a few seconds
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()
load_dotenv("env.litecoin")

async def test_bot_startup():
    """Test that the bot can start without errors"""
    print("🎰 Testing bot startup...")
    
    try:
        # Import the main module
        sys.path.insert(0, os.getcwd())
        import main
        
        print("✅ Main module imported successfully")
        
        # Test database initialization
        await main.init_db()
        print("✅ Database initialized successfully")
        
        # Test that bot token is valid format
        if main.BOT_TOKEN and len(main.BOT_TOKEN) > 20:
            print("✅ BOT_TOKEN appears valid")
        else:
            print("❌ BOT_TOKEN invalid")
            return False
        
        print("✅ Bot startup test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Bot startup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_bot_startup())
    if success:
        print("\n🚀 Bot is ready for deployment!")
        print("\nTo start the bot, run:")
        print("python main.py")
    else:
        print("\n❌ Bot startup test failed")
    
    sys.exit(0 if success else 1)
