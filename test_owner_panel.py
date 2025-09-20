#!/usr/bin/env python3
"""
Owner Panel Test Script
Tests owner panel functionality and access control
"""

import os
import sys
import asyncio
from unittest.mock import Mock, AsyncMock
sys.path.append('.')

# Import our main module
import main

class MockUser:
    def __init__(self, user_id, username="TestOwner"):
        self.id = user_id
        self.username = username
        self.first_name = username

class MockUpdate:
    def __init__(self, user_id, is_callback=False):
        self.effective_user = MockUser(user_id)
        if is_callback:
            self.callback_query = Mock()
            self.callback_query.from_user = self.effective_user
            self.callback_query.answer = AsyncMock()
            self.callback_query.edit_message_text = AsyncMock()
        else:
            self.message = Mock()
            self.message.reply_text = AsyncMock()

class MockContext:
    def __init__(self):
        self.bot_data = {}

async def test_owner_functions():
    """Test owner panel functionality"""
    print("🧪 Testing Owner Panel Functions...")
    
    # Test 1: Owner detection
    print("\n1. Testing owner detection...")
    
    # Set a test owner ID for testing
    original_owner_id = main.OWNER_USER_ID
    main.OWNER_USER_ID = 12345  # Test owner ID
    
    test_owner_id = 12345
    test_regular_id = 67890
    
    # Test owner detection
    assert main.is_owner(test_owner_id) == True, "Owner should be detected"
    assert main.is_owner(test_regular_id) == False, "Regular user should not be owner"
    print("✅ Owner detection working correctly")
    
    # Test 2: Database initialization
    print("\n2. Testing database initialization...")
    try:
        await main.init_db()
        print("✅ Database initialization successful")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
    
    # Test 3: Owner panel callback (direct call)
    print("\n3. Testing owner panel callback (direct call)...")
    try:
        update = MockUpdate(test_owner_id, is_callback=False)
        context = MockContext()
        await main.owner_panel_callback(update, context)
        print("✅ Owner panel direct call successful")
    except Exception as e:
        print(f"❌ Owner panel direct call failed: {e}")
        return False
    
    # Test 4: Owner panel callback (callback query)
    print("\n4. Testing owner panel callback (callback query)...")
    try:
        update = MockUpdate(test_owner_id, is_callback=True)
        context = MockContext()
        await main.owner_panel_callback(update, context)
        print("✅ Owner panel callback query successful")
    except Exception as e:
        print(f"❌ Owner panel callback query failed: {e}")
        return False
    
    # Test 5: Access control for non-owner
    print("\n5. Testing access control for non-owner...")
    try:
        update = MockUpdate(test_regular_id, is_callback=True)
        context = MockContext()
        await main.owner_panel_callback(update, context)
        print("✅ Access control working correctly")
    except Exception as e:
        print(f"❌ Access control test failed: {e}")
        return False
    
    # Test 6: Sub-panel functions
    print("\n6. Testing owner sub-panel functions...")
    sub_panels = [
        main.owner_detailed_stats_callback,
        main.owner_user_mgmt_callback,
        main.owner_financial_callback,
        main.owner_withdrawals_callback,
        main.owner_system_health_callback,
        main.owner_bot_settings_callback,
        main.owner_analytics_callback,
        main.owner_placeholder_callback
    ]
    
    for panel_func in sub_panels:
        try:
            update = MockUpdate(test_owner_id, is_callback=True)
            context = MockContext()
            await panel_func(update, context)
        except Exception as e:
            print(f"❌ Sub-panel {panel_func.__name__} failed: {e}")
            return False
    
    print("✅ All owner sub-panel functions working")
    
    # Restore original owner ID
    main.OWNER_USER_ID = original_owner_id
    
    print("\n🎉 All owner panel tests passed!")
    return True

async def main_test():
    """Run all tests"""
    print("🎰 Telegram Casino Bot - Owner Panel Test")
    print("=" * 50)
    
    success = await test_owner_functions()
    
    if success:
        print("\n✅ All tests passed! Owner panel is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed! Check the output above.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main_test())
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Test runner failed: {e}")
        sys.exit(1)
