#!/usr/bin/env python3
"""
Quick sticker test script
Test sending the sticker ID you provided
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

# Your sticker ID
TEST_STICKER_ID = "CAACAgEAAxkBAAEYa01o40Ls-VcPD_X8wWSknnbe-rFFdgACIAYAAhUgyUZSc9ORzvjuTDYE"

async def test_sticker():
    """Test sending your sticker"""
    from telegram import Bot
    
    if not BOT_TOKEN or BOT_TOKEN == "test_token_for_local_testing":
        print("❌ Error: Please set a valid BOT_TOKEN in your .env file")
        return
    
    print("🧪 Testing Your Sticker")
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
    print("\n📝 To test the sticker, we need your chat_id")
    print("   You can use @userinfobot on Telegram to get your chat_id")
    print("   Or just start a chat with your bot and use any message")
    print()
    chat_id_input = input("Enter your chat_id (or press Enter to skip): ").strip()
    
    if not chat_id_input:
        print("\n⚠️  Skipping sticker test (no chat_id provided)")
        print("   To test the sticker, run this script again and provide your chat_id")
        return
    
    try:
        chat_id = int(chat_id_input)
    except ValueError:
        print(f"❌ Invalid chat_id: {chat_id_input}")
        return
    
    # Test your sticker
    print(f"\n📤 Sending your sticker...")
    print(f"Sticker ID: {TEST_STICKER_ID}")
    
    try:
        msg = await bot.send_sticker(
            chat_id=chat_id, 
            sticker=TEST_STICKER_ID
        )
        print(f"✅ Sticker sent successfully! Message ID: {msg.message_id}")
        print(f"📱 Check your Telegram chat to see the sticker!")
        
        # Try to get sticker info
        if msg.sticker:
            print(f"\n📋 Sticker Details:")
            print(f"   - File ID: {msg.sticker.file_id}")
            print(f"   - Width: {msg.sticker.width}")
            print(f"   - Height: {msg.sticker.height}")
            print(f"   - Is Animated: {msg.sticker.is_animated}")
            print(f"   - Is Video: {msg.sticker.is_video}")
            if msg.sticker.set_name:
                print(f"   - Sticker Set: {msg.sticker.set_name}")
        
    except Exception as e:
        print(f"❌ Failed to send sticker: {type(e).__name__}: {e}")
        
        # Provide troubleshooting help
        print(f"\n🔧 Troubleshooting:")
        print(f"   1. Check if the sticker ID is valid")
        print(f"   2. Make sure your bot has permission to send stickers")
        print(f"   3. Verify the chat_id is correct")
        print(f"   4. Try with a different sticker ID")
    
    print("\n" + "=" * 50)
    print("🎉 Sticker test complete!")

if __name__ == "__main__":
    try:
        asyncio.run(test_sticker())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
