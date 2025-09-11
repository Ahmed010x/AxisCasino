#!/usr/bin/env python3
"""
Telegram Casino Bot - Simple Main Entry Point

This version is designed to avoid event loop conflicts.
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# Configure logging before imports
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def main():
    """Main function to start the bot."""
    try:
        # Get bot token from environment
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token or bot_token == 'your_telegram_bot_token_here':
            logger.error("BOT_TOKEN not found or using placeholder value!")
            logger.error("Please set a real bot token in .env file")
            return
        
        # Import bot components
        from bot.handlers.start import start, help_command
        from bot.handlers.account import balance, daily_bonus, stats
        from bot.handlers.games import slots, blackjack, roulette, dice, poker, achievements
        from bot.handlers.leaderboard import leaderboard_command
        from bot.handlers.callbacks import button_callback
        from bot.handlers.payment_handlers import payments_menu
        from bot.database.db import init_db
        from bot.utils.achievements import init_achievements_db

        # Initialize database
        logger.info("Initializing database...")
        await init_db()
        await init_achievements_db()
        logger.info("Database initialized successfully")

        # Create application
        logger.info("Creating Telegram application...")
        application = Application.builder().token(bot_token).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("balance", balance))
        application.add_handler(CommandHandler("daily", daily_bonus))
        application.add_handler(CommandHandler("stats", stats))
        application.add_handler(CommandHandler("payments", payments_menu))
        
        # Add game handlers
        application.add_handler(CommandHandler("slots", slots))
        application.add_handler(CommandHandler("blackjack", blackjack))
        application.add_handler(CommandHandler("roulette", roulette))
        application.add_handler(CommandHandler("dice", dice))
        application.add_handler(CommandHandler("poker", poker))
        application.add_handler(CommandHandler("achievements", achievements))
        application.add_handler(CommandHandler("leaderboard", leaderboard_command))
        
        # Add callback query handler for inline buttons
        application.add_handler(CallbackQueryHandler(button_callback))

        # Run the bot until the user presses Ctrl-C
        logger.info("🎰 Starting Telegram Casino Bot...")
        logger.info("Bot is ready! Send /start to begin playing.")
        
        await application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

def run_bot():
    """Run the bot with proper event loop handling."""
    try:
        # Set event loop policy for Windows
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the bot
        loop.run_until_complete(main())
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.close()
        except:
            pass

if __name__ == '__main__':
    run_bot()
