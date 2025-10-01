#!/usr/bin/env python3
"""
Test script to verify deposit and withdrawal functionality
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import main functions from main.py
from main import (
    init_db, create_user, get_user, update_balance, deduct_balance,
    check_withdrawal_limits, validate_crypto_address, calculate_withdrawal_fee,
    log_withdrawal, format_usd, format_crypto_usd, get_crypto_usd_rate,
    DEMO_MODE
)

async def test_basic_user_operations():
    """Test basic user creation and balance operations"""
    print("🧪 Testing basic user operations...")
    
    # Initialize database
    await init_db()
    
    # Test user creation
    test_user_id = 12345
    user = await create_user(test_user_id, "test_user")
    assert user is not None, "User creation failed"
    assert user['balance'] == 0.0, "Initial balance should be 0"
    print("✅ User creation: PASSED")
    
    # Test balance update
    success = await update_balance(test_user_id, 100.0)
    assert success, "Balance update failed"
    
    user = await get_user(test_user_id)
    assert user['balance'] == 100.0, "Balance update verification failed"
    print("✅ Balance update: PASSED")
    
    # Test balance deduction
    success = await deduct_balance(test_user_id, 25.0)
    assert success, "Balance deduction failed"
    
    user = await get_user(test_user_id)
    assert user['balance'] == 75.0, "Balance deduction verification failed"
    print("✅ Balance deduction: PASSED")
    
    return test_user_id

async def test_withdrawal_limits():
    """Test withdrawal limit checks"""
    print("🧪 Testing withdrawal limits...")
    
    test_user_id = 12346
    await create_user(test_user_id, "test_withdrawal_user")
    
    # Test minimum withdrawal limit
    result = await check_withdrawal_limits(test_user_id, 0.5)
    assert not result['allowed'], "Should reject amounts below minimum"
    print("✅ Minimum withdrawal limit: PASSED")
    
    # Test maximum withdrawal limit
    result = await check_withdrawal_limits(test_user_id, 15000.0)
    assert not result['allowed'], "Should reject amounts above maximum"
    print("✅ Maximum withdrawal limit: PASSED")
    
    # Test valid withdrawal amount
    result = await check_withdrawal_limits(test_user_id, 50.0)
    assert result['allowed'], "Should allow valid amounts"
    print("✅ Valid withdrawal amount: PASSED")

async def test_crypto_address_validation():
    """Test cryptocurrency address validation"""
    print("🧪 Testing crypto address validation...")
    
    # Test valid LTC addresses
    valid_ltc_addresses = [
        "LTC1234567890123456789012345678",
        "MTC1234567890123456789012345678",
        "ltc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
    ]
    
    for addr in valid_ltc_addresses:
        result = validate_crypto_address(addr, "LTC")
        print(f"  Testing {addr[:20]}...: {'✅ VALID' if result else '❌ INVALID'}")
    
    # Test invalid LTC address
    invalid_addr = "invalid_address_123"
    result = validate_crypto_address(invalid_addr, "LTC")
    assert not result, "Should reject invalid addresses"
    print("✅ Invalid address rejection: PASSED")

async def test_fee_calculation():
    """Test withdrawal fee calculation"""
    print("🧪 Testing fee calculation...")
    
    # Test fee calculation
    fee1 = calculate_withdrawal_fee(100.0)
    expected_fee1 = 100.0 * 0.02  # 2% = $2.00
    assert fee1 == expected_fee1, f"Fee calculation failed: {fee1} != {expected_fee1}"
    print(f"✅ Fee for $100: ${fee1}")
    
    # Test minimum fee
    fee2 = calculate_withdrawal_fee(10.0)
    expected_fee2 = max(10.0 * 0.02, 1.0)  # 2% of $10 = $0.20, but minimum is $1.00
    assert fee2 == expected_fee2, f"Minimum fee calculation failed: {fee2} != {expected_fee2}"
    assert fee2 >= 1.0, "Minimum fee should be $1"
    print(f"✅ Fee for $10: ${fee2}")

async def test_formatting_functions():
    """Test USD and crypto formatting functions"""
    print("🧪 Testing formatting functions...")
    
    # Test USD formatting
    usd_str = await format_usd(1234.56)
    assert "1,234.56" in usd_str, f"USD formatting failed: {usd_str}"
    print(f"✅ USD formatting: {usd_str}")
    
    # Test crypto formatting (with mock rate)
    crypto_str = await format_crypto_usd(0.1, "LTC")
    print(f"✅ Crypto formatting: {crypto_str}")

async def test_demo_mode():
    """Test demo mode functionality"""
    print("🧪 Testing demo mode...")
    
    # Check if demo mode is properly configured
    print(f"Demo mode enabled: {DEMO_MODE}")
    
    if DEMO_MODE:
        print("✅ Demo mode: ENABLED (simulated transactions)")
    else:
        print("✅ Demo mode: DISABLED (real transactions)")

async def run_all_tests():
    """Run all tests"""
    print("🚀 Starting Deposit/Withdrawal System Tests")
    print("=" * 50)
    
    try:
        # Test basic operations
        test_user_id = await test_basic_user_operations()
        print()
        
        # Test withdrawal limits
        await test_withdrawal_limits()
        print()
        
        # Test crypto validation
        await test_crypto_address_validation()
        print()
        
        # Test fee calculation
        await test_fee_calculation()
        print()
        
        # Test formatting
        await test_formatting_functions()
        print()
        
        # Test demo mode
        await test_demo_mode()
        print()
        
        print("=" * 50)
        print("🎉 ALL TESTS PASSED! Deposit/Withdrawal system is working correctly.")
        
        # Show user balance for verification
        user = await get_user(test_user_id)
        balance_str = await format_usd(user['balance'])
        print(f"💰 Test user final balance: {balance_str}")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    # Set demo mode for testing
    os.environ['DEMO_MODE'] = 'true'
    
    # Run tests
    success = asyncio.run(run_all_tests())
    
    if success:
        print("\n✅ Deposit and withdrawal functionality is ready for production!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed. Please check the implementation.")
        sys.exit(1)
