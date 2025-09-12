#!/usr/bin/env python3
"""
Complete Stake Casino Bot System Launcher
Runs the Flask API, serves the mini app, and starts the Telegram bot
"""

import os
import sys
import asyncio
import signal
import subprocess
import threading
import time
from pathlib import Path
import webbrowser
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_status(message, status="INFO"):
    colors = {
        "INFO": Colors.OKBLUE,
        "SUCCESS": Colors.OKGREEN,
        "WARNING": Colors.WARNING,
        "ERROR": Colors.FAIL,
        "HEADER": Colors.HEADER
    }
    color = colors.get(status, Colors.OKBLUE)
    print(f"{color}{message}{Colors.ENDC}")

def check_environment():
    """Check if environment is properly configured"""
    print_status("🔧 Checking environment configuration...", "HEADER")
    
    # Check for BOT_TOKEN
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print_status("❌ BOT_TOKEN not found in environment", "ERROR")
        print_status("Please add your bot token to .env file", "WARNING")
        return False
    
    print_status(f"✅ BOT_TOKEN found: {bot_token[:10]}...", "SUCCESS")
    
    # Check other configurations
    mini_app_url = os.getenv("MINI_APP_URL", "http://localhost:5001")
    flask_api_url = os.getenv("FLASK_API_URL", "http://localhost:5001")
    
    print_status(f"✅ MINI_APP_URL: {mini_app_url}", "SUCCESS")
    print_status(f"✅ FLASK_API_URL: {flask_api_url}", "SUCCESS")
    
    return True

def run_flask_api():
    """Run the Flask API server"""
    print_status("🔥 Starting Flask API server...", "INFO")
    try:
        # Run flask_api.py
        process = subprocess.Popen([
            sys.executable, 
            "flask_api.py"
        ], cwd=Path(__file__).parent)
        
        print_status("✅ Flask API server started successfully", "SUCCESS")
        
        # Wait for the process
        process.wait()
        
    except Exception as e:
        print_status(f"❌ Flask API error: {e}", "ERROR")

def run_telegram_bot():
    """Run the Telegram bot"""
    print_status("🤖 Starting Telegram bot...", "INFO")
    try:
        # Run stake_bot_clean.py
        process = subprocess.Popen([
            sys.executable, 
            "stake_bot_clean.py"
        ], cwd=Path(__file__).parent)
        
        print_status("✅ Telegram bot started successfully", "SUCCESS")
        
        # Wait for the process
        process.wait()
        
    except Exception as e:
        print_status(f"❌ Telegram bot error: {e}", "ERROR")

def show_startup_info():
    """Show startup information"""
    print("\n" + "="*60)
    print_status("🎰 STAKE CASINO BOT SYSTEM", "HEADER")
    print("="*60)
    print_status("🚀 System Components:", "INFO")
    print_status("   📡 Flask API Server (Port 5001)", "INFO")
    print_status("   🤖 Telegram Bot", "INFO") 
    print_status("   🎮 Mini App Interface", "INFO")
    print("\n" + "="*60)
    print_status("🔗 Access Points:", "INFO")
    print_status("   🌐 Flask API: http://localhost:5001", "INFO")
    print_status("   🎮 Mini App: http://localhost:5001/", "INFO")
    print_status("   📊 Health Check: http://localhost:5001/api/health", "INFO")
    print("="*60 + "\n")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print_status("\n🛑 Received shutdown signal. Stopping all services...", "WARNING")
    sys.exit(0)

def main():
    """Main startup function"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Show startup info
    show_startup_info()
    
    # Check environment
    if not check_environment():
        print_status("❌ Environment check failed. Please fix the issues above.", "ERROR")
        return 1
    
    print_status("🚀 Starting all services...", "HEADER")
    
    try:
        # Start Flask API in a separate thread
        flask_thread = threading.Thread(target=run_flask_api, daemon=True)
        flask_thread.start()
        
        # Wait a moment for Flask to start
        time.sleep(3)
        
        # Check if Flask API is running
        import requests
        try:
            response = requests.get("http://localhost:5001/api/health", timeout=5)
            if response.status_code == 200:
                print_status("✅ Flask API is responding", "SUCCESS")
            else:
                print_status("⚠️ Flask API returned unexpected status", "WARNING")
        except:
            print_status("⚠️ Flask API health check failed", "WARNING")
        
        # Start Telegram bot
        print_status("🤖 Starting Telegram bot...", "INFO")
        run_telegram_bot()
        
    except KeyboardInterrupt:
        print_status("\n🛑 Received KeyboardInterrupt. Shutting down...", "WARNING")
    except Exception as e:
        print_status(f"❌ Startup error: {e}", "ERROR")
        return 1
    
    print_status("👋 Casino Bot System stopped", "INFO")
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print_status(f"❌ Fatal error: {e}", "ERROR")
        sys.exit(1)
