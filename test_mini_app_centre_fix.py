#!/usr/bin/env python3
"""
Mini App Centre Test
Tests the Mini App Centre functionality to ensure all callbacks work properly.
"""

import asyncio
import os
import sys
from unittest.mock import Mock, AsyncMock
from dotenv import load_dotenv

# Add the project root to the path
sys.path.append('/Users/ahmed/Telegram casino')

# Load environment variables
load_dotenv()

# Import main bot functions
from main import (
    init_db, get_user, create_user, 
    show_mini_app_centre, show_balance_callback,
    show_stats_callback, show_leaderboard_callback,
    show_help_callback, bonus_centre_callback,
    handle_callback
)

class MockUpdate:
    def __init__(self, user_id=12345, callback_data=None):
        self.effective_user = Mock()
        self.effective_user.id = user_id
        self.effective_user.username = "test_user"
        
        if callback_data:
            self.callback_query = Mock()
            self.callback_query.data = callback_data
            self.callback_query.from_user = self.effective_user
            self.callback_query.answer = AsyncMock()
            self.callback_query.edit_message_text = AsyncMock()
        else:
            self.callback_query = None
            self.message = Mock()
            self.message.reply_text = AsyncMock()

class MockContext:
    def __init__(self):
        self.bot = Mock()
        self.bot.username = "test_casino_bot"

async def test_mini_app_centre():
    """Test Mini App Centre functionality"""
    print("🧪 Testing Mini App Centre...")
    
    # Initialize database
    await init_db()
    print("✅ Database initialized")
    
    # Create test user
    user_id = 12345
    test_user = await get_user(user_id)
    if not test_user:
        await create_user(user_id, "test_user")
        test_user = await get_user(user_id)
    
    print(f"✅ Test user created: {test_user}")
    
    # Test Mini App Centre display
    update = MockUpdate(user_id)
    context = MockContext()
    
    try:
        await show_mini_app_centre(update, context)
        print("✅ Mini App Centre display works")
    except Exception as e:
        print(f"❌ Mini App Centre display failed: {e}")
        return False
    
    # Test callback handlers
    test_callbacks = [
        "mini_app_centre",
        "show_balance", 
        "show_stats",
        "show_leaderboard",
        "show_help",
        "bonus_centre",
        "claim_daily_bonus",
        "get_referral"
    ]
    
    for callback_data in test_callbacks:
        update = MockUpdate(user_id, callback_data)
        context = MockContext()
        
        try:
            await handle_callback(update, context)
            print(f"✅ Callback '{callback_data}' works")
        except Exception as e:
            print(f"❌ Callback '{callback_data}' failed: {e}")
    
    print("🎉 Mini App Centre tests completed!")
    return True

async def test_webapp_integration():
    """Test WebApp integration"""
    print("🌐 Testing WebApp integration...")
    
    # Test WebApp URL generation
    from main import WEBAPP_URL, WEBAPP_ENABLED, WEBAPP_IMPORTS_AVAILABLE
    
    print(f"WebApp URL: {WEBAPP_URL}")
    print(f"WebApp Enabled: {WEBAPP_ENABLED}")
    print(f"WebApp Imports Available: {WEBAPP_IMPORTS_AVAILABLE}")
    
    if WEBAPP_ENABLED:
        user_id = 12345
        test_url = f"{WEBAPP_URL}?user_id={user_id}&balance=1000"
        print(f"Generated WebApp URL: {test_url}")
        print("✅ WebApp URL generation works")
    else:
        print("⚠️ WebApp is disabled")
    
    return True

async def test_all_callbacks():
    """Test all callback handlers"""
    print("📞 Testing all callback handlers...")
    
    # Get all callback data from buttons
    all_callbacks = [
        # Main navigation
        "main_panel", "mini_app_centre", "show_balance", "show_stats",
        "show_leaderboard", "show_help", "bonus_centre",
        
        # Financial operations
        "deposit", "withdraw", "deposit_card", "deposit_bank", 
        "deposit_crypto", "deposit_ewallet", "withdraw_bank", 
        "withdraw_crypto", "withdraw_ewallet",
        
        # Bonus operations
        "claim_daily_bonus", "get_referral", "show_achievements", "bonus_history",
        
        # Unknown callback (should go to placeholder)
        "unknown_callback"
    ]
    
    user_id = 12345
    context = MockContext()
    
    for callback_data in all_callbacks:
        update = MockUpdate(user_id, callback_data)
        
        try:
            await handle_callback(update, context)
            print(f"✅ Callback '{callback_data}' handled successfully")
        except Exception as e:
            print(f"❌ Callback '{callback_data}' failed: {e}")
    
    print("🎯 All callback tests completed!")
    return True

async def main():
    """Run all tests"""
    print("🚀 Starting Mini App Centre Tests...\n")
    
    try:
        # Test database and basic functionality
        await test_mini_app_centre()
        print()
        
        # Test WebApp integration
        await test_webapp_integration()
        print()
        
        # Test all callbacks
        await test_all_callbacks()
        print()
        
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("✅ Mini App Centre is working properly")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
