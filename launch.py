#!/usr/bin/env python3
"""
Simple launcher for Telegram Casino Bot
Handles environment setup and provides user-friendly startup
"""

import os
import sys
import subprocess

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3.8, 0):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_virtual_environment():
    """Check if virtual environment exists and activate it"""
    venv_path = ".venv"
    if os.path.exists(venv_path):
        print("✅ Virtual environment found")
        if sys.platform == "win32":
            activate_script = os.path.join(venv_path, "Scripts", "activate.bat")
            python_path = os.path.join(venv_path, "Scripts", "python.exe")
        else:
            activate_script = os.path.join(venv_path, "bin", "activate")
            python_path = os.path.join(venv_path, "bin", "python")
        
        if os.path.exists(python_path):
            return python_path
    
    print("⚠️  Virtual environment not found")
    print("   Run setup.sh or create virtual environment manually")
    return None

def check_environment_file():
    """Check if .env file exists and has required variables"""
    if not os.path.exists('.env'):
        print("⚠️  .env file not found")
        print("   Copy .env.example to .env and add your BOT_TOKEN")
        return False
    
    with open('.env', 'r') as f:
        content = f.read()
        if 'test_token_for_local_testing' in content:
            print("⚠️  Please update BOT_TOKEN in .env file")
            print("   Get your token from @BotFather on Telegram")
            return False
    
    print("✅ Environment configuration found")
    return True

def main():
    """Main launcher function"""
    print("🎰 Telegram Casino Bot Launcher")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check virtual environment
    python_path = check_virtual_environment()
    if not python_path:
        python_path = "python3"  # fallback to system python
    
    # Check environment
    env_ok = check_environment_file()
    
    print("\n🚀 Starting Casino Bot...")
    
    if not env_ok:
        print("\n⚠️  Configuration issues detected but continuing...")
        print("   Bot may not work without proper BOT_TOKEN")
    
    try:
        # Launch the bot
        subprocess.run([python_path, "main.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Bot failed to start: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Bot shutdown requested")
    except FileNotFoundError:
        print(f"\n❌ Python not found at: {python_path}")
        print("   Try running: python3 main.py")

if __name__ == "__main__":
    main()
