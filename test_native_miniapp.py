#!/usr/bin/env python3
"""
Test script to verify the native CryptoBot mini app integration
Tests the createPayment API and ensures proper response structure
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CRYPTOBOT_API_TOKEN = os.environ.get("CRYPTOBOT_API_TOKEN")

async def test_create_invoice():
    """Test the createInvoice API for native mini app integration"""
    
    if not CRYPTOBOT_API_TOKEN:
        print("❌ CRYPTOBOT_API_TOKEN not configured")
        return False
    
    headers = {
        'Crypto-Pay-API-Token': CRYPTOBOT_API_TOKEN,
        'Content-Type': 'application/json'
    }
    
    # Test data
    data = {
        'asset': 'LTC',
        'amount': '0.01000000',  # Small test amount
        'description': 'Test Casino deposit - $1.00 USD',
        'hidden_message': '12345',  # Test user ID
        'expires_in': 3600,
        'allow_comments': False,
        'allow_anonymous': False,
    }
    
    print("🧪 Testing CryptoBot createInvoice API...")
    print(f"📤 Request data: {json.dumps(data, indent=2)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post('https://pay.crypt.bot/api/createInvoice', 
                                  headers=headers, json=data) as response:
                
                print(f"📊 Response status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"📥 Response: {json.dumps(result, indent=2)}")
                    
                    if result.get('ok'):
                        invoice_data = result.get('result', {})
                        invoice_id = invoice_data.get('invoice_id')
                        mini_app_url = invoice_data.get('mini_app_invoice_url')
                        web_app_url = invoice_data.get('web_app_invoice_url')
                        bot_url = invoice_data.get('bot_invoice_url')
                        
                        print(f"\n✅ Invoice created successfully!")
                        print(f"🆔 Invoice ID: {invoice_id}")
                        print(f"🔗 Mini App URL: {mini_app_url}")
                        print(f"🔗 Web App URL: {web_app_url}")
                        print(f"🔗 Bot URL: {bot_url}")
                        
                        # Verify we have the essential fields for native mini app
                        native_url = mini_app_url or web_app_url
                        if native_url and invoice_id:
                            print(f"\n🎉 NATIVE MINI APP INTEGRATION SUCCESS!")
                            print(f"✅ Native URL present: {native_url[:50]}...")
                            print(f"✅ Invoice ID present: {invoice_id}")
                            print(f"✅ Ready for native Telegram mini app experience!")
                            return True
                        else:
                            print(f"\n❌ Missing required fields for mini app integration")
                            print(f"Available URLs: mini_app={bool(mini_app_url)}, web_app={bool(web_app_url)}, bot={bool(bot_url)}")
                            return False
                    else:
                        error = result.get('error', {})
                        print(f"\n❌ API returned error: {error}")
                        return False
                else:
                    error_text = await response.text()
                    print(f"❌ HTTP error {response.status}: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

async def test_exchange_rates():
    """Test exchange rates API to verify LTC rate availability"""
    
    if not CRYPTOBOT_API_TOKEN:
        print("❌ CRYPTOBOT_API_TOKEN not configured")
        return False
    
    headers = {
        'Crypto-Pay-API-Token': CRYPTOBOT_API_TOKEN
    }
    
    print("\n🧪 Testing CryptoBot exchange rates API...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://pay.crypt.bot/api/getExchangeRates', 
                                 headers=headers) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    if result.get('ok'):
                        rates = result.get('result', [])
                        ltc_rate = None
                        
                        for rate in rates:
                            if rate.get('source') == 'LTC' and rate.get('target') == 'USD':
                                ltc_rate = float(rate.get('rate', 0))
                                break
                        
                        if ltc_rate:
                            print(f"✅ LTC/USD rate available: ${ltc_rate:.2f}")
                            return True
                        else:
                            print(f"❌ LTC/USD rate not found")
                            return False
                    else:
                        print(f"❌ Rates API error: {result}")
                        return False
                else:
                    error_text = await response.text()
                    print(f"❌ Rates API HTTP error {response.status}: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Rates test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 NATIVE CRYPTOBOT MINI APP TEST SUITE")
    print("=" * 50)
    
    # Test 1: Exchange rates
    rates_ok = await test_exchange_rates()
    
    # Test 2: Invoice creation
    invoice_ok = await test_create_invoice()
    
    print("\n" + "=" * 50)
    print("📋 TEST RESULTS:")
    print(f"✅ Exchange Rates API: {'PASS' if rates_ok else 'FAIL'}")
    print(f"✅ Invoice Creation API: {'PASS' if invoice_ok else 'FAIL'}")
    
    if rates_ok and invoice_ok:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"🔥 Native CryptoBot mini app integration is ready!")
        print(f"💡 Users will now get the native payment experience within Telegram!")
    else:
        print(f"\n❌ Some tests failed. Check your CryptoBot API configuration.")
    
    return rates_ok and invoice_ok

if __name__ == "__main__":
    asyncio.run(main())
