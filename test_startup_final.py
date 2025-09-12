#!/usr/bin/env python3
"""
Final test to verify the bot can start without any missing function errors
"""
import os
import sys
import asyncio
import logging

# Set up minimal logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set required environment variables for testing
os.environ['BOT_TOKEN'] = 'test_token_123456:ABCDEF'
os.environ['WEBAPP_URL'] = 'https://your-casino-webapp.vercel.app'

async def test_bot_startup():
    """Test if bot can start without errors"""
    try:
        # Import the main module
        from main import BOT_TOKEN, WEBAPP_URL, WEBAPP_ENABLED
        
        print("✅ Main module imported successfully")
        print(f"✅ Bot token: {'Set' if BOT_TOKEN else 'Not set'}")
        print(f"✅ WebApp URL: {WEBAPP_URL}")
        print(f"✅ WebApp enabled: {WEBAPP_ENABLED}")
        
        # Test that all handler functions exist
        from main import (
            start_command, help_command, mini_app_centre_command, webapp_command,
            show_mini_app_centre, classic_casino_callback, inline_games_callback,
            show_balance_callback, main_panel_callback, placeholder_callback,
            handle_callback
        )
        
        print("✅ All callback handlers exist")
        
        # Test database functions
        from main import init_db, get_user
        print("✅ Database functions available")
        
        print("\n🎉 All tests passed! Bot is ready to start.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_bot_startup())
    sys.exit(0 if success else 1)
