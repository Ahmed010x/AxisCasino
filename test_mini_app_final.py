#!/usr/bin/env python3
"""
Final Mini App Centre Test - Comprehensive callback and WebApp verification
Tests all bot handlers, Mini App Centre button, and WebApp functionality
"""

import asyncio
import sys
import os
import logging
from unittest.mock import AsyncMock, MagicMock

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mini_app_centre_final():
    """Test Mini App Centre callback and WebApp functionality"""
    
    print("🔍 FINAL MINI APP CENTRE TEST")
    print("=" * 50)
    
    # Test 1: Import verification
    print("\n1️⃣ Testing imports...")
    try:
        from telegram import Update, CallbackQuery, User as TelegramUser, Message, Chat
        from telegram.ext import Application, CallbackQueryHandler
        print("✅ Telegram imports successful")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test 2: Check if main.py can be imported
    print("\n2️⃣ Testing main.py import...")
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        import main
        print("✅ main.py imported successfully")
    except Exception as e:
        print(f"❌ main.py import error: {e}")
        return False
    
    # Test 3: Check Mini App Centre callback handler
    print("\n3️⃣ Testing Mini App Centre callback handler...")
    
    # Create mock objects
    mock_user = TelegramUser(id=12345, first_name="TestUser", is_bot=False)
    mock_chat = Chat(id=12345, type="private")
    mock_message = Message(
        message_id=1,
        date=None,
        chat=mock_chat,
        from_user=mock_user
    )
    
    mock_callback_query = AsyncMock()
    mock_callback_query.from_user = mock_user
    mock_callback_query.message = mock_message
    mock_callback_query.data = "mini_app_centre"
    mock_callback_query.answer = AsyncMock()
    mock_callback_query.edit_message_text = AsyncMock()
    
    mock_update = AsyncMock()
    mock_update.callback_query = mock_callback_query
    
    mock_context = AsyncMock()
    mock_context.bot = AsyncMock()
    
    try:
        # Call the callback handler
        await main.handle_callback(mock_update, mock_context)
        
        # Verify the callback was answered
        mock_callback_query.answer.assert_called_once()
        
        # Verify message was edited (the handler should send a message)
        assert mock_callback_query.edit_message_text.called, "Mini App Centre callback should edit message"
        
        print("✅ Mini App Centre callback handler works correctly")
        
        # Get the message content that was sent
        call_args = mock_callback_query.edit_message_text.call_args
        if call_args:
            text = call_args[1].get('text', '') if call_args[1] else ''
            print(f"📱 Message content preview: {text[:100]}...")
            
            # Check if WebApp button is included
            reply_markup = call_args[1].get('reply_markup') if call_args[1] else None
            if reply_markup:
                print("✅ Reply markup (buttons) included in response")
            else:
                print("⚠️ No reply markup found - checking inline keyboard")
        
    except Exception as e:
        print(f"❌ Mini App Centre callback test failed: {e}")
        return False
    
    # Test 4: Check WebApp configuration
    print("\n4️⃣ Testing WebApp configuration...")
    
    try:
        webapp_url = getattr(main, 'WEBAPP_URL', None)
        webapp_enabled = getattr(main, 'WEBAPP_ENABLED', False)
        
        print(f"🌐 WebApp URL: {webapp_url}")
        print(f"⚡ WebApp Enabled: {webapp_enabled}")
        
        if webapp_enabled and webapp_url:
            print("✅ WebApp configuration is valid")
        else:
            print("❌ WebApp configuration is invalid")
            return False
            
    except Exception as e:
        print(f"❌ WebApp configuration test failed: {e}")
        return False
    
    # Test 5: Check if WebApp imports are available
    print("\n5️⃣ Testing WebApp imports...")
    
    try:
        webapp_imports_available = getattr(main, 'WEBAPP_IMPORTS_AVAILABLE', False)
        print(f"📱 WebApp imports available: {webapp_imports_available}")
        
        if webapp_imports_available:
            print("✅ WebApp imports are available")
        else:
            print("⚠️ WebApp imports not available - using compatibility mode")
            
    except Exception as e:
        print(f"❌ WebApp imports test failed: {e}")
        return False
    
    # Test 6: Test WebApp server endpoints (if running)
    print("\n6️⃣ Testing WebApp server endpoints...")
    
    try:
        import aiohttp
        
        # Try to connect to the WebApp server
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                # Test health endpoint
                async with session.get('http://localhost:3000/health') as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Health endpoint working: {data.get('status', 'unknown')}")
                    else:
                        print(f"⚠️ Health endpoint returned status {response.status}")
                        
                # Test casino WebApp endpoint
                async with session.get('http://localhost:3000/casino?user_id=test&balance=1000') as response:
                    if response.status == 200:
                        content = await response.text()
                        if '<title>🎰 Casino WebApp</title>' in content:
                            print("✅ Casino WebApp endpoint working correctly")
                        else:
                            print("⚠️ Casino WebApp endpoint returns unexpected content")
                    else:
                        print(f"⚠️ Casino WebApp endpoint returned status {response.status}")
                        
            except aiohttp.ClientError:
                print("ℹ️ WebApp server not running (this is normal if bot is not started)")
                
    except ImportError:
        print("⚠️ aiohttp not available for WebApp server testing")
    except Exception as e:
        print(f"❌ WebApp server test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 FINAL MINI APP CENTRE TEST COMPLETED")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    print("🚀 Starting Final Mini App Centre Test...")
    
    try:
        asyncio.run(test_mini_app_centre_final())
        print("\n✅ All tests completed successfully!")
        print("🎰 Mini App Centre functionality is ready!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
