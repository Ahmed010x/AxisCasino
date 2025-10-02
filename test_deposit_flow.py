#!/usr/bin/env python3
"""
Test deposit functionality to ensure it's working properly
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

async def test_deposit_flow():
    """Test the deposit flow functions"""
    print("🔍 Testing deposit functionality...")
    
    try:
        # Import main module
        import main
        
        # Initialize database
        await main.init_db()
        print("✅ Database initialized")
        
        # Test user creation
        test_user_id = 12345
        user = await main.create_user(test_user_id, "test_user")
        print(f"✅ Test user created: {user}")
        
        # Test crypto rate fetch (this might fail if no API token)
        rate = await main.get_crypto_usd_rate("LTC")
        print(f"📈 LTC rate: ${rate:.4f}" if rate > 0 else "⚠️  LTC rate: Unable to fetch (expected with test token)")
        
        # Test demo mode deposit
        original_demo = main.DEMO_MODE
        main.DEMO_MODE = True
        
        success = await main.update_balance(test_user_id, 100.0)
        print(f"✅ Demo deposit test: {'Success' if success else 'Failed'}")
        
        # Check balance
        user = await main.get_user(test_user_id)
        print(f"💰 User balance after deposit: ${user['balance']:.2f}")
        
        # Restore demo mode
        main.DEMO_MODE = original_demo
        
        print("\n🎉 Deposit functionality test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_deposit_flow())
    sys.exit(0 if result else 1)
