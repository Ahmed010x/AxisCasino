#!/usr/bin/env python3
"""
Deploy the fixed Telegram Casino Bot
Simple deployment runner for main.py
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Setup logging for deployment"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('casino_bot_fixed.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

async def deploy_bot():
    """Deploy the fixed casino bot"""
    logger = setup_logging()
    
    try:
        logger.info("🚀 Starting deployment of fixed Casino Bot...")
        logger.info(f"📅 Deployment time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Import and run the fixed bot
        import main
        logger.info("✅ Bot module imported successfully")
        
        # The main module will run automatically when imported
        # since it has the if __name__ == "__main__" block
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Deployment failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        # Run the deployment
        print("🎰 Telegram Casino Bot - Fixed Version Deployment")
        print("=" * 50)
        
        # Since main has its own asyncio.run(), we just import it
        import main
        
    except KeyboardInterrupt:
        print("\n❌ Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fatal deployment error: {e}")
        sys.exit(1)
