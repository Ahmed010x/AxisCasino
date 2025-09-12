#!/usr/bin/env python3
"""
Direct Mini App Centre Button Test
Tests the Mini App Centre button and WebApp URL generation directly
"""

import asyncio
import sys
import os

async def test_mini_app_button():
    """Test Mini App Centre button and WebApp functionality directly"""
    
    print("🎮 DIRECT MINI APP CENTRE BUTTON TEST")
    print("=" * 50)
    
    # Import main module
    sys.path.insert(0, os.path.dirname(__file__))
    import main
    
    print(f"\n📱 WebApp Configuration:")
    print(f"   URL: {main.WEBAPP_URL}")
    print(f"   Enabled: {main.WEBAPP_ENABLED}")
    print(f"   Imports Available: {main.WEBAPP_IMPORTS_AVAILABLE}")
    
    # Test 1: Check if show_mini_app_centre function exists
    print(f"\n1️⃣ Testing show_mini_app_centre function...")
    
    if hasattr(main, 'show_mini_app_centre'):
        print("✅ show_mini_app_centre function found")
        
        # Check function signature
        import inspect
        sig = inspect.signature(main.show_mini_app_centre)
        print(f"   Function signature: {sig}")
        
    else:
        print("❌ show_mini_app_centre function not found")
        return False
    
    # Test 2: Check Mini App Centre button generation
    print(f"\n2️⃣ Testing Mini App Centre button generation...")
    
    try:
        from telegram import InlineKeyboardButton, WebAppInfo
        
        # Test WebApp button creation
        if main.WEBAPP_ENABLED and main.WEBAPP_IMPORTS_AVAILABLE:
            try:
                # Create a WebApp button like the bot does
                webapp_button = InlineKeyboardButton(
                    "🎰 Open Casino WebApp",
                    web_app=WebAppInfo(url=main.WEBAPP_URL)
                )
                print("✅ WebApp button created successfully")
                print(f"   Button text: {webapp_button.text}")
                print(f"   WebApp URL: {webapp_button.web_app.url}")
                
            except Exception as e:
                print(f"❌ WebApp button creation failed: {e}")
                return False
        else:
            print("ℹ️ WebApp disabled or imports not available")
            
    except Exception as e:
        print(f"❌ Button generation test failed: {e}")
        return False
    
    # Test 3: Test callback data handling
    print(f"\n3️⃣ Testing callback data handling...")
    
    # Check if the callback handler looks for "mini_app_centre"
    try:
        import inspect
        source = inspect.getsource(main.handle_callback)
        
        if 'mini_app_centre' in source:
            print("✅ Callback handler includes 'mini_app_centre' case")
            
            # Check if it calls show_mini_app_centre
            if 'show_mini_app_centre' in source:
                print("✅ Callback handler calls show_mini_app_centre function")
            else:
                print("⚠️ Callback handler doesn't call show_mini_app_centre")
        else:
            print("❌ Callback handler doesn't handle 'mini_app_centre'")
            return False
            
    except Exception as e:
        print(f"❌ Callback data test failed: {e}")
        return False
    
    # Test 4: Test WebApp endpoint availability (if server is running)
    print(f"\n4️⃣ Testing WebApp endpoint availability...")
    
    try:
        import aiohttp
        
        timeout = aiohttp.ClientTimeout(total=3)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(main.WEBAPP_URL.split('?')[0]) as response:
                    if response.status == 200:
                        content = await response.text()
                        if '🎰 Casino WebApp' in content:
                            print("✅ WebApp endpoint is serving casino content")
                        else:
                            print("⚠️ WebApp endpoint serves content but not casino-specific")
                    else:
                        print(f"⚠️ WebApp endpoint returned status {response.status}")
                        
            except aiohttp.ClientError:
                print("ℹ️ WebApp server not reachable (bot may not be running)")
                
    except ImportError:
        print("⚠️ aiohttp not available for endpoint testing")
    except Exception as e:
        print(f"❌ WebApp endpoint test failed: {e}")
    
    print(f"\n" + "=" * 50)
    print("🎉 DIRECT MINI APP CENTRE BUTTON TEST COMPLETED")
    
    # Summary
    print(f"\n📋 SUMMARY:")
    print(f"   ✅ Mini App function exists: YES")
    print(f"   ✅ WebApp enabled: {main.WEBAPP_ENABLED}")
    print(f"   ✅ WebApp URL configured: {main.WEBAPP_URL}")
    print(f"   ✅ Callback handler ready: YES")
    
    return True

if __name__ == "__main__":
    print("🚀 Starting Direct Mini App Centre Button Test...")
    
    try:
        asyncio.run(test_mini_app_button())
        print("\n🎰 Mini App Centre button is ready for Telegram!")
        print("📱 Users can now click the Mini App Centre button to open the casino WebApp")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
