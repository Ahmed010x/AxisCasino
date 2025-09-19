#!/usr/bin/env python3
"""
Simplified Bot Runner - Test HTTPXRequest without complex restart logic
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def start_command(update, context):
    """Simple start command"""
    await update.message.reply_text("🎰 Simple bot is working!")

async def simple_main():
    """Simple main function without complex features"""
    try:
        logger.info("Starting simple bot...")
        
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN not found")
            return
        
        # Create simple application
        application = (ApplicationBuilder()
                      .token(BOT_TOKEN)
                      .read_timeout(30)
                      .write_timeout(30)
                      .connect_timeout(30)
                      .pool_timeout(30)
                      .build())
        
        # Add simple handler
        application.add_handler(CommandHandler("start", start_command))
        
        # Initialize and start
        await application.initialize()
        await application.start()
        
        logger.info("Bot initialized successfully, starting polling...")
        
        await application.updater.start_polling(
            allowed_updates=["message"],
            drop_pending_updates=True,
            timeout=30
        )
        
        logger.info("Bot is running! Press Ctrl+C to stop...")
        
        # Keep running until stopped
        import signal
        stop_event = asyncio.Event()
        
        def signal_handler(signum, frame):
            stop_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        await stop_event.wait()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        if 'application' in locals():
            await application.stop()
            await application.shutdown()
            logger.info("Bot shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(simple_main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
