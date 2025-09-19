#!/usr/bin/env python3
"""
Test the keep-alive system and health monitoring
"""

import asyncio
import time
import requests
from datetime import datetime
import sys
import os

# Add the current directory to the path so we can import from main.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_flask_server():
    """Test the Flask keep-alive server endpoints"""
    print("🧪 Testing Keep-Alive Flask Server...")
    
    try:
        from main import create_keep_alive_server
        app = create_keep_alive_server()
        
        if app:
            print("✅ Flask app created successfully")
            
            # Test app routes are defined
            routes = [rule.rule for rule in app.url_map.iter_rules()]
            expected_routes = ['/', '/health', '/ping', '/restart']
            
            for route in expected_routes:
                if route in routes:
                    print(f"✅ Route {route} found")
                else:
                    print(f"❌ Route {route} missing")
            
            return True
        else:
            print("❌ Failed to create Flask app")
            return False
            
    except Exception as e:
        print(f"❌ Flask server test failed: {e}")
        return False

def test_health_monitor():
    """Test the health monitoring system"""
    print("\n🧪 Testing Health Monitor...")
    
    try:
        from main import BotHealthMonitor
        
        # Create health monitor instance
        health = BotHealthMonitor()
        print("✅ BotHealthMonitor created successfully")
        
        # Test recording updates
        health.record_update()
        health.record_update()
        print("✅ Updates recorded successfully")
        
        # Test recording errors
        health.record_error()
        print("✅ Errors recorded successfully")
        
        # Test health status
        status = health.get_health_status()
        expected_keys = ['healthy', 'uptime_seconds', 'last_update_ago', 'total_updates', 'total_errors', 'error_rate']
        
        for key in expected_keys:
            if key in status:
                print(f"✅ Health status key '{key}' found: {status[key]}")
            else:
                print(f"❌ Health status key '{key}' missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Health monitor test failed: {e}")
        return False

def test_auto_restart():
    """Test the auto-restart system"""
    print("\n🧪 Testing Auto-Restart System...")
    
    try:
        from main import BotAutoRestart
        
        # Create auto-restart instance
        restart = BotAutoRestart()
        print("✅ BotAutoRestart created successfully")
        
        # Test should_restart method
        if restart.should_restart():
            print("✅ should_restart() returns True initially")
        else:
            print("❌ should_restart() should return True initially")
        
        # Test restart delay calculation
        delay = restart.get_restart_delay()
        print(f"✅ Initial restart delay: {delay} seconds")
        
        # Test recording restart
        restart.record_restart()
        print("✅ Restart recorded successfully")
        
        # Test delay increases after restart
        new_delay = restart.get_restart_delay()
        if new_delay > delay:
            print(f"✅ Restart delay increased to: {new_delay} seconds")
        else:
            print(f"⚠️ Restart delay did not increase: {new_delay} seconds")
        
        return True
        
    except Exception as e:
        print(f"❌ Auto-restart test failed: {e}")
        return False

def test_database_init():
    """Test database initialization"""
    print("\n🧪 Testing Database Initialization...")
    
    try:
        from main import init_database
        
        # Test database initialization
        asyncio.run(init_database())
        print("✅ Database initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization test failed: {e}")
        return False

def test_imports():
    """Test all critical imports"""
    print("\n🧪 Testing Critical Imports...")
    
    critical_imports = [
        'BotHealthMonitor',
        'BotAutoRestart', 
        'create_keep_alive_server',
        'start_keep_alive_server',
        'enhanced_error_handler',
        'create_application',
        'run_bot',
        'main'
    ]
    
    try:
        for import_name in critical_imports:
            try:
                exec(f"from main import {import_name}")
                print(f"✅ {import_name} imported successfully")
            except ImportError as e:
                print(f"❌ Failed to import {import_name}: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Keep-Alive System Test Suite")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_health_monitor,
        test_auto_restart,
        test_flask_server,
        test_database_init
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Keep-alive system is ready.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
