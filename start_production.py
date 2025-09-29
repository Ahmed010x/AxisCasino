#!/usr/bin/env python3
"""
Enhanced Startup Script with Web Server Integration
For production deployment on Render, Heroku, Railway, etc.
"""

import os
import sys
import asyncio
import logging
import signal
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import our deployment-ready bot
from deployment_ready_bot import main as run_bot

def setup_environment():
    """Setup environment variables and configuration"""
    
    # Set default values if not provided
    os.environ.setdefault('PORT', '8080')
    os.environ.setdefault('HOST', '0.0.0.0')
    
    # Check required environment variables
    required_vars = ['BOT_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your deployment environment.")
        sys.exit(1)
    
    print("✅ Environment variables validated")

def setup_logging():
    """Configure logging for production"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', mode='a') if os.access('.', os.W_OK) else logging.NullHandler()
        ]
    )
    
    # Suppress some noisy logs
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    print("✅ Logging configured")

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

async def main():
    """Main startup function"""
    print("🎰 Enhanced Telegram Casino Bot - Production Startup")
    print("=" * 60)
    
    # Setup environment and logging
    setup_environment()
    setup_logging()
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print(f"🚀 Starting bot on port {os.getenv('PORT')}")
    print(f"🌍 Environment: {'Production' if os.getenv('RENDER') else 'Development'}")
    
    try:
        # Run the enhanced bot
        await run_bot()
    except KeyboardInterrupt:
        print("\n👋 Shutdown requested by user")
    except Exception as e:
        print(f"❌ Fatal startup error: {e}")
        logging.exception("Fatal startup error")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        sys.exit(1)
