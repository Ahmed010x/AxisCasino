#!/usr/bin/env python3
"""Test CryptoBot API connection and endpoint"""

import aiohttp
import asyncio
import json
import os
from dotenv import load_dotenv

# Load environment like main.py does
load_dotenv()
load_dotenv("env.litecoin")

CRYPTOBOT_API_TOKEN = os.getenv('CRYPTOBOT_API_TOKEN')

async def test_cryptobot_api():
    """Test CryptoBot API endpoints"""
    
    if not CRYPTOBOT_API_TOKEN:
        print("❌ No CryptoBot API token configured")
        return
    
    headers = {
        'Crypto-Pay-API-Token': CRYPTOBOT_API_TOKEN,
        'Content-Type': 'application/json'
    }
    
    print(f"🔑 Using API token: {CRYPTOBOT_API_TOKEN[:20]}...")
    
    # Test 1: Get app info to verify token
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            print("\n📊 Testing getMe endpoint...")
            async with session.get('https://pay.crypt.bot/api/getMe', headers=headers) as response:
                result = await response.json()
                print(f"Status: {response.status}")
                print(f"Response: {json.dumps(result, indent=2)}")
                
            print("\n💰 Testing createInvoice endpoint...")
            data = {
                'asset': 'USDT',
                'amount': '5.0',
                'description': 'Test casino deposit',
                'hidden_message': '12345',  # Test user ID
                'expires_in': 3600,
                'allow_comments': False,
                'allow_anonymous': False
            }
            
            async with session.post('https://pay.crypt.bot/api/createInvoice', 
                                  headers=headers, json=data) as response:
                result = await response.json()
                print(f"Status: {response.status}")
                print(f"Response: {json.dumps(result, indent=2)}")
                
                if result.get('ok') and 'result' in result:
                    invoice = result['result']
                    print(f"\n✅ Invoice created successfully!")
                    print(f"Invoice ID: {invoice.get('invoice_id')}")
                    print(f"Pay URL: {invoice.get('pay_url')}")
                    print(f"Web App URL: {invoice.get('web_app_invoice_url', 'Not available')}")
                    print(f"Mini App URL: {invoice.get('mini_app_invoice_url', 'Not available')}")
                else:
                    print(f"❌ Invoice creation failed: {result}")
    
    except Exception as e:
        print(f"❌ Error testing CryptoBot API: {e}")

if __name__ == "__main__":
    asyncio.run(test_cryptobot_api())
