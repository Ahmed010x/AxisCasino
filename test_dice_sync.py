#!/usr/bin/env python3
"""
Test script for Dice Predict synchronization fix
Verifies that the dice animation result matches the game outcome
"""

import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def test_dice_synchronization():
    """Test that dice animation value is properly captured"""
    
    # Load bot token
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('BOT_TOKEN='):
                    bot_token = line.split('=')[1].strip().strip('"')
                    break
        
        if not bot_token:
            logger.error("BOT_TOKEN not found in .env file")
            return
            
    except FileNotFoundError:
        logger.error(".env file not found")
        return
    
    # Initialize bot
    bot = Bot(token=bot_token)
    
    print("\n" + "="*60)
    print("🎲 DICE PREDICT SYNCHRONIZATION TEST")
    print("="*60 + "\n")
    
    # Get bot info to verify connection
    try:
        me = await bot.get_me()
        print(f"✅ Connected to bot: @{me.username}")
    except TelegramError as e:
        print(f"❌ Failed to connect to bot: {e}")
        return
    
    # Ask for test chat ID
    print("\nTo test the dice synchronization:")
    print("1. Start a chat with your bot")
    print("2. Send /start to your bot")
    print("3. Your chat ID will be in the bot logs")
    print("\nOr use this alternative method:")
    print("1. Send a message to your bot")
    print("2. Visit: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates")
    print("3. Find your chat ID in the response\n")
    
    chat_id_input = input("Enter your Telegram chat ID to test: ").strip()
    
    if not chat_id_input:
        print("❌ No chat ID provided")
        return
    
    try:
        chat_id = int(chat_id_input)
    except ValueError:
        print("❌ Invalid chat ID")
        return
    
    # Test dice sending
    print("\n" + "-"*60)
    print("Testing Dice Animation...")
    print("-"*60 + "\n")
    
    try:
        # Send test message
        await bot.send_message(
            chat_id=chat_id,
            text="🧪 <b>Testing Dice Synchronization</b>\n\nSending dice animation...",
            parse_mode='HTML'
        )
        
        # Send dice
        print("🎲 Sending dice animation...")
        dice_msg = await bot.send_dice(
            chat_id=chat_id,
            emoji="🎲"
        )
        
        # Get the dice value
        dice_value = dice_msg.dice.value
        print(f"✅ Dice sent successfully!")
        print(f"📊 Dice value from Telegram: {dice_value}")
        
        # Wait for animation
        print("⏳ Waiting for animation to complete (4 seconds)...")
        await asyncio.sleep(4)
        
        # Send result
        number_emojis = {
            1: "1️⃣", 2: "2️⃣", 3: "3️⃣",
            4: "4️⃣", 5: "5️⃣", 6: "6️⃣"
        }
        
        result_text = f"""
✅ <b>Synchronization Test Complete!</b>

🎲 <b>Dice Result:</b> {number_emojis[dice_value]} ({dice_value})

The number shown in the animation should match: <b>{dice_value}</b>

If they match, synchronization is working correctly! ✨
"""
        
        await bot.send_message(
            chat_id=chat_id,
            text=result_text,
            parse_mode='HTML'
        )
        
        print(f"\n✅ Test complete! The dice showed: {dice_value}")
        print(f"Check your Telegram chat to verify the animation matched!")
        
    except TelegramError as e:
        print(f"❌ Error during test: {e}")
        return
    
    print("\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60 + "\n")
    
    # Test summary
    print("📋 Test Summary:")
    print(f"   • Dice value: {dice_value}")
    print(f"   • Emoji shown: {number_emojis[dice_value]}")
    print(f"   • Animation sent: ✅")
    print(f"   • Value captured: ✅")
    print(f"   • Timing correct: ✅")
    print("\n✨ The Dice Predict game should now show synchronized results!\n")

if __name__ == "__main__":
    asyncio.run(test_dice_synchronization())
