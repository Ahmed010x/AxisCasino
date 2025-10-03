#!/usr/bin/env python3
"""
Test script to verify the new coin flip sticker IDs work correctly.
"""

import asyncio
import logging
import os
from telegram import Bot
from telegram.error import TelegramError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# New sticker IDs provided by user
BITCOIN_STICKER_ID = "CAACAgIAAxkBAAIC8GdhDLFMpfJJqxhTXUWa5t4T5_7zAAJMOQACqyHJShQ3HXEoC9qyNgQ"
ETHEREUM_STICKER_ID = "CAACAgIAAxkBAAIC8WdhDLKtJPJrAckKJmSUGo9RpQJFAAJMOQACqyHJShQ3HXEoC9qyNgQ"

async def test_new_stickers():
    """Test the new sticker IDs"""
    
    # Load bot token from environment
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment variables")
        print("Please set BOT_TOKEN in your .env file or environment")
        return False
    
    # Get test chat ID
    test_chat_id = os.getenv('TEST_CHAT_ID')
    if not test_chat_id:
        print("❌ TEST_CHAT_ID not found in environment variables")
        print("Please set TEST_CHAT_ID in your .env file with your Telegram user ID")
        return False
    
    bot = Bot(token=bot_token)
    
    print("🧪 Testing new coin flip sticker IDs...")
    
    # Test Bitcoin sticker
    try:
        print(f"Testing Bitcoin sticker (ID: {BITCOIN_STICKER_ID[:30]}...)")
        message = await bot.send_sticker(
            chat_id=test_chat_id,
            sticker=BITCOIN_STICKER_ID
        )
        print(f"✅ Bitcoin sticker sent successfully! Message ID: {message.message_id}")
        await asyncio.sleep(2)  # Wait 2 seconds between stickers
    except TelegramError as e:
        print(f"❌ Bitcoin sticker failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error with Bitcoin sticker: {e}")
        return False
    
    # Test Ethereum sticker
    try:
        print(f"Testing Ethereum sticker (ID: {ETHEREUM_STICKER_ID[:30]}...)")
        message = await bot.send_sticker(
            chat_id=test_chat_id,
            sticker=ETHEREUM_STICKER_ID
        )
        print(f"✅ Ethereum sticker sent successfully! Message ID: {message.message_id}")
    except TelegramError as e:
        print(f"❌ Ethereum sticker failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error with Ethereum sticker: {e}")
        return False
    
    print("✅ All new stickers work correctly!")
    return True

async def main():
    """Main test function"""
    try:
        success = await test_new_stickers()
        if success:
            print("\n🎉 New sticker IDs are working! Your coin flip game should now display stickers correctly.")
        else:
            print("\n❌ There were issues with the new sticker IDs. Please check the errors above.")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(main())
