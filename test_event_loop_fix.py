#!/usr/bin/env python3
"""
Test script to verify the event loop fix works correctly.
This simulates different event loop scenarios.
"""

import asyncio
import nest_asyncio

async def dummy_async_main():
    """Dummy async main for testing"""
    print("Dummy async main started")
    await asyncio.sleep(1)
    print("Dummy async main completed")
    return True

def test_no_existing_loop():
    """Test when there's no existing event loop"""
    print("\n=== Testing with no existing loop ===")
    
    try:
        loop = asyncio.get_running_loop()
        print("ERROR: Found unexpected existing loop")
        return False
    except RuntimeError:
        print("✓ No existing loop detected (expected)")
    
    # Test our main pattern
    try:
        result = asyncio.run(dummy_async_main())
        print(f"✓ asyncio.run() worked: {result}")
        return True
    except Exception as e:
        print(f"✗ asyncio.run() failed: {e}")
        return False

def test_with_existing_loop():
    """Test when there's already an existing event loop"""
    print("\n=== Testing with existing loop ===")
    
    nest_asyncio.apply()
    
    async def run_test():
        try:
            # Now we're inside a running loop
            loop = asyncio.get_running_loop()
            print("✓ Found existing loop (expected)")
            
            # Test our pattern
            task = asyncio.ensure_future(dummy_async_main())
            result = await task
            print(f"✓ ensure_future() worked: {result}")
            return True
            
        except Exception as e:
            print(f"✗ Test failed: {e}")
            return False
    
    try:
        result = asyncio.run(run_test())
        return result
    except Exception as e:
        print(f"✗ Outer test failed: {e}")
        return False

def test_main_pattern():
    """Test our actual main() pattern"""
    print("\n=== Testing main() pattern ===")
    
    nest_asyncio.apply()
    
    def test_main():
        try:
            loop = asyncio.get_running_loop()
            print("Found existing event loop, scheduling task...")
            return asyncio.ensure_future(dummy_async_main())
        except RuntimeError:
            print("No existing event loop, creating new one...")
            return asyncio.run(dummy_async_main())
    
    try:
        result = test_main()
        print(f"✓ Main pattern worked: {result}")
        return True
    except Exception as e:
        print(f"✗ Main pattern failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing event loop handling patterns...")
    
    tests = [
        test_no_existing_loop,
        test_with_existing_loop,
        test_main_pattern
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print(f"\n=== Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    if all(results):
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
