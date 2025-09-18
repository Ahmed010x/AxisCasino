#!/usr/bin/env python3
"""
Test deployment entry point with dummy configuration
"""

import os
import sys
import asyncio
import subprocess
import time

def test_deploy_script():
    """Test the deployment script with dummy environment"""
    print("Testing deployment script...")
    
    # Set dummy environment variables
    env = os.environ.copy()
    env['BOT_TOKEN'] = 'dummy_token_for_testing'
    env['ADMIN_USER_IDS'] = '123456789'
    
    try:
        # Start the deployment script
        process = subprocess.Popen(
            [sys.executable, 'deploy_bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd="/Users/ahmed/Telegram Axis"
        )
        
        # Wait a few seconds to see startup behavior
        time.sleep(3)
        
        # Check if process is still running or if it failed gracefully
        return_code = process.poll()
        
        if return_code is None:
            print("✓ Process is running (no immediate crash)")
            # Terminate cleanly
            process.terminate()
            stdout, stderr = process.communicate(timeout=5)
            print("Process terminated successfully")
            return True
        else:
            # Process exited, check why
            stdout, stderr = process.communicate()
            print(f"Process exited with code: {return_code}")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            
            # For this test, we expect it to fail at bot initialization due to dummy token
            # But it should not fail at the entry point level
            if "Failed to start bot" in stderr or "Invalid token" in stderr:
                print("✓ Expected failure at bot initialization (dummy token)")
                return True
            else:
                print("✗ Unexpected failure")
                return False
                
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def test_main_entry():
    """Test the main.py entry point"""
    print("\nTesting main.py entry point...")
    
    env = os.environ.copy()
    env['BOT_TOKEN'] = 'dummy_token_for_testing'
    env['ADMIN_USER_IDS'] = '123456789'
    
    try:
        process = subprocess.Popen(
            [sys.executable, 'main.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd="/Users/ahmed/Telegram Axis"
        )
        
        time.sleep(3)
        
        return_code = process.poll()
        
        if return_code is None:
            print("✓ Process is running")
            process.terminate()
            stdout, stderr = process.communicate(timeout=5)
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"Process exited with code: {return_code}")
            if "Invalid token" in stderr or "HTTP" in stderr:
                print("✓ Expected failure at bot initialization")
                return True
            else:
                print("✗ Unexpected early exit")
                print(f"STDERR: {stderr}")
                return False
                
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("Running deployment tests...")
    
    test1 = test_deploy_script()
    test2 = test_main_entry()
    
    if test1 and test2:
        print("\n✅ All deployment tests passed!")
        print("The bot should deploy successfully on Render.")
    else:
        print("\n❌ Some tests failed!")
        print("Need to fix deployment issues.")
    
    sys.exit(0 if (test1 and test2) else 1)
