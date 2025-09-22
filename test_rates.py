#!/usr/bin/env python3
"""
Test script to verify CryptoBot API rate fetching
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('env.litecoin')

async def test_cryptobot_rates():
    """Test the CryptoBot API rate fetching"""
    url = "https://pay.crypt.bot/api/getExchangeRates"
    token = os.environ.get("CRYPTOBOT_API_TOKEN")
    
    headers = {}
    if token:
        headers["Crypto-Pay-API-Token"] = token
        print(f"🔑 Using API token: {token[:10]}...")
    else:
        print("⚠️  No API token found, trying without authentication")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as resp:
                print(f"📡 Response status: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("ok"):
                        rates = data.get("result", [])
                        
                        print("✅ CryptoBot API successful!")
                        print("📊 Available rates:")
                        
                        for asset in ['LTC', 'TON', 'SOL', 'USDT']:
                            for rate in rates:
                                if rate.get("source") == asset and rate.get("target") == "USD":
                                    price = float(rate.get("rate", 0))
                                    print(f"   {asset}/USD: ${price:.6f}")
                                    break
                            else:
                                print(f"   {asset}/USD: Not found")
                                
                        print(f"\n📋 Total rates available: {len(rates)}")
                    else:
                        error_info = data.get("error", {})
                        print(f"❌ API returned error: {error_info}")
                    
                else:
                    text = await resp.text()
                    print(f"❌ API Error: HTTP {resp.status}")
                    print(f"Response: {text}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_cryptobot_rates())
