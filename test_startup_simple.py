#!/usr/bin/env python3
"""
Simple test to verify the bot starts without event loop errors
"""

import sys
import os
import asyncio
import subprocess
import time

def test_bot_startup():
    """Test that the bot starts without immediate errors"""
    print("Testing bot startup...")
    
    # Start the bot in a subprocess
    try:
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd="/Users/ahmed/Telegram Axis"
        )
        
        # Wait a few seconds to see if it starts properly
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is None:
            print("✓ Bot is running (no immediate exit)")
            # Terminate the process
            process.terminate()
            time.sleep(1)
            if process.poll() is None:
                process.kill()
            return True
        else:
            # Process exited, check output
            stdout, stderr = process.communicate()
            print(f"✗ Bot exited with code: {process.returncode}")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Failed to start bot: {e}")
        return False

if __name__ == "__main__":
    success = test_bot_startup()
    if success:
        print("✓ Bot startup test passed!")
        sys.exit(0)
    else:
        print("✗ Bot startup test failed!")
        sys.exit(1)
