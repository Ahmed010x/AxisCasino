#!/usr/bin/env python3
"""
Keep-Alive Integration Test
Tests that the keep-alive server is properly integrated with the main bot process.
"""

import sys
import os
import time
import requests
import threading
import subprocess
from unittest.mock import patch

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(__file__))

def test_keep_alive_integration():
    """Test that keep-alive server integrates properly with main bot"""
    print("🧪 Testing Keep-Alive Integration...")
    
    # Test 1: Import and function availability
    try:
        from main import create_keep_alive_server, start_keep_alive_server
        print("✅ Keep-alive functions imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import keep-alive functions: {e}")
        return False
    
    # Test 2: Flask app creation
    try:
        app = create_keep_alive_server()
        print("✅ Flask app created successfully")
        
        # Test routes exist
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        expected_routes = ['/', '/health', '/status']
        for route in expected_routes:
            if route in routes:
                print(f"✅ Route {route} exists")
            else:
                print(f"❌ Route {route} missing")
                return False
    except Exception as e:
        print(f"❌ Failed to create Flask app: {e}")
        return False
    
    # Test 3: Server startup (mock test)
    try:
        with patch('threading.Thread') as mock_thread:
            start_keep_alive_server()
            print("✅ Keep-alive server startup function works")
            mock_thread.assert_called_once()
    except Exception as e:
        print(f"❌ Keep-alive server startup failed: {e}")
        return False
    
    print("🎉 All keep-alive integration tests passed!")
    return True

def test_main_integration():
    """Test that main.py includes keep-alive server startup"""
    print("\n🧪 Testing Main Function Integration...")
    
    try:
        with open("main.py", "r") as f:
            content = f.read()
        
        # Check for required imports
        required_imports = [
            "from flask import Flask",
            "import threading"
        ]
        
        for import_line in required_imports:
            if import_line in content:
                print(f"✅ Import found: {import_line}")
            else:
                print(f"❌ Missing import: {import_line}")
                return False
        
        # Check for keep-alive functions
        required_functions = [
            "def create_keep_alive_server():",
            "def start_keep_alive_server():",
            "start_keep_alive_server()"
        ]
        
        for func in required_functions:
            if func in content:
                print(f"✅ Function/call found: {func}")
            else:
                print(f"❌ Missing function/call: {func}")
                return False
        
        print("✅ Main function integration verified")
        return True
        
    except Exception as e:
        print(f"❌ Failed to check main.py integration: {e}")
        return False

def test_deployment_config():
    """Test deployment configuration files"""
    print("\n🧪 Testing Deployment Configuration...")
    
    # Test Procfile
    try:
        with open("Procfile", "r") as f:
            procfile_content = f.read().strip()
        
        if "web: python main.py" in procfile_content:
            print("✅ Procfile correctly configured for integrated server")
        else:
            print(f"❌ Procfile configuration issue. Content: {procfile_content}")
            return False
    except FileNotFoundError:
        print("❌ Procfile not found")
        return False
    except Exception as e:
        print(f"❌ Error reading Procfile: {e}")
        return False
    
    # Test requirements.txt includes Flask
    try:
        with open("requirements.txt", "r") as f:
            requirements = f.read()
        
        if "Flask" in requirements:
            print("✅ Flask dependency found in requirements.txt")
        else:
            print("❌ Flask dependency missing from requirements.txt")
            return False
    except Exception as e:
        print(f"❌ Error checking requirements.txt: {e}")
        return False
    
    print("✅ Deployment configuration verified")
    return True

def main():
    """Run all tests"""
    print("🚀 Keep-Alive Integration Test Suite")
    print("=" * 50)
    
    tests = [
        test_keep_alive_integration,
        test_main_integration,
        test_deployment_config
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    if passed == total:
        print("🎉 All tests passed! Keep-alive integration is ready for deployment.")
        return True
    else:
        print("❌ Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
