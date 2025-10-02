#!/usr/bin/env python3
"""
Test the actual deposit callback flow
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# Add current directory to path
sys.path.insert(0, os.getcwd())

class MockUpdate:
    def __init__(self):
        self.callback_query = MockCallbackQuery()
        self.message = MockMessage()
        self.effective_user = MockUser()

class MockCallbackQuery:
    def __init__(self):
        self.data = "deposit_LTC"
        self.from_user = MockUser()
    
    async def answer(self):
        pass
    
    async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
        print(f"📝 Bot would send message:\n{text}\n")

class MockMessage:
    def __init__(self):
        self.text = "50"  # Simulating user typing "50"
        self.from_user = MockUser()
    
    async def reply_text(self, text, reply_markup=None, parse_mode=None):
        print(f"📝 Bot would reply:\n{text}\n")

class MockUser:
    def __init__(self):
        self.id = 12345
        self.username = "test_user"
        self.first_name = "Test"

class MockContext:
    def __init__(self):
        self.user_data = {}

async def test_deposit_callback_flow():
    """Test the full deposit callback flow"""
    print("🔍 Testing deposit callback flow...")
    
    try:
        # Import main module
        import main
        
        # Initialize database
        await main.init_db()
        
        # Create test user
        test_user_id = 12345
        user = await main.create_user(test_user_id, "test_user")
        print(f"✅ Test user created with balance: ${user['balance']:.2f}")
        
        # Enable demo mode
        original_demo = main.DEMO_MODE
        main.DEMO_MODE = True
        print("✅ Demo mode enabled")
        
        # Test 1: deposit_crypto_callback
        print("\n--- Test 1: deposit_crypto_callback ---")
        update = MockUpdate()
        context = MockContext()
        
        await main.deposit_crypto_callback(update, context)
        print(f"✅ Context after deposit_crypto_callback: {context.user_data}")
        
        # Test 2: handle_deposit_amount_input
        print("\n--- Test 2: handle_deposit_amount_input ---")
        update.message.text = "50"  # User types $50
        
        await main.handle_deposit_amount_input(update, context)
        print(f"✅ Context after amount input: {context.user_data}")
        
        # Check user balance after deposit
        user = await main.get_user(test_user_id)
        print(f"💰 User balance after deposit: ${user['balance']:.2f}")
        
        # Restore demo mode
        main.DEMO_MODE = original_demo
        
        print("\n🎉 Deposit callback flow test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_deposit_callback_flow())
    sys.exit(0 if result else 1)
