#!/usr/bin/env python3
"""
Sticker ID Finder for Telegram Bot
This script helps you find valid sticker file IDs that work with your bot.

Usage:
1. Run this script
2. Send stickers to your bot
3. The bot will reply with the valid file_id
4. Copy those IDs to bot/games/coinflip.py
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ Error: BOT_TOKEN not found in .env file")
    sys.exit(1)

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming stickers and display their file_id"""
    if not update.message or not update.message.sticker:
        return
    
    sticker = update.message.sticker
    user = update.message.from_user
    
    logger.info(f"Received sticker from {user.username} (ID: {user.id})")
    
    # Build detailed sticker info
    info_text = f"""
✅ <b>STICKER RECEIVED</b>

📋 <b>File ID:</b>
<code>{sticker.file_id}</code>

📏 <b>Dimensions:</b> {sticker.width}x{sticker.height}
📦 <b>File Size:</b> {sticker.file_size} bytes
🏷️ <b>Set Name:</b> {sticker.set_name or 'None'}
{"🎭 <b>Emoji:</b> " + sticker.emoji if sticker.emoji else ""}

<b>How to use:</b>
1. Copy the File ID above
2. Open bot/games/coinflip.py
3. Update BITCOIN_STICKER_ID or ETHEREUM_STICKER_ID with this ID
4. Restart your bot

<i>Send more stickers to get their IDs!</i>
"""
    
    try:
        await update.message.reply_text(
            info_text,
            parse_mode='HTML'
        )
        
        # Also print to console for easy copying
        print("\n" + "="*60)
        print(f"STICKER FILE ID: {sticker.file_id}")
        print(f"From: {user.username} ({user.id})")
        print(f"Set: {sticker.set_name or 'N/A'}")
        print("="*60 + "\n")
        
    except Exception as e:
        logger.error(f"Error sending reply: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages with instructions"""
    if not update.message:
        return
    
    help_text = """
🔍 <b>STICKER ID FINDER</b>

This bot will help you find valid sticker file IDs.

<b>How to use:</b>
1️⃣ Send any sticker to this chat
2️⃣ The bot will reply with the sticker's file_id
3️⃣ Copy that ID and use it in your bot

<b>For Coin Flip Game:</b>
• Send a Bitcoin-themed sticker
• Send an Ethereum-themed sticker
• Copy their IDs to bot/games/coinflip.py

💡 <b>Tip:</b> You can find stickers by:
• Searching "@stickers" in any Telegram chat
• Browsing https://t.me/addstickers/
• Creating your own with @Stickers bot

Ready? Send me a sticker! 🎨
"""
    
    await update.message.reply_text(help_text, parse_mode='HTML')

async def main():
    """Run the sticker ID finder bot"""
    print("\n" + "="*60)
    print("🔍 STICKER ID FINDER BOT")
    print("="*60)
    print(f"Bot Token: {BOT_TOKEN[:20]}...")
    print("\nStarting bot...")
    print("Send stickers to get their file IDs")
    print("Press Ctrl+C to stop\n")
    print("="*60 + "\n")
    
    # Build application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Start polling
    print("✅ Bot is running! Send stickers to get their file IDs.\n")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✋ Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Fatal error: {e}", exc_info=True)
