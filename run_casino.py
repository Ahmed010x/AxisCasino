#!/usr/bin/env python3
"""
Startup script for Stake Casino Bot
Runs both the Telegram bot and Flask API concurrently
"""

import os
import sys
import asyncio
import signal
import subprocess
import threading
import time
from pathlib import Path

def run_flask_api():
    """Run the Flask API in a separate process"""
    print("🔥 Starting Flask API server...")
    try:
        # Run flask_api.py
        process = subprocess.Popen([
            sys.executable, 
            "flask_api.py"
        ], cwd=Path(__file__).parent)
        
        # Wait for the process to complete
        process.wait()
        
    except Exception as e:
        print(f"❌ Flask API error: {e}")

def run_telegram_bot():
    """Run the Telegram bot"""
    print("🤖 Starting Telegram bot...")
    try:
        # Import and run the bot
        from stake_bot_clean import main
        asyncio.run(main())
        
    except Exception as e:
        print(f"❌ Telegram bot error: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n🛑 Received shutdown signal. Stopping services...")
    sys.exit(0)

def main():
    """Main startup function"""
    print("🎰 Stake Casino Bot System")
    print("🚀 Starting all services...")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check if BOT_TOKEN is set
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("❌ Error: BOT_TOKEN environment variable not set!")
        print("Please set your bot token in the .env file or environment variables")
        sys.exit(1)
    
    try:
        # Start Flask API in a separate thread
        flask_thread = threading.Thread(target=run_flask_api, daemon=True)
        flask_thread.start()
        
        # Give Flask a moment to start
        time.sleep(2)
        print("✅ Flask API started")
        
        # Start Telegram bot in main thread
        run_telegram_bot()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        print("👋 Services stopped")

if __name__ == "__main__":
    main()
