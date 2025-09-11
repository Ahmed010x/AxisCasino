#!/usr/bin/env python3
"""
Simple bot launcher that avoids event loop conflicts.
"""

import subprocess
import sys
import os

def launch_bot():
    """Launch the bot in a clean subprocess."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(script_dir, ".venv", "bin", "python")
    main_script = os.path.join(script_dir, "main.py")
    
    if not os.path.exists(venv_python):
        print("❌ Virtual environment not found!")
        print(f"Expected: {venv_python}")
        return False
    
    if not os.path.exists(main_script):
        print("❌ main.py not found!")
        return False
    
    # Check if .env file exists and has token
    env_file = os.path.join(script_dir, ".env")
    if not os.path.exists(env_file):
        print("❌ .env file not found!")
        print("Please create .env file with BOT_TOKEN=your_token_here")
        return False
    
    print("🚀 Launching Telegram Casino Bot...")
    print("📍 Press Ctrl+C to stop the bot")
    print("🎮 Available commands:")
    print("   /start - Start the casino")
    print("   /help - Show help and game rules")
    print("   /slots - Play slot machine")
    print("   /blackjack - Play blackjack")
    print("   /roulette - Play roulette")
    print("   /dice - Play dice games")
    print("   /poker - Play Texas Hold'em poker")
    print("   /balance - Check your balance")
    print("   /daily - Claim daily bonus")
    print("   /achievements - View achievements")
    print("   /leaderboard - View leaderboards")
    print("   /payments - Manage deposits/withdrawals")
    print()
    
    try:
        # Launch the bot as a subprocess
        result = subprocess.run([venv_python, main_script], cwd=script_dir)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        return True
    except Exception as e:
        print(f"❌ Error launching bot: {e}")
        return False

if __name__ == "__main__":
    success = launch_bot()
    if not success:
        print("\n❌ Bot failed to start properly")
        sys.exit(1)
