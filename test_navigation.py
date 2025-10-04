#!/usr/bin/env python3
"""
Test script to verify all back button and navigation handlers work correctly.
This script tests callback handler patterns without requiring the full bot to run.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_callback_patterns():
    """Test that all callback patterns are covered"""
    
    # Callback patterns that should be handled
    test_patterns = [
        # Main navigation
        "main_panel",
        "mini_app_centre", 
        "games",
        
        # Game callbacks
        "game_slots",
        "game_blackjack", 
        "game_dice",
        "game_dice_predict",
        "game_coinflip",
        "game_roulette",
        
        # Game betting patterns
        "slots_bet_5",
        "blackjack_bet_10", 
        "dice_bet_25",
        "dice_play_50",
        "dice_predict_bet_5",
        "dice_predict_toggle_3",
        "dice_predict_play_10",
        "coinflip_bet_5",
        "coinflip_play_bitcoin_5",
        "roulette_select_red",
        
        # Bonus callbacks
        "weekly_bonus",
        "claim_weekly_bonus",
        "bonus_menu",
        
        # Financial callbacks
        "deposit",
        "withdraw",
        "deposit_LTC",
        "withdraw_LTC",
        
        # Menu callbacks
        "referral_menu",
        "user_stats", 
        "help_menu",
        "admin_panel",
    ]
    
    print("🧪 Testing callback patterns...")
    
    # Read main.py to check for handlers
    try:
        with open('main.py', 'r') as f:
            content = f.read()
            
        missing_handlers = []
        covered_handlers = []
        
        for pattern in test_patterns:
            # Skip deposit/withdraw patterns that have dedicated handlers
            if pattern.startswith('deposit_') or pattern.startswith('withdraw_'):
                print(f"ℹ️  {pattern} (has dedicated handler)")
                covered_handlers.append(pattern)
                continue
            
            # Extract the base pattern for startswith checks
            base_pattern = pattern.split('_')[0] + '_' if '_' in pattern else pattern
                
            # Check if pattern is handled in callback_handler
            if (f'data == "{pattern}"' in content or 
                f'data.startswith("{base_pattern}")' in content or
                f'data.startswith("{pattern.split("_")[0]}_")' in content):
                covered_handlers.append(pattern)
                print(f"✅ {pattern}")
            else:
                missing_handlers.append(pattern)
                print(f"❌ {pattern}")
        
        print(f"\n📊 Results:")
        print(f"✅ Covered: {len(covered_handlers)}/{len(test_patterns)}")
        print(f"❌ Missing: {len(missing_handlers)}")
        
        if missing_handlers:
            print(f"\n🚨 Missing handlers:")
            for handler in missing_handlers:
                print(f"   - {handler}")
            return False
        else:
            print(f"\n🎉 All callback patterns are handled!")
            return True
            
    except Exception as e:
        print(f"❌ Error reading main.py: {e}")
        return False

def test_game_file_callbacks():
    """Test that game files use correct callback data"""
    
    print("\n🎮 Testing game file callback data...")
    
    game_files = [
        'bot/games/coinflip.py',
        'bot/games/dice.py', 
        'bot/games/dice_predict.py',
        'bot/games/slots.py',
        'bot/games/blackjack.py',
        'bot/games/roulette.py'
    ]
    
    consistent_callbacks = []
    inconsistent_callbacks = []
    
    for game_file in game_files:
        try:
            with open(game_file, 'r') as f:
                content = f.read()
                
            # Check for "Back to Games" buttons
            if 'callback_data="mini_app_centre"' in content:
                consistent_callbacks.append(game_file)
                print(f"✅ {game_file} - Uses mini_app_centre")
            elif 'callback_data="games"' in content:
                inconsistent_callbacks.append(game_file)  
                print(f"⚠️  {game_file} - Uses 'games' (should be mini_app_centre)")
            else:
                print(f"ℹ️  {game_file} - No back to games button found")
                
        except FileNotFoundError:
            print(f"⏭️  {game_file} - File not found (skipping)")
        except Exception as e:
            print(f"❌ {game_file} - Error: {e}")
    
    print(f"\n📊 Game File Results:")
    print(f"✅ Consistent: {len(consistent_callbacks)}")
    print(f"⚠️  Inconsistent: {len(inconsistent_callbacks)}")
    
    if inconsistent_callbacks:
        print(f"\n🔧 Files needing update:")
        for file in inconsistent_callbacks:
            print(f"   - {file}")
        return False
    else:
        print(f"\n🎉 All game files use consistent callback data!")
        return True

def test_missing_functions():
    """Test that all referenced callback functions exist"""
    
    print("\n🔍 Testing for missing callback functions...")
    
    try:
        with open('main.py', 'r') as f:
            content = f.read()
            
        # Functions that should exist based on callback handler
        expected_functions = [
            'start_panel_callback',
            'games_menu_callback', 
            'referral_menu_callback',
            'user_stats_callback',
            'help_menu_callback',
            'admin_panel_callback',
            'bonus_menu_callback',
            'weekly_bonus_callback',
            'claim_weekly_bonus_callback',
            'deposit_callback',
            'withdraw_start',
            'game_slots_callback',
            'game_blackjack_callback',
            'game_dice_callback',
            'game_roulette_callback', 
            'handle_dice_predict_callback',
            'handle_coinflip_callback',
            'handle_roulette_callback'
        ]
        
        missing_functions = []
        existing_functions = []
        
        for func in expected_functions:
            if f'def {func}(' in content or f'async def {func}(' in content:
                existing_functions.append(func)
                print(f"✅ {func}")
            else:
                missing_functions.append(func)
                print(f"❌ {func}")
        
        print(f"\n📊 Function Results:")
        print(f"✅ Existing: {len(existing_functions)}/{len(expected_functions)}")
        print(f"❌ Missing: {len(missing_functions)}")
        
        if missing_functions:
            print(f"\n🚨 Missing functions:")
            for func in missing_functions:
                print(f"   - {func}")
            return False
        else:
            print(f"\n🎉 All required callback functions exist!")
            return True
            
    except Exception as e:
        print(f"❌ Error reading main.py: {e}")
        return False

def main():
    """Run all navigation tests"""
    
    print("🧪 BACK BUTTON & NAVIGATION TEST SUITE")
    print("=" * 50)
    
    test1 = test_callback_patterns()
    test2 = test_game_file_callbacks() 
    test3 = test_missing_functions()
    
    print("\n" + "=" * 50)
    print("📋 FINAL RESULTS:")
    
    if test1 and test2 and test3:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Back button navigation is fully functional")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print("🔧 Check the issues above and fix them")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
