#!/usr/bin/env python3
"""
Production-ready deployment script for Telegram Casino Bot.
This script handles graceful startup and shutdown for deployment platforms.
"""

import asyncio
import logging
import signal
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from main import async_main

def setup_logging():
    """Configure logging for production deployment"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', mode='a')
        ]
    )
    return logging.getLogger(__name__)

def setup_signal_handlers(logger):
    """Setup graceful shutdown signal handlers"""
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down gracefully...")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

async def main():
    """Main deployment entry point"""
    logger = setup_logging()
    setup_signal_handlers(logger)
    
    logger.info("🚀 Starting Telegram Casino Bot (Production Mode)")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    try:
        # Check environment
        required_env = ['BOT_TOKEN']
        missing = [var for var in required_env if not os.getenv(var)]
        if missing:
            logger.error(f"Missing required environment variables: {missing}")
            sys.exit(1)
        
        logger.info("✅ Environment check passed")
        
        # Start the bot
        await async_main()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Bot failed with error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.run(main())
    except Exception as e:
        print(f"Failed to start bot: {e}")
        sys.exit(1)
