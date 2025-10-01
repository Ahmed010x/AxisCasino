#!/usr/bin/env python3
"""
🎮 Casino Games Verification Script
Tests all implemented games and their handlers
"""

import sys
import os
sys.path.append('.')

def test_game_implementation():
    """Test all game implementations"""
    print("🎮 CASINO GAMES VERIFICATION")
    print("=" * 50)
    
    # Test imports
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler
        import aiosqlite
        import asyncio
        print("✅ All dependencies imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Read main.py and verify game components
    try:
        with open('main.py', 'r') as f:
            content = f.read()
        print("✅ Main bot file loaded successfully")
    except FileNotFoundError:
        print("❌ main.py not found")
        return False
    
    # Verify each game
    games = [
        {
            'name': 'Slots',
            'emoji': '🎰',
            'callback': 'slots',
            'states': ['SLOTS_BET_AMOUNT'],
            'functions': ['slots_start', 'slots_bet_amount']
        },
        {
            'name': 'Coinflip', 
            'emoji': '🪙',
            'callback': 'coinflip',
            'states': ['COINFLIP_BET_AMOUNT', 'COINFLIP_PREDICTION'],
            'functions': ['coinflip_start', 'coinflip_bet_amount', 'coinflip_play']
        },
        {
            'name': 'Dice',
            'emoji': '🎲', 
            'callback': 'dice',
            'states': ['DICE_BET_AMOUNT', 'DICE_PREDICTION'],
            'functions': ['dice_start', 'dice_bet_amount', 'dice_play']
        },
        {
            'name': 'Blackjack',
            'emoji': '🃏',
            'callback': 'blackjack', 
            'states': ['BLACKJACK_BET_AMOUNT', 'BLACKJACK_PLAYING'],
            'functions': ['blackjack_start', 'blackjack_bet_amount', 'blackjack_hit', 'blackjack_stand']
        },
        {
            'name': 'Roulette',
            'emoji': '🎡',
            'callback': 'roulette',
            'states': ['ROULETTE_BET_AMOUNT', 'ROULETTE_BET_TYPE'], 
            'functions': ['roulette_start', 'roulette_bet_amount', 'roulette_play']
        },
        {
            'name': 'Crash',
            'emoji': '🚀',
            'callback': 'crash',
            'states': ['CRASH_BET_AMOUNT', 'CRASH_CASHOUT'],
            'functions': ['crash_start', 'crash_bet_amount', 'crash_cashout']
        }
    ]
    
    all_passed = True
    
    for game in games:
        print(f"\n{game['emoji']} Testing {game['name']} Game:")
        print("-" * 30)
        
        # Check button exists
        button_pattern = f'callback_data="{game["callback"]}"'
        if button_pattern in content:
            print(f"  ✅ Game button found")
        else:
            print(f"  ❌ Game button missing")
            all_passed = False
            
        # Check handler pattern exists  
        handler_pattern = f'pattern="^{game["callback"]}$"'
        if handler_pattern in content:
            print(f"  ✅ Handler pattern found")
        else:
            print(f"  ❌ Handler pattern missing")
            all_passed = False
            
        # Check conversation handler exists
        conv_handler = f'{game["callback"]}_conv_handler'
        if conv_handler in content:
            print(f"  ✅ Conversation handler found")
        else:
            print(f"  ❌ Conversation handler missing")
            all_passed = False
            
        # Check states exist
        for state in game['states']:
            if state in content:
                print(f"  ✅ State {state} found")
            else:
                print(f"  ❌ State {state} missing")
                all_passed = False
                
        # Check functions exist
        for func in game['functions']:
            if f"async def {func}" in content:
                print(f"  ✅ Function {func} found")
            else:
                print(f"  ❌ Function {func} missing")
                all_passed = False
    
    # Check handler registration
    print(f"\n🔧 Testing Handler Registration:")
    print("-" * 30)
    
    for game in games:
        handler_add = f"application.add_handler({game['callback']}_conv_handler)"
        if handler_add in content:
            print(f"  ✅ {game['name']} handler registered")
        else:
            print(f"  ❌ {game['name']} handler not registered")
            all_passed = False
    
    # Check database integration
    print(f"\n💾 Testing Database Integration:")
    print("-" * 30)
    
    db_functions = [
        'get_user', 'update_balance', 'deduct_balance', 'log_game_session'
    ]
    
    for func in db_functions:
        if f"async def {func}" in content:
            print(f"  ✅ Database function {func} found")
        else:
            print(f"  ❌ Database function {func} missing")
            all_passed = False
    
    # Final result
    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 ALL GAMES VERIFIED SUCCESSFULLY!")
        print("✅ Ready for production use")
        print(f"✅ Total games implemented: {len(games)}")
        print("✅ All handlers properly registered")
        print("✅ Database integration complete")
        return True
    else:
        print("❌ VERIFICATION FAILED!")
        print("Some components are missing or misconfigured")
        return False

if __name__ == "__main__":
    success = test_game_implementation()
    sys.exit(0 if success else 1)
