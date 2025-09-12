#!/usr/bin/env python3
"""
Test script to verify the bot can start without actually running
"""

import asyncio
import sys
import os

async def test_bot_startup():
    """Test if the bot can initialize without starting"""
    print("🧪 Testing Casino Bot startup...")
    
    try:
        # Import main module
        import main
        
        print("✅ Main module imported successfully")
        print(f"✅ WebApp imports available: {main.WEBAPP_IMPORTS_AVAILABLE}")
        
        # Test database initialization
        await main.init_db()
        print("✅ Database initialization successful")
        
        # Test user creation/retrieval
        test_user = await main.create_user(12345, "TestUser")
        print(f"✅ User creation successful: {test_user}")
        
        retrieved_user = await main.get_user(12345)
        print(f"✅ User retrieval successful: {retrieved_user}")
        
        # Test balance operations
        success = await main.deduct_balance(12345, 100)
        print(f"✅ Balance deduction successful: {success}")
        
        new_balance = await main.update_balance(12345, 50)
        print(f"✅ Balance update successful: {new_balance}")
        
        # Test game session logging
        session_id = await main.log_game_session(12345, "test", 100, 50, "win")
        print(f"✅ Game session logging successful: {session_id}")
        
        print("\n🎉 All startup tests passed!")
        print("🚀 Bot is ready to start!")
        
        # Show configuration
        print(f"\n📋 Configuration:")
        print(f"• WebApp URL: {main.WEBAPP_URL}")
        print(f"• WebApp Enabled: {main.WEBAPP_ENABLED}")
        print(f"• WebApp Imports: {'Available' if main.WEBAPP_IMPORTS_AVAILABLE else 'Fallback mode'}")
        print(f"• Database: {main.DB_PATH}")
        print(f"• Port: {main.PORT}")
        
        return True
        
    except Exception as e:
        print(f"❌ Startup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🎰 Casino Bot Startup Test")
    print("=" * 30)
    
    try:
        success = asyncio.run(test_bot_startup())
        if success:
            print("\n✅ Bot startup test PASSED - Ready for deployment!")
            sys.exit(0)
        else:
            print("\n❌ Bot startup test FAILED")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        sys.exit(1)
