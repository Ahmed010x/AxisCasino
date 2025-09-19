#!/usr/bin/env python3
"""
Test script for the enhanced keep-alive server endpoints
"""

import requests
import json
import time
from datetime import datetime

def test_endpoint(url, endpoint_name):
    """Test a single endpoint"""
    try:
        print(f"🔍 Testing {endpoint_name}...")
        response = requests.get(url, timeout=10)
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ {endpoint_name} - OK")
                print(f"   📄 Response: {json.dumps(data, indent=2)}")
                return True
            except json.JSONDecodeError:
                print(f"   ⚠️ {endpoint_name} - Invalid JSON response")
                print(f"   📄 Raw response: {response.text}")
                return False
        else:
            print(f"   ❌ {endpoint_name} - Failed")
            print(f"   📄 Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ {endpoint_name} - Connection Error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ {endpoint_name} - Unexpected Error: {e}")
        return False

def main():
    """Test all keep-alive endpoints"""
    print("🚀 Testing Enhanced Keep-Alive Server Endpoints")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Configuration
    base_url = "http://localhost:8080"  # Default port
    
    endpoints = [
        ("/", "Root Endpoint"),
        ("/health", "Health Check"),
        ("/status", "Status Endpoint"),
        ("/metrics", "Metrics Endpoint"),
        ("/ping", "Ping Endpoint"),
        ("/nonexistent", "404 Test (Expected to fail)")
    ]
    
    results = []
    
    print("📊 Testing Endpoints:")
    print("-" * 40)
    
    for endpoint, name in endpoints:
        url = f"{base_url}{endpoint}"
        success = test_endpoint(url, name)
        results.append((name, success))
        print()
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    print("📋 TEST SUMMARY:")
    print("-" * 40)
    
    passed = sum(1 for _, success in results if success)
    total = len(results) - 1  # Exclude the 404 test from success count
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        if name == "404 Test (Expected to fail)":
            status = "✅ EXPECTED" if not success else "❌ UNEXPECTED"
        print(f"   {status} - {name}")
    
    print()
    print(f"🎯 Results: {passed}/{total} endpoints working correctly")
    
    if passed == total:
        print("🎉 All keep-alive endpoints are working perfectly!")
    else:
        print("⚠️ Some endpoints may need attention.")
    
    print()
    print("💡 Usage Notes:")
    print("   • The keep-alive server should start automatically with the bot")
    print("   • Use these endpoints for health monitoring and deployment checks")
    print("   • For production, access via your deployment URL instead of localhost")

if __name__ == "__main__":
    main()
