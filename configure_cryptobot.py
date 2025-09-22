#!/usr/bin/env python3
"""
Quick CryptoBot API Configuration Script
This script helps you configure the CryptoBot API token for your casino bot.
"""

import os
import sys

def main():
    print("🔧 CryptoBot API Configuration Helper")
    print("=" * 50)
    print()
    
    # Check current status
    env_file = ".env"
    if not os.path.exists(env_file):
        print("❌ .env file not found!")
        print("Please create a .env file first.")
        return
    
    # Read current .env
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    # Check if token is already configured
    if "CRYPTOBOT_API_TOKEN=" in env_content and not env_content.find("CRYPTOBOT_API_TOKEN=") == -1:
        lines = env_content.split('\n')
        for line in lines:
            if line.startswith('CRYPTOBOT_API_TOKEN=') and not line.startswith('#'):
                if len(line.split('=', 1)[1].strip()) > 10:
                    print("✅ CryptoBot API token appears to be already configured!")
                    print("If you're still getting rate errors, the token might be invalid.")
                    print()
                    choice = input("Do you want to update it? (y/n): ").lower()
                    if choice != 'y':
                        return
                break
    
    print("📋 To get your CryptoBot API token:")
    print("1. Open Telegram and start @CryptoBot")
    print("2. Type: /api")
    print("3. Follow the prompts to create an API token")
    print("4. Copy the token (format: 1234:AAExxxxx...)")
    print()
    
    # Get token from user
    while True:
        token = input("Paste your CryptoBot API token here: ").strip()
        
        if not token:
            print("❌ Please enter a token")
            continue
            
        if ':' not in token or len(token) < 20:
            print("❌ Invalid token format. Should be like: 1234:AAExxxxxxxxxxxxx")
            continue
            
        break
    
    # Update .env file
    try:
        lines = env_content.split('\n')
        updated = False
        
        # Look for existing CRYPTOBOT_API_TOKEN line and update it
        for i, line in enumerate(lines):
            if 'CRYPTOBOT_API_TOKEN=' in line:
                lines[i] = f"CRYPTOBOT_API_TOKEN={token}"
                updated = True
                print(f"✅ Updated existing token configuration (line {i+1})")
                break
        
        # If not found, add it
        if not updated:
            lines.append(f"CRYPTOBOT_API_TOKEN={token}")
            print("✅ Added new token configuration")
        
        # Write back to file
        with open(env_file, 'w') as f:
            f.write('\n'.join(lines))
        
        print()
        print("🎉 Configuration complete!")
        print()
        print("Next steps:")
        print("1. Restart your casino bot")
        print("2. Test with /testcrypto command (owner only)")
        print("3. Try the deposit flow")
        print()
        print("Your bot should now be able to fetch live crypto rates!")
        
    except Exception as e:
        print(f"❌ Error updating .env file: {e}")

if __name__ == "__main__":
    main()
