#!/usr/bin/env python3
"""
Quick test to verify bot is working and can send messages.
This helps debug before trying to collect sticker IDs.
"""

import os
import sys
import asyncio
from telegram import Bot

async def test_bot():
    """Test basic bot functionality"""
    bot_token = os.getenv('BOT_TOKEN')
    
    if not bot_token:
        print("❌ BOT_TOKEN environment variable not set!")
        print("Run: export BOT_TOKEN='your_token_here'")
        sys.exit(1)
    
    print("🤖 Testing bot with token:", bot_token[:20] + "...")
    
    bot = Bot(token=bot_token)
    
    try:
        # Get bot info
        me = await bot.get_me()
        print(f"\n✅ Bot is alive!")
        print(f"   Username: @{me.username}")
        print(f"   Name: {me.first_name}")
        print(f"   ID: {me.id}")
        print(f"\n✨ Bot is ready to collect sticker IDs!")
        print(f"\n📱 Open Telegram and message @{me.username}")
        return True
    except Exception as e:
        print(f"\n❌ Bot test failed: {e}")
        return False

if __name__ == '__main__':
    result = asyncio.run(test_bot())
    sys.exit(0 if result else 1)
