#!/usr/bin/env python3
"""
Startup script for Telegram Casino Bot
Handles dependencies and deployment scenarios gracefully
"""

import sys
import subprocess
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_requirements():
    """Install required packages if not available"""
    required_packages = [
        "python-telegram-bot==20.7",
        "aiosqlite==0.19.0", 
        "python-dotenv==1.0.0",
        "nest-asyncio==1.5.8",
        "aiohttp==3.9.1"
    ]
    
    for package in required_packages:
        try:
            __import__(package.split('==')[0].replace('-', '_'))
        except ImportError:
            logger.info(f"Installing {package}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_dependencies():
    """Check if all dependencies are available"""
    try:
        import telegram
        import aiosqlite
        import dotenv
        import nest_asyncio
        import aiohttp
        logger.info("✅ All dependencies available")
        return True
    except ImportError as e:
        logger.warning(f"❌ Missing dependency: {e}")
        return False

if __name__ == "__main__":
    logger.info("🎰 Starting Telegram Casino Bot...")
    
    # Check dependencies
    if not check_dependencies():
        logger.info("📦 Installing missing dependencies...")
        try:
            install_requirements()
        except Exception as e:
            logger.error(f"❌ Failed to install dependencies: {e}")
            sys.exit(1)
    
    # Start the main bot
    try:
        import main
        logger.info("✅ Bot startup completed")
    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}")
        sys.exit(1)
