#!/usr/bin/env python3
"""Test the bot's deposit functionality directly"""

import asyncio
import sys
import os

# Add the current directory to the path so we can import from main.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment like main.py does
load_dotenv()
load_dotenv("env.litecoin")

# Import the function from main.py
from main import create_crypto_payment

async def test_deposit():
    """Test creating a deposit payment"""
    print("🧪 Testing casino deposit payment creation...")
    
    # Test creating a $5 USD deposit (converted to USDT)
    result = await create_crypto_payment('USDT', 5.0, 12345)
    
    print(f"✅ Result: {result}")
    
    if result.get('ok'):
        payment_data = result['result']
        print(f"💰 Payment ID: {payment_data.get('payment_id')}")
        print(f"🔗 Payment URL: {payment_data.get('payment_url')}")
        print(f"📱 Mini App URL: {payment_data.get('mini_app_url')}")
        print(f"🌐 Web App URL: {payment_data.get('web_app_url')}")
    else:
        print(f"❌ Error: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_deposit())
