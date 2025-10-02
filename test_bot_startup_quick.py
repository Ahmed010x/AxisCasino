#!/usr/bin/env python3
"""
Quick bot startup test to ensure no runtime errors
"""

import asyncio
import logging
import sys
import os

# Suppress most logging during test
logging.getLogger().setLevel(logging.CRITICAL)

async def test_bot_startup():
    """Test if the bot can start without errors"""
    try:
        # Set test environment
        os.environ['BOT_TOKEN'] = 'test_token'
        os.environ['CASINO_DB'] = 'test_casino.db'
        
        # Try to import and initialize main components
        import main
        
        # Test database initialization
        await main.init_db()
        print("✅ Database initialization successful")
        
        # Test bot creation (this will fail due to invalid token but should not crash)
        try:
            app = main.Application.builder().token('test_token').build()
            print("✅ Bot application creation successful")
        except Exception as e:
            if "Invalid token" in str(e) or "Unauthorized" in str(e):
                print("✅ Bot creation test passed (expected token error)")
            else:
                raise
        
        print("✅ Bot startup test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Bot startup test failed: {e}")
        return False
    finally:
        # Clean up test database
        if os.path.exists('test_casino.db'):
            os.remove('test_casino.db')

if __name__ == "__main__":
    result = asyncio.run(test_bot_startup())
    sys.exit(0 if result else 1)
