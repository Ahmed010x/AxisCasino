#!/usr/bin/env python3
"""
Simple Bot Test - Minimal setup to test HTTPXRequest initialization
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def test_bot_initialization():
    """Test basic bot initialization"""
    try:
        logger.info("Testing bot initialization...")
        
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN not found in environment")
            return False
        
        # Create minimal application
        application = (ApplicationBuilder()
                      .token(BOT_TOKEN)
                      .read_timeout(30)
                      .write_timeout(30)
                      .connect_timeout(30)
                      .pool_timeout(30)
                      .build())
        
        logger.info("✅ Application created successfully")
        
        # Initialize the application
        await application.initialize()
        logger.info("✅ Application initialized successfully")
        
        # Test a simple API call
        bot_info = await application.bot.get_me()
        logger.info(f"✅ Bot info retrieved: {bot_info.username}")
        
        # Clean shutdown
        await application.shutdown()
        logger.info("✅ Application shutdown successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Bot initialization test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 Testing Bot HTTPXRequest Initialization")
    print("=" * 50)
    
    success = await test_bot_initialization()
    
    if success:
        print("🎉 Bot initialization test PASSED")
        print("✅ HTTPXRequest is working correctly")
        return 0
    else:
        print("❌ Bot initialization test FAILED")
        print("🔧 Please check the error messages above")
        return 1

if __name__ == "__main__":
    import sys
    try:
        result = asyncio.run(main())
        sys.exit(result)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
