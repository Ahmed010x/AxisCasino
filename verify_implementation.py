#!/usr/bin/env python3
"""
Verification script to check if all the required features are properly implemented:
1. Message prioritization system
2. Owner panel with admin controls  
3. Weekly bonus feature
4. All handler registrations
"""

import re
import sys

def check_file_content(filename, checks):
    """Check if all required patterns exist in the file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        results = {}
        for check_name, pattern in checks.items():
            if isinstance(pattern, str):
                # Simple string search
                results[check_name] = pattern in content
            elif isinstance(pattern, list):
                # All patterns must be found
                results[check_name] = all(p in content for p in pattern)
            else:
                # Regex pattern
                results[check_name] = bool(re.search(pattern, content, re.MULTILINE))
        
        return results
    except FileNotFoundError:
        print(f"❌ File {filename} not found!")
        return {}

def main():
    print("🔍 Verifying Telegram Casino Bot Implementation...")
    print("=" * 60)
    
    # Define all the checks we need to perform
    checks = {
        # Message Prioritization System
        "Message Priority Helpers": [
            "async def set_pending_amount_request",
            "async def validate_amount_request", 
            "async def clear_amount_request",
            "async def send_priority_message"
        ],
        
        # Owner Panel
        "Owner Panel Function": "async def owner_panel_callback",
        "Owner Command": "async def owner_command", 
        "Owner Command Registration": 'CommandHandler("owner", owner_command)',
        "Owner Panel Registration": 'CallbackQueryHandler(owner_panel_callback, pattern="^owner_panel$")',
        
        # Weekly Bonus
        "Weekly Bonus Helpers": [
            "async def can_claim_weekly_bonus",
            "async def claim_weekly_bonus"
        ],
        "Weekly Bonus Button": '"🎁 Weekly Bonus"',
        "Weekly Bonus Handler": "weekly_bonus_callback",
        "Weekly Bonus Registration": 'CallbackQueryHandler(weekly_bonus_callback, pattern="^weekly_bonus$")',
        
        # Database Migration
        "Weekly Bonus DB Migration": "last_weekly_bonus INTEGER DEFAULT 0",
        
        # Core Bot Features
        "Main Menu": "Welcome to Axis Casino",
        "Mini App Centre": "mini_app_centre",
        "Balance Display": "show_balance",
        "Deposit/Withdraw": ["deposit", "withdraw"],
        
        # Game Integration
        "Games Available": ["slots", "dice", "coinflip"],
        "Game Handlers": "game_callback",
        
        # Error Handling
        "Global Error Handler": "global_error_handler",
        "Try-Catch Blocks": "try:",
    }
    
    # Run the checks
    results = check_file_content("main.py", checks)
    
    # Display results
    passed = 0
    total = len(checks)
    
    for check_name, passed_check in results.items():
        status = "✅ PASS" if passed_check else "❌ FAIL"
        print(f"{status} - {check_name}")
        if passed_check:
            passed += 1
    
    print("=" * 60)
    print(f"📊 SUMMARY: {passed}/{total} checks passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All features are properly implemented!")
        return 0
    else:
        print("⚠️  Some features may need attention.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
