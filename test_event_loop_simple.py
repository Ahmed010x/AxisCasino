#!/usr/bin/env python3
"""
Test script to check event loop handling without requiring bot token
"""

import asyncio
import nest_asyncio
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_async_main():
    """Simulate the async main function without bot operations"""
    print("Starting simulated async main...")
    
    # Simulate some async work
    await asyncio.sleep(1)
    print("Async work completed")
    
    # Simulate the keep-alive server startup
    from aiohttp import web
    
    async def health_check(request):
        return web.json_response({"status": "ok", "test": True})
    
    app = web.Application()
    app.router.add_get("/health", health_check)
    
    print("Would start keep-alive server here...")
    # Don't actually start it for testing
    
    print("Simulated bot would run here...")
    await asyncio.sleep(2)
    print("Simulation complete")

def test_main():
    """Test our main function pattern"""
    print("Testing main function pattern...")
    
    nest_asyncio.apply()
    
    try:
        print("Attempting asyncio.run()...")
        asyncio.run(test_async_main())
        print("✓ asyncio.run() worked successfully")
        return True
        
    except RuntimeError as e:
        if "already running" in str(e):
            print("Event loop already running, using alternative approach...")
            loop = asyncio.get_event_loop()
            if loop.is_running():
                print("Loop is running, creating task...")
                task = loop.create_task(test_async_main())
                print("Task created, this would block in production...")
                return True
            else:
                print("Loop exists but not running, using run_until_complete...")
                loop.run_until_complete(test_async_main())
                return True
        else:
            print(f"✗ Unexpected RuntimeError: {e}")
            return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("Testing event loop handling...")
    
    # Test 1: Normal case
    success = test_main()
    
    if success:
        print("\n✓ Event loop test passed!")
        print("The entry point should work on deployment platforms.")
    else:
        print("\n✗ Event loop test failed!")
        print("Need to fix the entry point.")
    
    sys.exit(0 if success else 1)
