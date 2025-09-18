#!/usr/bin/env python3
"""
Test script for the production keep-alive server.
Tests all health check endpoints to ensure they're working correctly.
"""

import requests
import json
import time
import sys

def test_server_endpoints():
    """Test all keep-alive server endpoints."""
    base_url = "http://localhost:10000"
    
    endpoints = [
        "/",
        "/health", 
        "/status",
        "/ping",
        "/metrics"
    ]
    
    print("🧪 Testing production keep-alive server endpoints...")
    print(f"📍 Base URL: {base_url}")
    print("-" * 50)
    
    all_passed = True
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            print(f"Testing {endpoint}... ", end="")
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print("✅ PASS")
                
                # Print JSON responses for structured endpoints
                if endpoint in ["/health", "/status", "/ping", "/metrics"]:
                    try:
                        data = response.json()
                        print(f"   Response: {json.dumps(data, indent=2)}")
                    except:
                        print(f"   Response: {response.text}")
                else:
                    print(f"   Response: {response.text}")
            else:
                print(f"❌ FAIL (Status: {response.status_code})")
                all_passed = False
                
        except requests.exceptions.ConnectionError:
            print("❌ FAIL (Connection refused - server not running)")
            all_passed = False
        except requests.exceptions.Timeout:
            print("❌ FAIL (Timeout)")
            all_passed = False
        except Exception as e:
            print(f"❌ FAIL (Error: {e})")
            all_passed = False
            
        print()
    
    print("-" * 50)
    if all_passed:
        print("🎉 All endpoints are working correctly!")
        return True
    else:
        print("⚠️ Some endpoints failed. Check the server logs.")
        return False

if __name__ == "__main__":
    success = test_server_endpoints()
    sys.exit(0 if success else 1)
