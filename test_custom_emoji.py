#!/usr/bin/env python3
"""
Test Custom Emoji Implementation
Test different methods to send custom emojis in Telegram Bot
"""

import asyncio
import logging
from telegram import Bot, MessageEntity
from telegram.constants import ParseMode
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Custom Telegram Emoji IDs for testing
HEADS_EMOJI_ID = "5886663771962743061"
TAILS_EMOJI_ID = "5886234567290918532"

async def test_custom_emoji_methods(bot: Bot, chat_id: str):
    """Test different methods to send custom emojis"""
    
    print("🧪 Testing Custom Emoji Methods...")
    
    # Method 1: MessageEntity with custom_emoji_id
    print("\n1️⃣ Testing MessageEntity with custom_emoji_id...")
    try:
        text = "🪙 Testing custom emoji: 🪙"
        entities = [
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=0,
                length=1,
                custom_emoji_id=HEADS_EMOJI_ID
            ),
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=len("🪙 Testing custom emoji: "),
                length=1,
                custom_emoji_id=TAILS_EMOJI_ID
            )
        ]
        
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            entities=entities
        )
        print("✅ MessageEntity method sent successfully")
        
    except Exception as e:
        print(f"❌ MessageEntity method failed: {e}")
    
    # Method 2: HTML <tg-emoji> tags
    print("\n2️⃣ Testing HTML <tg-emoji> tags...")
    try:
        html_text = f'''
🎰 <b>COIN FLIP TEST</b> 🎰

<tg-emoji emoji-id="{HEADS_EMOJI_ID}">🪙</tg-emoji> <b>HEADS</b> <tg-emoji emoji-id="{HEADS_EMOJI_ID}">🪙</tg-emoji>

<tg-emoji emoji-id="{TAILS_EMOJI_ID}">🪙</tg-emoji> <b>TAILS</b> <tg-emoji emoji-id="{TAILS_EMOJI_ID}">🪙</tg-emoji>

<i>Testing custom emoji display...</i>
'''
        
        await bot.send_message(
            chat_id=chat_id,
            text=html_text,
            parse_mode=ParseMode.HTML
        )
        print("✅ HTML <tg-emoji> method sent successfully")
        
    except Exception as e:
        print(f"❌ HTML <tg-emoji> method failed: {e}")
    
    # Method 3: Direct custom emoji IDs in text (experimental)
    print("\n3️⃣ Testing direct emoji ID insertion...")
    try:
        # This is experimental - might not work
        direct_text = f"🎰 Direct emoji test: [{HEADS_EMOJI_ID}] vs [{TAILS_EMOJI_ID}]"
        
        await bot.send_message(
            chat_id=chat_id,
            text=direct_text
        )
        print("✅ Direct emoji ID method sent successfully")
        
    except Exception as e:
        print(f"❌ Direct emoji ID method failed: {e}")
    
    # Method 4: Fallback with enhanced regular emojis
    print("\n4️⃣ Testing enhanced fallback emojis...")
    try:
        fallback_text = """
🎰 <b>COIN FLIP FALLBACK</b> 🎰

🟡 <b>HEADS</b> 🟡 (Gold Coin)
🔵 <b>TAILS</b> 🔵 (Blue Coin)

<i>Using standard emojis as fallback...</i>
"""
        
        await bot.send_message(
            chat_id=chat_id,
            text=fallback_text,
            parse_mode=ParseMode.HTML
        )
        print("✅ Fallback emoji method sent successfully")
        
    except Exception as e:
        print(f"❌ Fallback emoji method failed: {e}")

async def main():
    """Main test function"""
    
    # Get bot token from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment variables")
        return
    
    # Get test chat ID (you can replace this with your user ID for testing)
    test_chat_id = os.getenv('TEST_CHAT_ID')
    if not test_chat_id:
        print("❌ TEST_CHAT_ID not found in environment variables")
        print("💡 Add your Telegram user ID as TEST_CHAT_ID in .env file for testing")
        return
    
    # Initialize bot
    bot = Bot(token=bot_token)
    
    try:
        # Test bot connection
        me = await bot.get_me()
        print(f"🤖 Bot connected: @{me.username}")
        
        # Run custom emoji tests
        await test_custom_emoji_methods(bot, test_chat_id)
        
        print("\n✅ All tests completed!")
        print("\n📝 Instructions for user:")
        print("1. Check your Telegram chat for test messages")
        print("2. If custom emojis appear as regular emojis, it means:")
        print("   - Your bot might not have access to the custom emoji pack")
        print("   - Custom emojis might require Telegram Premium")
        print("   - The emoji IDs might be incorrect or expired")
        print("3. The fallback method should always work with regular emojis")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
