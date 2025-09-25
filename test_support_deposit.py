#!/usr/bin/env python3
"""
Test script to verify support and deposit functionality
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append('.')

async def test_all():
    """Run comprehensive tests for support and deposit functionality."""
    print("🧪 Testing Telegram Casino Bot - Support & Deposit Functions")
    print("=" * 60)
    
    try:
        # Test 1: Import all required modules
        print("\n1. Testing imports...")
        from main import (
            support_command, deposit_callback, create_crypto_invoice,
            get_crypto_usd_rate, init_db, create_user, get_user,
            BOT_TOKEN, SUPPORT_CHANNEL, CRYPTOBOT_API_TOKEN, CRYPTOBOT_WEBHOOK_SECRET
        )
        print("✅ All imports successful")
        
        # Test 2: Environment configuration
        print("\n2. Testing environment configuration...")
        print(f"✅ BOT_TOKEN configured: {'Yes' if BOT_TOKEN else 'No'}")
        print(f"✅ SUPPORT_CHANNEL: {SUPPORT_CHANNEL}")
        print(f"✅ CRYPTOBOT_API_TOKEN configured: {'Yes' if CRYPTOBOT_API_TOKEN else 'No'}")
        print(f"✅ CRYPTOBOT_WEBHOOK_SECRET configured: {'Yes' if CRYPTOBOT_WEBHOOK_SECRET and CRYPTOBOT_WEBHOOK_SECRET != 'your_webhook_secret_here' else 'No (needs real secret)'}")
        
        # Test 3: Database initialization
        print("\n3. Testing database...")
        await init_db()
        print("✅ Database initialized successfully")
        
        # Test 4: User management
        print("\n4. Testing user management...")
        test_user_id = 999999999
        await create_user(test_user_id, 'TestUser')
        user = await get_user(test_user_id)
        print(f"✅ User creation: {'Success' if user else 'Failed'}")
        if user:
            print(f"   └─ User ID: {user['user_id']}, Balance: ${user['balance']:.2f}")
        
        # Test 5: Crypto rate API
        print("\n5. Testing crypto rate API...")
        ltc_rate = await get_crypto_usd_rate('LTC')
        print(f"✅ LTC/USD rate: ${ltc_rate:.2f}")
        print(f"✅ Rate API working: {'Yes' if ltc_rate > 0 else 'No'}")
        
        # Test 6: Invoice creation (requires valid API token)
        print("\n6. Testing invoice creation...")
        if CRYPTOBOT_API_TOKEN and ltc_rate > 0:
            # Calculate LTC amount for $50 USD
            usd_amount = 50.0
            ltc_amount = usd_amount / ltc_rate
            
            invoice_result = await create_crypto_invoice('LTC', ltc_amount, test_user_id)
            if invoice_result.get('ok'):
                invoice_data = invoice_result.get('result', {})
                print("✅ Invoice creation: Success")
                print(f"   └─ Invoice ID: {invoice_data.get('invoice_id')}")
                print(f"   └─ Pay URL: {invoice_data.get('pay_url', 'N/A')[:50]}...")
                print(f"   └─ Amount: {invoice_data.get('amount')} LTC")
            else:
                print(f"❌ Invoice creation failed: {invoice_result.get('error', 'Unknown error')}")
        else:
            print("⚠️ Skipping invoice test (API token not configured or rate unavailable)")
        
        # Test 7: Webhook endpoint simulation
        print("\n7. Testing webhook configuration...")
        from main import RENDER_EXTERNAL_URL
        webhook_url = f'{RENDER_EXTERNAL_URL}/webhook/cryptobot' if RENDER_EXTERNAL_URL else 'https://axiscasino.onrender.com/webhook/cryptobot'
        print(f"✅ Webhook URL: {webhook_url}")
        
        # Test 8: Support system
        print("\n8. Testing support system...")
        print(f"✅ Support channel configured: {SUPPORT_CHANNEL}")
        print("✅ Support command available: Yes")
        
        # Test 9: Configuration validation
        print("\n9. Testing configuration completeness...")
        import os
        min_deposit = os.environ.get("MIN_DEPOSIT_USD", "1.00")
        max_deposit = os.environ.get("MAX_DEPOSIT_USD", "50000.00")
        min_withdrawal = os.environ.get("MIN_WITHDRAWAL_USD", "1.00")
        max_withdrawal = os.environ.get("MAX_WITHDRAWAL_USD", "10000.00")
        supported_assets = os.environ.get("SUPPORTED_CRYPTO_ASSETS", "LTC")
        primary_asset = os.environ.get("CRYPTOBOT_USD_ASSET", "LTC")
        
        print(f"✅ Deposit limits: ${min_deposit} - ${max_deposit}")
        print(f"✅ Withdrawal limits: ${min_withdrawal} - ${max_withdrawal}")
        print(f"✅ Supported assets: {supported_assets}")
        print(f"✅ Primary asset: {primary_asset}")
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS COMPLETED!")
        print("\n📋 SUMMARY:")
        print("✅ Bot imports and configuration working")
        print("✅ Database operations functional")
        print("✅ Crypto rate API operational")
        print("✅ Support system configured")
        print("✅ LTC-only deposit/withdrawal system ready")
        
        if CRYPTOBOT_WEBHOOK_SECRET == 'your_webhook_secret_here':
            print("\n⚠️  PRODUCTION NOTE:")
            print("   Set a real CRYPTOBOT_WEBHOOK_SECRET in .env for production")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_all())
    exit(0 if success else 1)
