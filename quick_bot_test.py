#!/usr/bin/env python3
"""
Quick bot test - start and immediately shutdown
"""
import asyncio
import os
import signal
import sys
from dotenv import load_dotenv

load_dotenv()

async def quick_test():
    """Quick test of bot startup and shutdown"""
    print("🧪 Quick Bot Test - Starting...")
    
    try:
        # Import main async function
        sys.path.append('.')
        from main import async_main
        
        # Create a timeout task
        async def timeout_shutdown():
            await asyncio.sleep(3)  # Wait 3 seconds
            print("⏰ Test timeout - sending shutdown signal")
            os.kill(os.getpid(), signal.SIGINT)
        
        # Start timeout task
        timeout_task = asyncio.create_task(timeout_shutdown())
        
        # Try to start the bot
        try:
            await async_main()
        except KeyboardInterrupt:
            print("✅ Bot shutdown gracefully from test timeout")
        
        timeout_task.cancel()
        print("🎉 Quick test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(quick_test())
        print("✅ Test result:", "PASSED" if result else "FAILED")
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        sys.exit(1)
