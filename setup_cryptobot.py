#!/usr/bin/env python3
"""
CryptoBot API Setup Helper
This script helps you configure the CryptoBot API token for the casino bot.
"""

import os
import sys
from dotenv import load_dotenv

def main():
    print("🔧 CryptoBot API Setup Helper")
    print("=" * 50)
    
    # Load current environment
    load_dotenv()
    current_token = os.environ.get('CRYPTOBOT_API_TOKEN')
    
    if current_token:
        print(f"✅ Current CRYPTOBOT_API_TOKEN: {current_token[:10]}...")
        print(f"   Token length: {len(current_token)} characters")
        
        # Test the token
        print("\n🧪 Testing current token...")
        # We can't easily test async functions here, so just show instructions
        print("   Run '/testcrypto' command in your bot to test the API connection.")
    else:
        print("❌ CRYPTOBOT_API_TOKEN is not configured")
    
    print("\n📋 **HOW TO GET CRYPTOBOT API TOKEN:**")
    print("1. Open Telegram and find @CryptoBot")
    print("2. Send /start to begin")
    print("3. Go to Bot API section")
    print("4. Create new API token")
    print("5. Copy the token (format: 1234:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw)")
    
    print("\n⚙️ **HOW TO CONFIGURE:**")
    print("1. Edit your .env file")
    print("2. Add this line:")
    print("   CRYPTOBOT_API_TOKEN=your_token_here")
    print("3. Restart the bot")
    
    print("\n🔧 **OPTIONAL ENVIRONMENT VARIABLES:**")
    print("CRYPTOBOT_WEBHOOK_SECRET=your_webhook_secret")
    print("MIN_DEPOSIT_LTC_USD=1.00")
    print("MIN_DEPOSIT_TON_USD=2.50") 
    print("MIN_DEPOSIT_SOL_USD=1.15")
    print("MIN_DEPOSIT_USDT_USD=1.00")
    
    # Check .env file exists
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"\n✅ {env_file} file exists")
        
        # Offer to add token interactively
        token = input("\n💡 Enter your CryptoBot API token (or press Enter to skip): ").strip()
        
        if token:
            # Read current .env content
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            # Check if CRYPTOBOT_API_TOKEN already exists
            token_exists = False
            for i, line in enumerate(lines):
                if line.startswith('CRYPTOBOT_API_TOKEN='):
                    lines[i] = f'CRYPTOBOT_API_TOKEN={token}\n'
                    token_exists = True
                    break
            
            # Add token if not exists
            if not token_exists:
                lines.append(f'CRYPTOBOT_API_TOKEN={token}\n')
            
            # Write back to file
            with open(env_file, 'w') as f:
                f.writelines(lines)
            
            print(f"✅ Token added to {env_file}")
            print("🔄 Please restart the bot for changes to take effect")
        else:
            print("⏭️ Skipped token configuration")
    else:
        print(f"\n⚠️ {env_file} file not found")
        print("   You may need to copy .env.example to .env first")
    
    print("\n🚀 **TESTING:**")
    print("After configuring the token:")
    print("1. Restart your bot")
    print("2. Use /testcrypto command (owner only)")
    print("3. Try making a test deposit")
    
    print("\n📞 **SUPPORT:**")
    print("If you need help, check the documentation or contact support.")

if __name__ == "__main__":
    main()
