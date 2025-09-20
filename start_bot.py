#!/usr/bin/env python3
"""
Simple Bot Startup Script
Handles environment setup and graceful startup/shutdown
"""

import os
import sys
import signal
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('casino_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"🛑 Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

def setup_environment():
    """Setup environment and check requirements"""
    logger.info("🔧 Setting up environment...")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv("env.litecoin")
        logger.info("✅ Environment variables loaded")
    except Exception as e:
        logger.error(f"❌ Failed to load environment: {e}")
        return False
    
    # Check critical environment variables
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token or bot_token == 'your_bot_token_here':
        logger.error("❌ BOT_TOKEN not set! Please set your actual bot token.")
        logger.info("💡 Get your bot token from @BotFather on Telegram")
        return False
    
    cryptobot_token = os.getenv('CRYPTOBOT_API_TOKEN')
    if not cryptobot_token:
        logger.error("❌ CRYPTOBOT_API_TOKEN not set!")
        return False
    
    logger.info("✅ Critical environment variables are set")
    return True

def main():
    """Main startup function"""
    logger.info("🎰 Starting Casino Bot...")
    
    # Setup environment
    if not setup_environment():
        logger.error("❌ Environment setup failed")
        sys.exit(1)
    
    # Import and run the bot
    try:
        logger.info("📦 Importing bot modules...")
        import main
        
        logger.info("🚀 Starting bot application...")
        asyncio.run(main.main())
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
