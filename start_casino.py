#!/usr/bin/env python3
"""
Quick Start Script for Stake Casino Bot
Simple script to run the bot directly for testing
"""

import os
import sys
import subprocess
import signal
import time
from dotenv import load_dotenv

load_dotenv()

def check_bot_token():
    """Check if bot token is configured"""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("❌ BOT_TOKEN not found in .env file")
        print("Please add your bot token to the .env file:")
        print("BOT_TOKEN=your_bot_token_here")
        return False
    print(f"✅ Bot token found: {bot_token[:10]}...")
    return True

def start_flask_api():
    """Start Flask API in background"""
    print("🔥 Starting Flask API server...")
    
    try:
        # Start Flask API
        flask_process = subprocess.Popen([
            sys.executable, "flask_api.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for it to start
        time.sleep(3)
        
        # Check if it's running
        if flask_process.poll() is None:
            print("✅ Flask API started successfully on port 5001")
            return flask_process
        else:
            print("❌ Flask API failed to start")
            return None
            
    except Exception as e:
        print(f"❌ Error starting Flask API: {e}")
        return None

def start_telegram_bot():
    """Start Telegram bot"""
    print("🤖 Starting Telegram bot...")
    
    try:
        # Start Telegram bot
        bot_process = subprocess.Popen([
            sys.executable, "stake_bot_clean.py"
        ])
        
        print("✅ Telegram bot started successfully")
        return bot_process
        
    except Exception as e:
        print(f"❌ Error starting Telegram bot: {e}")
        return None

def main():
    """Main function"""
    print("🎰 Stake Casino Bot - Quick Start")
    print("="*40)
    
    # Check configuration
    if not check_bot_token():
        return 1
    
    # Start Flask API
    flask_process = start_flask_api()
    if not flask_process:
        return 1
    
    # Start Telegram bot
    bot_process = start_telegram_bot()
    if not bot_process:
        if flask_process:
            flask_process.terminate()
        return 1
    
    print("\n🚀 System is running!")
    print("="*40)
    print("🌐 Flask API: http://localhost:5001")
    print("🎮 Mini App: http://localhost:5001/")
    print("🤖 Telegram Bot: Ready for commands")
    print("="*40)
    print("\nPress Ctrl+C to stop all services")
    
    try:
        # Wait for bot process to finish
        bot_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        
        # Terminate processes
        if bot_process and bot_process.poll() is None:
            bot_process.terminate()
            print("✅ Telegram bot stopped")
        
        if flask_process and flask_process.poll() is None:
            flask_process.terminate()
            print("✅ Flask API stopped")
    
    print("👋 Goodbye!")
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
