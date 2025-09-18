#!/usr/bin/env python3
"""
Test script to check the invoice system functionality
"""
import asyncio
import aiohttp
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
load_dotenv(".env.owner")

CRYPTOBOT_API_TOKEN = os.environ.get("CRYPTOBOT_API_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

async def test_create_invoice():
    """Test creating a crypto invoice"""
    if not CRYPTOBOT_API_TOKEN:
        print("❌ CRYPTOBOT_API_TOKEN not found in environment")
        return False
    
    headers = {
        'Crypto-Pay-API-Token': CRYPTOBOT_API_TOKEN,
        'Content-Type': 'application/json'
    }
    
    data = {
        'asset': 'LTC',
        'amount': '0.01',
        'description': 'Test Casino deposit',
        'hidden_message': '12345',
        'paid_btn_name': 'callback',
        'paid_btn_url': f'{RENDER_EXTERNAL_URL}/payment_success' if RENDER_EXTERNAL_URL else 'https://example.com/success'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post('https://pay.crypt.bot/api/createInvoice', 
                                  headers=headers, json=data) as response:
                result = await response.json()
                print("✅ Invoice creation test result:")
                print(f"   Status: {'SUCCESS' if result.get('ok') else 'FAILED'}")
                
                if result.get('ok'):
                    invoice_data = result.get('result', {})
                    print(f"   Invoice ID: {invoice_data.get('invoice_id')}")
                    print(f"   Pay URL: {invoice_data.get('pay_url')}")
                    print(f"   Amount: {invoice_data.get('amount')} {invoice_data.get('asset')}")
                    return True
                else:
                    error = result.get('error', {})
                    print(f"   Error: {error.get('name', 'Unknown')} - {error.get('code', 'N/A')}")
                    return False
                    
    except Exception as e:
        print(f"❌ Exception during invoice test: {e}")
        return False

async def main():
    print("🧪 Testing Casino Bot Invoice System")
    print("=" * 50)
    
    # Check environment variables
    print("\n📋 Environment Check:")
    print(f"   CRYPTOBOT_API_TOKEN: {'✅ SET' if CRYPTOBOT_API_TOKEN else '❌ MISSING'}")
    print(f"   RENDER_EXTERNAL_URL: {'✅ SET' if RENDER_EXTERNAL_URL else '❌ MISSING'}")
    
    if not CRYPTOBOT_API_TOKEN:
        print("\n❌ Cannot test invoice creation without CRYPTOBOT_API_TOKEN")
        return
    
    # Test invoice creation
    print("\n🧾 Testing Invoice Creation:")
    success = await test_create_invoice()
    
    print(f"\n📊 Test Results:")
    print(f"   Invoice System: {'✅ WORKING' if success else '❌ FAILED'}")
    
    if success:
        print("\n✅ Invoice system is ready for deposits!")
    else:
        print("\n❌ Invoice system needs configuration!")

if __name__ == "__main__":
    asyncio.run(main())
