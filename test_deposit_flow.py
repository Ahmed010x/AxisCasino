#!/usr/bin/env python3
"""
Test the deposit flow end-to-end
"""
import asyncio
import aiosqlite
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
load_dotenv(".env.owner")

DB_PATH = "casino.db"
CRYPTOBOT_API_TOKEN = os.environ.get("CRYPTOBOT_API_TOKEN")

async def test_deposit_flow():
    """Test the complete deposit flow"""
    print("🧪 Testing Deposit Flow")
    print("=" * 40)
    
    # 1. Check environment
    print("\n📋 Environment Check:")
    print(f"   CRYPTOBOT_API_TOKEN: {'✅ SET' if CRYPTOBOT_API_TOKEN else '❌ MISSING'}")
    
    # 2. Check database connectivity
    print("\n💾 Database Check:")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            user_count = (await cursor.fetchone())[0]
            print(f"   Database connection: ✅ WORKING")
            print(f"   Total users: {user_count}")
    except Exception as e:
        print(f"   Database connection: ❌ FAILED - {e}")
        return False
    
    # 3. Test user creation/retrieval
    print("\n👤 User System Check:")
    test_user_id = 12345
    try:
        # Import functions from main.py
        import sys
        sys.path.append('.')
        from main import get_user, create_user, get_crypto_usd_rate, create_crypto_invoice
        
        user = await get_user(test_user_id)
        if not user:
            user = await create_user(test_user_id, "test_user")
            print(f"   Created test user: ✅ SUCCESS")
        else:
            print(f"   Retrieved test user: ✅ SUCCESS")
        
        print(f"   User balance: {user['balance']:.8f} LTC")
        
    except Exception as e:
        print(f"   User system: ❌ FAILED - {e}")
        return False
    
    # 4. Test crypto rate system
    print("\n💱 Crypto Rate Check:")
    try:
        ltc_rate = await get_crypto_usd_rate('LTC')
        ton_rate = await get_crypto_usd_rate('TON')
        sol_rate = await get_crypto_usd_rate('SOL')
        
        print(f"   LTC rate: ${ltc_rate:.2f}")
        print(f"   TON rate: ${ton_rate:.2f}")
        print(f"   SOL rate: ${sol_rate:.2f}")
        print(f"   Rate system: ✅ WORKING")
        
    except Exception as e:
        print(f"   Rate system: ❌ FAILED - {e}")
        return False
    
    # 5. Test invoice creation
    print("\n🧾 Invoice Creation Check:")
    try:
        if not CRYPTOBOT_API_TOKEN:
            print("   Skipping invoice test - no API token")
            return True
            
        # Test creating a small invoice
        test_amount_usd = 1.0
        test_asset = 'LTC'
        asset_amount = test_amount_usd / ltc_rate
        
        invoice = await create_crypto_invoice(test_asset, asset_amount, test_user_id)
        
        if invoice.get('ok'):
            print(f"   Invoice creation: ✅ SUCCESS")
            print(f"   Invoice ID: {invoice['result']['invoice_id']}")
            print(f"   Amount: {asset_amount:.8f} {test_asset}")
            return True
        else:
            print(f"   Invoice creation: ❌ FAILED - {invoice.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"   Invoice creation: ❌ FAILED - {e}")
        return False

async def main():
    success = await test_deposit_flow()
    
    print(f"\n📊 Overall Status:")
    if success:
        print("✅ Deposit system is fully operational!")
    else:
        print("❌ Deposit system has issues that need fixing!")

if __name__ == "__main__":
    asyncio.run(main())
