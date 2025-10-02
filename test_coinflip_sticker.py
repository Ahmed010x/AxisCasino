#!/usr/bin/env python3
"""
Test script to verify coin flip stickers work
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Sticker IDs from coinflip.py
BITCOIN_STICKER_ID = "CAACAgEAAxkBAAEPfLto3fLKQk9KP9FaLSYjwZih82J-sQACIAYAAhUgyUYe7AYU47cPsDYE"
ETHEREUM_STICKER_ID = "CAACAgEAAxkBAAEPfL1o3fOba1jsv5rN1Ojdu5f0DCp_6wACHwYAAhUgyUbBT2yx1FdJ7DYE"

async def test_stickers():
    """Test sending stickers"""
    from telegram import Bot
    
    if not BOT_TOKEN or BOT_TOKEN == "test_token_for_local_testing":
        print("❌ Error: Please set a valid BOT_TOKEN in your .env file")
        return
    
    print("🧪 Testing Coin Flip Stickers")
    print("=" * 50)
    
    bot = Bot(token=BOT_TOKEN)
    
    # Get bot info
    try:
        me = await bot.get_me()
        print(f"✅ Bot connected: @{me.username}")
    except Exception as e:
        print(f"❌ Error connecting to bot: {e}")
        return
    
    # Ask for chat ID
    print("\n📝 To test stickers, send a message to your bot and get the chat_id")
    print("   You can use @userinfobot on Telegram to get your chat_id")
    print()
    chat_id_input = input("Enter your chat_id (or press Enter to skip): ").strip()
    
    if not chat_id_input:
        print("\n⚠️  Skipping sticker test (no chat_id provided)")
        print("   To test stickers, run this script again and provide your chat_id")
        return
    
    try:
        chat_id = int(chat_id_input)
    except ValueError:
        print(f"❌ Invalid chat_id: {chat_id_input}")
        return
    
    # Test Bitcoin sticker
    print(f"\n📤 Sending Bitcoin sticker...")
    try:
        msg = await bot.send_sticker(chat_id=chat_id, sticker=BITCOIN_STICKER_ID)
        print(f"✅ Bitcoin sticker sent successfully! Message ID: {msg.message_id}")
    except Exception as e:
        print(f"❌ Failed to send Bitcoin sticker: {type(e).__name__}: {e}")
    
    # Wait a moment
    await asyncio.sleep(2)
    
    # Test Ethereum sticker
    print(f"\n📤 Sending Ethereum sticker...")
    try:
        msg = await bot.send_sticker(chat_id=chat_id, sticker=ETHEREUM_STICKER_ID)
        print(f"✅ Ethereum sticker sent successfully! Message ID: {msg.message_id}")
    except Exception as e:
        print(f"❌ Failed to send Ethereum sticker: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Sticker test complete!")
    print("\nIf you received the stickers in Telegram, they're working correctly.")
    print("If not, the sticker IDs may need to be updated.")

if __name__ == "__main__":
    try:
        asyncio.run(test_stickers())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
