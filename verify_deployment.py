#!/usr/bin/env python3
"""
Final Deployment Verification Script
Ensures the bot is production-ready and all systems work correctly
"""
import asyncio
import os
import sys
import sqlite3
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_environment():
    """Check all required environment variables"""
    print("🔍 Checking environment variables...")
    
    required_vars = ['BOT_TOKEN', 'ADMIN_USER_IDS']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            masked_value = value[:10] + "..." if len(value) > 10 else value
            print(f"✅ {var}: {masked_value}")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False
    
    print("✅ All environment variables present")
    return True

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("\n🔍 Checking dependencies...")
    
    required_packages = [
        'telegram',
        'aiosqlite', 
        'flask',
        'waitress',
        'aiohttp',
        'dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"❌ Missing packages: {missing_packages}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies installed")
    return True

def check_database():
    """Check database file and structure"""
    print("\n🔍 Checking database...")
    
    db_path = os.getenv('CASINO_DB', 'casino.db')
    
    if not os.path.exists(db_path):
        print(f"⚠️  Database file {db_path} doesn't exist (will be created on first run)")
        return True
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        if cursor.fetchone():
            print("✅ Database structure is ready")
        else:
            print("⚠️  Database exists but may need initialization")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

def check_file_structure():
    """Check if all required files exist"""
    print("\n🔍 Checking file structure...")
    
    required_files = [
        'main.py',
        'requirements.txt',
        '.env',
        'bot/__init__.py',
        'bot/database/__init__.py',
        'bot/database/db.py'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"❌ {file_path}")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files present")
    return True

async def test_bot_import():
    """Test if the bot can be imported and initialized"""
    print("\n🔍 Testing bot import and initialization...")
    
    try:
        # Test basic imports
        from telegram.ext import Application
        print("✅ Telegram imports successful")
        
        # Test bot token
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            print("❌ BOT_TOKEN not available")
            return False
        
        # Test application creation
        application = Application.builder().token(bot_token).build()
        print("✅ Application creation successful")
        
        # Test initialization
        await application.initialize()
        print("✅ Application initialization successful")
        
        # Clean shutdown
        await application.shutdown()
        print("✅ Application shutdown successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Bot import/initialization failed: {e}")
        return False

def main():
    """Run all deployment checks"""
    print("🚀 Running Final Deployment Verification\n")
    print("=" * 50)
    
    checks = [
        ("Environment Variables", check_environment),
        ("Dependencies", check_dependencies), 
        ("Database", check_database),
        ("File Structure", check_file_structure),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
        except Exception as e:
            print(f"❌ {check_name} check failed with error: {e}")
            all_passed = False
    
    # Async checks
    try:
        if not asyncio.run(test_bot_import()):
            all_passed = False
    except Exception as e:
        print(f"❌ Async bot check failed: {e}")
        all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 ALL CHECKS PASSED!")
        print("✅ Bot is ready for production deployment")
        print("\n🚀 Deploy with confidence!")
        print("📋 Next steps:")
        print("   1. Deploy to your hosting platform (Render, Railway, etc.)")
        print("   2. Set environment variables on the platform")
        print("   3. Monitor logs during first startup")
        print("   4. Test bot functionality after deployment")
        return True
    else:
        print("❌ SOME CHECKS FAILED!")
        print("🔧 Please fix the issues above before deploying")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
