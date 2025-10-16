#!/usr/bin/env python3
"""
Production Startup Script for Telegram Casino Bot
Handles environment setup, database initialization, and bot startup.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

def setup_logging():
    """Configure logging for production"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('casino_bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noisy telegram logs
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)

def check_environment():
    """Check environment configuration"""
    logger = logging.getLogger(__name__)
    
    required_vars = ['BOT_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var) == 'test_token_for_local_testing':
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing or invalid environment variables: {missing_vars}")
        logger.error("Please update your .env file with production values")
        return False
    
    logger.info("Environment configuration verified ✅")
    return True

def check_database():
    """Check database exists and is accessible"""
    logger = logging.getLogger(__name__)
    
    db_path = os.getenv('CASINO_DB', 'casino.db')
    
    if not os.path.exists(db_path):
        logger.warning(f"Database file {db_path} not found - will be created on first run")
    else:
        logger.info(f"Database file {db_path} found ✅")
    
    return True

async def start_bot():
    """Start the casino bot"""
    logger = logging.getLogger(__name__)
    
    try:
        # Import main module
        import main
        
        logger.info("🎰 Starting Telegram Casino Bot...")
        logger.info(f"Startup time: {datetime.now()}")
        
        # The main module will handle the bot startup
        # This is just a wrapper to ensure proper error handling
        
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error starting bot: {e}")
        raise

def main():
    """Main startup function"""
    print("🚀 Telegram Casino Bot - Production Startup")
    print("=" * 50)
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check database
    if not check_database():
        sys.exit(1)
    
    # Start bot
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
