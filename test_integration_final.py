#!/usr/bin/env python3
"""
Mini App Integration Test
Tests the integration between the Telegram bot, Flask API, and mini app
"""

import os
import time
import requests
import subprocess
import threading
from dotenv import load_dotenv

load_dotenv()

def test_flask_endpoints():
    """Test all Flask API endpoints"""
    base_url = "http://localhost:5001"
    
    print("🧪 Testing Flask API endpoints...")
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 200:
            print("✅ Health endpoint working")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False
    
    # Test user creation/retrieval
    test_user_id = 999999
    try:
        response = requests.get(f"{base_url}/api/user/{test_user_id}")
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ User endpoint working - Balance: {user_data.get('balance', 'Unknown')}")
        else:
            print(f"❌ User endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ User endpoint error: {e}")
        return False
    
    # Test balance endpoint
    try:
        response = requests.get(f"{base_url}/api/balance/{test_user_id}")
        if response.status_code == 200:
            balance_data = response.json()
            print(f"✅ Balance endpoint working - Balance: {balance_data.get('balance', 'Unknown')}")
        else:
            print(f"❌ Balance endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Balance endpoint error: {e}")
        return False
    
    # Test bet endpoint
    try:
        bet_data = {
            "telegram_id": test_user_id,
            "amount": 50,
            "game_type": "dice"
        }
        response = requests.post(f"{base_url}/api/bet", json=bet_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Bet endpoint working - Result: {result.get('result', 'Unknown')}")
        else:
            print(f"❌ Bet endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bet endpoint error: {e}")
        return False
    
    return True

def test_mini_app_access():
    """Test mini app accessibility"""
    base_url = "http://localhost:5001"
    
    print("\n🎮 Testing Mini App access...")
    
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            print("✅ Mini app accessible")
            
            # Check if it contains expected elements
            content = response.text.lower()
            if "stake casino" in content:
                print("✅ Mini app contains expected content")
            else:
                print("⚠️ Mini app content might be incomplete")
            
            return True
        else:
            print(f"❌ Mini app not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Mini app access error: {e}")
        return False

def main():
    """Run integration tests"""
    print("🎰 Stake Casino - Integration Test")
    print("="*50)
    
    # Check if Flask API is running
    try:
        response = requests.get("http://localhost:5001/api/health", timeout=2)
        if response.status_code != 200:
            print("❌ Flask API not running. Please start with: python flask_api.py")
            return 1
    except:
        print("❌ Flask API not running. Please start with: python flask_api.py")
        return 1
    
    print("✅ Flask API is running")
    
    # Run tests
    tests_passed = 0
    total_tests = 2
    
    if test_flask_endpoints():
        tests_passed += 1
    
    if test_mini_app_access():
        tests_passed += 1
    
    # Results
    print("\n" + "="*50)
    print(f"📊 TEST RESULTS: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("🎉 All integration tests passed!")
        print("\n🚀 System is ready for production!")
        print("\nNext steps:")
        print("1. Start the bot: python stake_bot_clean.py")
        print("2. Test with Telegram: /start")
        print("3. Open mini app from bot interface")
        return 0
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    exit(main())
