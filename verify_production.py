#!/usr/bin/env python3
"""
Simple Production Verification Script
Quick check if the bot is working correctly
"""

import subprocess
import requests
import os
import sys
from datetime import datetime

def print_header(title):
    print(f"\n{'='*50}")
    print(f"🔍 {title}")
    print(f"{'='*50}")

def print_result(test_name, passed, message=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}" + (f": {message}" if message else ""))
    return passed

def main():
    print("🎰 Telegram Casino Bot - Quick Verification")
    
    results = []
    
    # Test 1: Check if bot process is running
    print_header("Process Check")
    try:
        result = subprocess.run(
            ["pgrep", "-f", "python.*main.py"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            pid = result.stdout.strip()
            results.append(print_result("Bot Process", True, f"PID: {pid}"))
        else:
            results.append(print_result("Bot Process", False, "No process found"))
    except Exception as e:
        results.append(print_result("Bot Process", False, str(e)))
    
    # Test 2: Check required files
    print_header("File Check")
    required_files = ["main.py", ".env", "requirements.txt"]
    base_path = "/Users/ahmed/Telegram Axis"
    
    for file_name in required_files:
        file_path = os.path.join(base_path, file_name)
        exists = os.path.exists(file_path)
        results.append(print_result(f"File: {file_name}", exists))
    
    # Test 3: Check health endpoint
    print_header("Health Check")
    try:
        response = requests.get("http://localhost:10000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            healthy = data.get("status") == "healthy"
            uptime = data.get("uptime_seconds", 0)
            results.append(print_result("Health Endpoint", healthy, f"Uptime: {uptime:.0f}s"))
        else:
            results.append(print_result("Health Endpoint", False, f"HTTP {response.status_code}"))
    except Exception as e:
        results.append(print_result("Health Endpoint", False, str(e)))
    
    # Test 4: Check ping endpoint
    print_header("Ping Test")
    try:
        response = requests.get("http://localhost:10000/ping", timeout=5)
        if response.status_code == 200:
            data = response.json()
            pong = data.get("pong", False)
            results.append(print_result("Ping Endpoint", pong))
        else:
            results.append(print_result("Ping Endpoint", False, f"HTTP {response.status_code}"))
    except Exception as e:
        results.append(print_result("Ping Endpoint", False, str(e)))
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    passed_tests = sum(results)
    total_tests = len(results)
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED - BOT IS OPERATIONAL ✅")
        print("The bot is ready for production use!")
    else:
        print(f"\n⚠️ {total_tests - passed_tests} TESTS FAILED")
        print("Please check the bot and resolve issues.")
    
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Return success code
    return 0 if passed_tests == total_tests else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Verification cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Verification failed with error: {e}")
        sys.exit(1)
