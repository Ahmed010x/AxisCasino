#!/usr/bin/env python3
"""
Deployment verification script
Checks if all required files and configurations are ready for deployment
"""
import os
import json

def check_file_exists(filepath, required=True):
    """Check if file exists and return status"""
    exists = os.path.exists(filepath)
    status = "✅" if exists else ("❌" if required else "⚠️")
    print(f"{status} {filepath} {'(required)' if required else '(optional)'}")
    return exists

def check_deployment_readiness():
    """Check if the bot is ready for deployment"""
    print("🚀 Deployment Readiness Check")
    print("=" * 50)
    
    all_good = True
    
    # Check required files
    print("\n📁 Required Files:")
    required_files = [
        "main.py",
        "requirements.txt", 
        "runtime.txt",
        "render.yaml"
    ]
    
    for file in required_files:
        if not check_file_exists(file, required=True):
            all_good = False
    
    # Check optional files
    print("\n📁 Optional Files:")
    optional_files = [
        "env.example",
        "casino_webapp_new.html",
        "balance_sync.js",
        ".env"
    ]
    
    for file in optional_files:
        check_file_exists(file, required=False)
    
    # Check environment variables
    print("\n🔧 Environment Configuration:")
    required_env_vars = [
        "BOT_TOKEN"
    ]
    
    optional_env_vars = [
        "WEBAPP_URL",
        "WEBAPP_ENABLED", 
        "WEBAPP_SECRET_KEY",
        "PORT",
        "RENDER_EXTERNAL_URL"
    ]
    
    for var in required_env_vars:
        value = os.environ.get(var)
        if value and value != "your_bot_token_here":
            print(f"✅ {var} (set)")
        else:
            print(f"❌ {var} (missing or default)")
            all_good = False
    
    for var in optional_env_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var} (set)")
        else:
            print(f"⚠️ {var} (not set)")
    
    # Check Python syntax
    print("\n🐍 Python Syntax Check:")
    import subprocess
    try:
        result = subprocess.run(['python3', '-m', 'py_compile', 'main.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ main.py syntax is valid")
        else:
            print(f"❌ main.py syntax error: {result.stderr}")
            all_good = False
    except Exception as e:
        print(f"⚠️ Could not check syntax: {e}")
    
    # Check requirements.txt
    print("\n📦 Dependencies Check:")
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
            if 'python-telegram-bot' in requirements:
                print("✅ python-telegram-bot dependency found")
            else:
                print("❌ python-telegram-bot dependency missing")
                all_good = False
                
            if 'aiosqlite' in requirements:
                print("✅ aiosqlite dependency found")
            else:
                print("❌ aiosqlite dependency missing") 
                all_good = False
                
            if 'aiohttp' in requirements:
                print("✅ aiohttp dependency found")
            else:
                print("❌ aiohttp dependency missing")
                all_good = False
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        all_good = False
    
    # Final status
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 DEPLOYMENT READY! ✅")
        print("\n📋 Next steps:")
        print("1. Set BOT_TOKEN environment variable")
        print("2. Deploy to Render or your hosting platform")
        print("3. Set webhook or start polling")
    else:
        print("⚠️ DEPLOYMENT ISSUES FOUND ❌")
        print("\n🔧 Please fix the issues above before deploying")
    
    return all_good

if __name__ == "__main__":
    check_deployment_readiness()
