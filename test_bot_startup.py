#!/usr/bin/env python3
"""
Test bot startup without actually running the bot
"""
import os
import sys
import asyncio
from unittest.mock import patch

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_bot_startup():
    """Test if the bot can initialize without errors"""
    print("🧪 Testing bot startup...")
    
    # Set minimal required environment variables
    os.environ['BOT_TOKEN'] = 'test_token_123:fake_token_for_testing'
    os.environ['WEBAPP_ENABLED'] = 'false'  # Disable WebApp for testing
    
    try:
        # Import main module
        from main import init_db, get_user, create_user
        
        print("✅ Main module imported successfully")
        
        # Test database initialization
        await init_db()
        print("✅ Database initialization successful")
        
        # Test user creation
        test_user = await create_user(12345, "test_user")
        print(f"✅ User creation successful: {test_user}")
        
        # Test user retrieval
        retrieved_user = await get_user(12345)
        print(f"✅ User retrieval successful: {retrieved_user}")
        
        print("🎉 All startup tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Startup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_bot_startup())
    sys.exit(0 if result else 1)
