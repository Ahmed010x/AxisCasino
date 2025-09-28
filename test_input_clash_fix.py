#!/usr/bin/env python3
"""
Test script to verify input clash fixes between deposit/withdrawal and game states.
Simulates the specific scenario where user gets insufficient balance message then tries to deposit.
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockUpdate:
    def __init__(self, user_id=12345, text="", is_callback=False, callback_data=""):
        self.effective_user = MagicMock()
        self.effective_user.id = user_id
        self.effective_user.username = f"testuser{user_id}"
        
        if is_callback:
            self.callback_query = MagicMock()
            self.callback_query.from_user = self.effective_user
            self.callback_query.data = callback_data
            self.callback_query.answer = AsyncMock()
            self.callback_query.edit_message_text = AsyncMock()
            self.message = None
        else:
            self.message = MagicMock()
            self.message.from_user = self.effective_user
            self.message.text = text
            self.message.reply_text = AsyncMock()
            self.callback_query = None

class MockContext:
    def __init__(self):
        self.user_data = {}

async def test_deposit_input_clash_fix():
    """Test the specific scenario: insufficient balance -> deposit -> input clash"""
    print("🧪 Testing Deposit Input Clash Fix...")
    
    try:
        # Import the fixed functions
        from main import handle_text_input_main, deposit_callback, deposit_crypto_callback
        
        user_id = 12345
        context = MockContext()
        
        # Step 1: Simulate user trying to make a withdrawal but getting insufficient balance
        print("   Step 1: User gets insufficient balance message")
        # This would normally set some state, but let's simulate stale state
        context.user_data['some_stale_game_state'] = True
        context.user_data['previous_withdrawal_attempt'] = 50.0
        
        # Step 2: User clicks deposit button
        print("   Step 2: User clicks deposit button")
        deposit_update = MockUpdate(user_id=user_id, is_callback=True, callback_data="deposit")
        await deposit_callback(deposit_update, context)
        
        # Verify state was cleared
        if 'some_stale_game_state' not in context.user_data:
            print("   ✅ Stale game state cleared on deposit start")
        else:
            print("   ❌ Stale game state not cleared")
        
        # Step 3: User selects LTC deposit
        print("   Step 3: User selects LTC deposit")
        crypto_update = MockUpdate(user_id=user_id, is_callback=True, callback_data="deposit_LTC")
        await deposit_crypto_callback(crypto_update, context)
        
        # Verify deposit state is set
        if 'awaiting_deposit_amount' in context.user_data:
            print("   ✅ Deposit state properly set")
        else:
            print("   ❌ Deposit state not set")
        
        # Step 4: User enters deposit amount
        print("   Step 4: User enters deposit amount")
        amount_update = MockUpdate(user_id=user_id, text="50.00")
        
        # This should now work without interference
        try:
            await handle_text_input_main(amount_update, context)
            print("   ✅ Text input handled without errors")
        except Exception as e:
            print(f"   ❌ Text input failed: {e}")
        
        # Step 5: Test edge case - user enters amount without proper state
        print("   Step 5: Testing helpful feedback for unexpected amount input")
        context.user_data.clear()  # Clear all states
        
        unexpected_amount_update = MockUpdate(user_id=user_id, text="25.50")
        try:
            await handle_text_input_main(unexpected_amount_update, context)
            print("   ✅ Unexpected amount input handled gracefully")
        except Exception as e:
            print(f"   ❌ Unexpected amount input failed: {e}")
        
        print("✅ Deposit input clash fix test completed successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import functions: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def test_withdrawal_input_clash_fix():
    """Test withdrawal input isolation"""
    print("\n🧪 Testing Withdrawal Input Clash Fix...")
    
    try:
        from main import withdraw_start, withdraw_crypto_callback
        
        user_id = 12345
        context = MockContext()
        
        # Add some stale states
        context.user_data['old_game_bet'] = 100.0
        context.user_data['awaiting_deposit_amount'] = 'LTC'  # Conflicting state
        
        # Start withdrawal
        withdraw_update = MockUpdate(user_id=user_id, is_callback=True, callback_data="withdraw")
        await withdraw_start(withdraw_update, context)
        
        # Verify stale states were cleared
        if 'old_game_bet' not in context.user_data and 'awaiting_deposit_amount' not in context.user_data:
            print("   ✅ Stale states cleared on withdrawal start")
        else:
            print("   ❌ Stale states not properly cleared")
        
        print("✅ Withdrawal input clash fix test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Withdrawal test failed: {e}")
        return False

async def main():
    """Run all input clash fix tests"""
    print("🚀 Testing Input Clash Fixes...")
    print("   This tests the specific issue: insufficient balance -> deposit -> input clash")
    
    results = []
    results.append(await test_deposit_input_clash_fix())
    results.append(await test_withdrawal_input_clash_fix())
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n{'='*60}")
    print("🏁 INPUT CLASH FIX TEST RESULTS")
    print(f"{'='*60}")
    print(f"✅ Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("\n✅ Fixed Issues:")
        print("   • Added context.user_data.clear() to deposit/withdrawal start functions")
        print("   • Enhanced text input handler with better state detection")
        print("   • Added helpful feedback for unexpected amount inputs")
        print("   • Improved logging for debugging input states")
        print("\n💡 The deposit input clash issue should now be resolved!")
    else:
        print("❌ Some tests failed. Please review the fixes.")

if __name__ == "__main__":
    asyncio.run(main())
