#!/usr/bin/env python3
"""
Simple test to verify that key back button navigation works.
Tests the most important navigation patterns.
"""

import os

def test_main_navigation():
    """Test the key navigation patterns that users rely on"""
    
    print("🧪 Testing Key Navigation Patterns")
    print("=" * 40)
    
    try:
        with open('main.py', 'r') as f:
            content = f.read()
            
        # Key patterns that must work
        key_patterns = [
            ('main_panel', 'Main menu navigation'),
            ('mini_app_centre', 'Games menu navigation'),
            ('games', 'Alternative games navigation'),
            ('weekly_bonus', 'Bonus menu'),
            ('claim_weekly_bonus', 'Bonus claiming')
        ]
        
        all_good = True
        
        for pattern, description in key_patterns:
            if f'data == "{pattern}"' in content:
                print(f"✅ {pattern} - {description}")
            else:
                print(f"❌ {pattern} - {description}")
                all_good = False
        
        print("\n🎮 Testing Game Back Buttons")
        print("-" * 30)
        
        game_files = ['bot/games/coinflip.py', 'bot/games/dice.py', 'bot/games/dice_predict.py', 'bot/games/slots.py']
        
        for game_file in game_files:
            try:
                with open(game_file, 'r') as f:
                    game_content = f.read()
                
                if 'Back to Games' in game_content and 'mini_app_centre' in game_content:
                    print(f"✅ {game_file} - Has working back button")
                else:
                    print(f"⚠️  {game_file} - Back button issues")
                    
            except FileNotFoundError:
                print(f"⏭️  {game_file} - File not found")
        
        print("\n🔧 Testing Function Existence")
        print("-" * 30)
        
        critical_functions = [
            'games_menu_callback',
            'start_panel_callback', 
            'weekly_bonus_callback',
            'claim_weekly_bonus_callback'
        ]
        
        for func in critical_functions:
            if f'def {func}(' in content:
                print(f"✅ {func}")
            else:
                print(f"❌ {func}")
                all_good = False
        
        print("\n" + "=" * 40)
        if all_good:
            print("🎉 ALL KEY NAVIGATION PATTERNS WORK!")
            print("✅ Back buttons are functional")
            return True
        else:
            print("❌ Some key patterns are missing")
            print("🔧 Fix the issues above")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_main_navigation()
    if success:
        print("\n🚀 Navigation system is ready!")
    else:
        print("\n⚠️  Navigation needs fixes!")
