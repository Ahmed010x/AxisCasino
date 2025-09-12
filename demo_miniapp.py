#!/usr/bin/env python3
"""
Demo script for Stake Casino Mini App
Shows the complete system working with Flask API and Mini App
"""

import subprocess
import time
import webbrowser
import os
import signal
import sys

def main():
    print("🎰 Stake Casino Mini App Demo")
    print("=" * 50)
    
    # Start Flask API
    print("🚀 Starting Flask API server...")
    api_process = subprocess.Popen([
        'python3', 'flask_api.py'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for API to start
    time.sleep(3)
    
    print("✅ Flask API started on http://localhost:5001")
    print("🎮 Mini App available at http://localhost:5001")
    print("")
    print("🔗 API Endpoints:")
    print("  • Health: http://localhost:5001/api/health")
    print("  • Balance: http://localhost:5001/api/balance/{user_id}")
    print("  • User Info: http://localhost:5001/api/user/{user_id}")
    print("  • Place Bet: POST http://localhost:5001/api/bet")
    print("")
    print("🎯 Mini App Features:")
    print("  • ✅ Telegram WebApp SDK integration")
    print("  • ✅ User first name display")
    print("  • ✅ Real-time balance from backend")
    print("  • ✅ Bet input field with validation")
    print("  • ✅ Play Dice button with backend API")
    print("  • ✅ Win/lose result display")
    print("  • ✅ Dynamic balance updates")
    print("  • ✅ Dark casino-style UI (black + neon green)")
    print("")
    print("🌐 Opening mini app in browser...")
    
    # Open in browser for demo
    webbrowser.open('http://localhost:5001')
    
    print("")
    print("🎮 To test with Telegram:")
    print("1. Set your BOT_TOKEN in .env file")
    print("2. Run: python3 stake_bot_clean.py")
    print("3. Send /start to your bot")
    print("4. Click the WebApp button")
    print("")
    print("Press Ctrl+C to stop the demo...")
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping demo...")
        api_process.terminate()
        api_process.wait()
        print("✅ Demo stopped")

if __name__ == "__main__":
    main()
