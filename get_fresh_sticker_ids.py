#!/usr/bin/env python3
"""
Helper script to get fresh sticker file IDs from Telegram.

Usage:
1. Run this script
2. Send a Bitcoin sticker to your bot
3. Send an Ethereum sticker to your bot
4. The script will print the file IDs you need to copy into coinflip.py

This helps get valid, non-expired sticker file IDs.
"""

import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

print("=" * 70)
print("🎯 STICKER FILE ID COLLECTOR")
print("=" * 70)
print("\n📌 Instructions:")
print("1. Start the bot (it should be running now)")
print("2. Open Telegram and find your bot")
print("3. Send a Bitcoin sticker to the bot (for HEADS)")
print("4. Send an Ethereum sticker to the bot (for TAILS)")
print("5. The file IDs will be printed below - copy them!")
print("\n⏳ Waiting for stickers...\n")
print("-" * 70)

collected_ids = {
    'bitcoin': None,
    'ethereum': None
}

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming stickers and log their file IDs"""
    sticker = update.message.sticker
    
    print(f"\n✅ STICKER RECEIVED!")
    print(f"   File ID: {sticker.file_id}")
    print(f"   File Unique ID: {sticker.file_unique_id}")
    print(f"   Emoji: {sticker.emoji if sticker.emoji else 'N/A'}")
    print(f"   Set Name: {sticker.set_name if sticker.set_name else 'N/A'}")
    print("-" * 70)
    
    # Try to identify if it's Bitcoin or Ethereum based on emoji or set name
    emoji = sticker.emoji.lower() if sticker.emoji else ""
    set_name = sticker.set_name.lower() if sticker.set_name else ""
    
    if 'bitcoin' in set_name or '₿' in emoji or 'btc' in set_name:
        collected_ids['bitcoin'] = sticker.file_id
        print("🟡 This looks like a BITCOIN sticker (for HEADS)")
    elif 'ethereum' in set_name or 'eth' in set_name or 'ether' in emoji:
        collected_ids['ethereum'] = sticker.file_id
        print("🔵 This looks like an ETHEREUM sticker (for TAILS)")
    else:
        print("❓ Unknown crypto - you can manually assign this")
    
    print("-" * 70)
    
    # If we have both, print the final config
    if collected_ids['bitcoin'] and collected_ids['ethereum']:
        print("\n" + "=" * 70)
        print("🎉 ALL STICKERS COLLECTED!")
        print("=" * 70)
        print("\n📋 Copy this configuration into coinflip.py:\n")
        print("COIN_STICKER_PACKS = {")
        print(f'    "heads": [')
        print(f'        "{collected_ids["bitcoin"]}",  # Bitcoin (Heads)')
        print(f'    ],')
        print(f'    "tails": [')
        print(f'        "{collected_ids["ethereum"]}",  # Ethereum (Tails)')
        print(f'    ]')
        print("}")
        print("\n" + "=" * 70)
        print("✨ You can now update coinflip.py with these IDs!")
        print("=" * 70)
    else:
        missing = []
        if not collected_ids['bitcoin']:
            missing.append('Bitcoin (for HEADS)')
        if not collected_ids['ethereum']:
            missing.append('Ethereum (for TAILS)')
        print(f"\n⏳ Still need: {', '.join(missing)}")
    
    # Send confirmation
    await update.message.reply_text(
        f"✅ Sticker received!\n"
        f"File ID: `{sticker.file_id}`\n"
        f"Keep sending more stickers if needed!",
        parse_mode='Markdown'
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages with instructions"""
    await update.message.reply_text(
        "👋 Hi! Send me stickers to get their file IDs.\n\n"
        "I need:\n"
        "🟡 1 Bitcoin sticker (for HEADS)\n"
        "🔵 1 Ethereum sticker (for TAILS)\n\n"
        "Just send the stickers and I'll show you the IDs!"
    )

def main():
    """Run the sticker collector bot"""
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Start the bot
    print("🤖 Bot is running! Send stickers now...\n")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
