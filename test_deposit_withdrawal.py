#!/usr/bin/env python3
"""
Test script for deposit and withdrawal functionality.
This tests the core logic without requiring a running bot.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add current directory to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Set demo mode for testing
os.environ["DEMO_MODE"] = "true"

# Import main module after setting environment
import main

async def test_crypto_rates():
    """Test cryptocurrency rate fetching."""
    print("🧪 Testing crypto rate fetching...")
    
    # Test rate fetching for different assets
    assets = ['BTC', 'LTC', 'ETH', 'TON', 'USDT']
    
    for asset in assets:
        try:
            rate = await main.get_crypto_usd_rate(asset)
            print(f"  • {asset}: ${rate:.4f} per unit")
        except Exception as e:
            print(f"  • {asset}: Error - {e}")
    
    print("✅ Crypto rate test completed\n")

async def test_deposit_helpers():
    """Test deposit helper functions."""
    print("🧪 Testing deposit helper functions...")
    
    # Test invoice creation
    try:
        invoice = await main.create_crypto_invoice("LTC", 0.01, 12345)
        print(f"  • Invoice creation: {'✅ Success' if invoice.get('ok') else '❌ Failed'}")
        if invoice.get('ok'):
            print(f"    - Invoice ID: {invoice['result'].get('invoice_id', 'N/A')}")
    except Exception as e:
        print(f"  • Invoice creation: ❌ Error - {e}")
    
    # Test formatting functions
    try:
        usd_format = await main.format_usd(123.45)
        crypto_format = await main.format_crypto_usd(0.01, "LTC")
        print(f"  • USD formatting: {usd_format}")
        print(f"  • Crypto formatting: {crypto_format}")
        print("  • Formatting: ✅ Success")
    except Exception as e:
        print(f"  • Formatting: ❌ Error - {e}")
    
    print("✅ Deposit helper test completed\n")

async def test_withdrawal_helpers():
    """Test withdrawal helper functions."""
    print("🧪 Testing withdrawal helper functions...")
    
    # Test withdrawal limits check
    try:
        limits = await main.check_withdrawal_limits(12345, 100.0)
        print(f"  • Withdrawal limits check: {'✅ Success' if limits else '❌ Failed'}")
        if limits:
            print(f"    - Can withdraw: {limits.get('can_withdraw', False)}")
    except Exception as e:
        print(f"  • Withdrawal limits: ❌ Error - {e}")
    
    # Test withdrawal fee calculation
    try:
        fee = main.calculate_withdrawal_fee(100.0)
        print(f"  • Withdrawal fee calculation: ${fee:.2f}")
        print("  • Fee calculation: ✅ Success")
    except Exception as e:
        print(f"  • Fee calculation: ❌ Error - {e}")
    
    # Test address validation
    try:
        test_addresses = {
            'LTC': 'LTC1qw4f8c6f2z5k8j9h6g5f4d3s2a1z0x9c8v7b6n5m4',
            'BTC': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
            'ETH': '0x742d35Cc6634C0532925a3b8D6DbE19b79E0'
        }
        
        for asset, address in test_addresses.items():
            is_valid = main.validate_crypto_address(address, asset)
            print(f"  • {asset} address validation: {'✅ Valid' if is_valid else '❌ Invalid'}")
    except Exception as e:
        print(f"  • Address validation: ❌ Error - {e}")
    
    print("✅ Withdrawal helper test completed\n")

async def test_database_operations():
    """Test database operations for deposit and withdrawal."""
    print("🧪 Testing database operations...")
    
    try:
        # Initialize database
        await main.init_db()
        print("  • Database initialization: ✅ Success")
        
        # Test user creation and retrieval
        test_user_id = 999999
        await main.create_user(test_user_id, "test_user")
        user = await main.get_user(test_user_id)
        print(f"  • User operations: {'✅ Success' if user else '❌ Failed'}")
        
        # Test balance operations
        if user:
            initial_balance = user['balance']
            success = await main.update_balance(test_user_id, 50.0)
            updated_user = await main.get_user(test_user_id)
            final_balance = updated_user['balance'] if updated_user else 0
            
            print(f"  • Balance update: {'✅ Success' if success and final_balance > initial_balance else '❌ Failed'}")
            print(f"    - Initial: ${initial_balance:.2f}, Final: ${final_balance:.2f}")
            
            # Test withdrawal logging
            withdrawal_id = await main.log_withdrawal(test_user_id, "LTC", 25.0, "test_address", 1.0, 24.0)
            print(f"  • Withdrawal logging: {'✅ Success' if withdrawal_id > 0 else '❌ Failed'}")
            
            if withdrawal_id > 0:
                # Test withdrawal status update
                status_updated = await main.update_withdrawal_status(withdrawal_id, "completed", "test_hash")
                print(f"  • Withdrawal status update: {'✅ Success' if status_updated else '❌ Failed'}")
        
    except Exception as e:
        print(f"  • Database operations: ❌ Error - {e}")
    
    print("✅ Database test completed\n")

async def main_test():
    """Run all tests."""
    print("🚀 Starting Deposit/Withdrawal System Tests\n")
    print("=" * 50)
    
    await test_crypto_rates()
    await test_deposit_helpers() 
    await test_withdrawal_helpers()
    await test_database_operations()
    
    print("=" * 50)
    print("🎉 All tests completed!")
    print("\n💡 If all tests passed, your deposit and withdrawal system is ready!")
    print("   You can now run the bot and test the actual user flows.")

if __name__ == "__main__":
    asyncio.run(main_test())
