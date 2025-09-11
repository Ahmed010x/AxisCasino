#!/usr/bin/env python3
"""
Telegram Casino Bot - Clean Entry Point

This version uses a clean subprocess approach to avoid any event loop conflicts.
"""

import subprocess
import sys
import os
import signal

def run_bot():
    """Run the bot in a clean subprocess environment."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(script_dir, ".venv", "bin", "python")
    
    # Check if virtual environment exists
    if not os.path.exists(venv_python):
        print("❌ Virtual environment not found!")
        print(f"Expected: {venv_python}")
        print("Please run: python -m venv .venv && .venv/bin/pip install -r requirements.txt")
        return False
    
    # Check if .env file exists
    env_file = os.path.join(script_dir, ".env")
    if not os.path.exists(env_file):
        print("❌ .env file not found!")
        print("Please create .env file with your bot token:")
        print("BOT_TOKEN=your_telegram_bot_token_here")
        return False
    
    # Create the bot script content
    bot_script = '''#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Main bot function."""
    # Import bot components
    from bot.handlers.start import start, help_command
    from bot.handlers.account import balance, daily_bonus, stats
    from bot.handlers.games import slots, blackjack, roulette, dice, poker, achievements
    from bot.handlers.leaderboard import leaderboard_command
    from bot.handlers.callbacks import button_callback
    from bot.handlers.payment_handlers import payments_menu
    from bot.database.db import init_db
    from bot.utils.achievements import init_achievements_db

    # Get bot token
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token or bot_token == 'your_telegram_bot_token_here':
        logger.error("❌ BOT_TOKEN not found or using placeholder!")
        logger.error("Please set a real bot token in .env file")
        return

    # Initialize database
    logger.info("🔧 Initializing database...")
    await init_db()
    await init_achievements_db()
    logger.info("✅ Database initialized successfully")

    # Create application
    logger.info("🤖 Creating Telegram application...")
    application = Application.builder().token(bot_token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("daily", daily_bonus))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("payments", payments_menu))
    application.add_handler(CommandHandler("slots", slots))
    application.add_handler(CommandHandler("blackjack", blackjack))
    application.add_handler(CommandHandler("roulette", roulette))
    application.add_handler(CommandHandler("dice", dice))
    application.add_handler(CommandHandler("poker", poker))
    application.add_handler(CommandHandler("achievements", achievements))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start bot
    logger.info("🎰 Starting Telegram Casino Bot...")
    logger.info("🚀 Bot is ready! Send /start to begin playing.")
    logger.info("📱 Available commands:")
    logger.info("   /start - Start the casino")
    logger.info("   /help - Show help and game rules")
    logger.info("   /slots, /blackjack, /roulette, /dice, /poker - Play games")
    logger.info("   /balance, /daily, /stats - Account management")
    logger.info("   /achievements, /leaderboard - Progress tracking")
    logger.info("   /payments - Deposit/withdrawal management")
    logger.info("🛑 Press Ctrl+C to stop the bot")
    
    await application.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
        print("\\n👋 Casino bot stopped. Thanks for playing!")
'''

    # Write the clean bot script
    clean_bot_path = os.path.join(script_dir, "run_bot_clean.py")
    with open(clean_bot_path, 'w') as f:
        f.write(bot_script)
    
    print("🎰 TELEGRAM CASINO BOT")
    print("=" * 50)
    print("🚀 Starting bot in clean environment...")
    print("📍 Press Ctrl+C to stop the bot")
    print("🎮 All casino games are ready!")
    print()
    
    try:
        # Run the clean bot script
        process = subprocess.Popen([venv_python, clean_bot_path], cwd=script_dir)
        
        def signal_handler(sig, frame):
            print("\\n🛑 Stopping bot...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Wait for the process
        process.wait()
        return process.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running bot: {e}")
        return False
    finally:
        # Clean up the temporary script
        if os.path.exists(clean_bot_path):
            os.remove(clean_bot_path)

if __name__ == "__main__":
    success = run_bot()
    if not success:
        print("\\n❌ Bot failed to start properly")
        sys.exit(1)
