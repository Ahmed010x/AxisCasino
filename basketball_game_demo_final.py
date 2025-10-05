#!/usr/bin/env python3
"""
Basketball Prediction Game Demo
Shows the clean UI and emoji animation integration
"""

import sys
import os
import random

# Add the project directory to the Python path
sys.path.insert(0, '/Users/ahmed/Telegram Axis')

def demonstrate_basketball_game():
    """Demonstrate the basketball prediction game functionality."""
    print("🏀 BASKETBALL PREDICTION GAME DEMO")
    print("=" * 50)
    
    try:
        from bot.games.prediction import PREDICTION_GAMES, format_outcome_display, calculate_multiplier
        
        basketball = PREDICTION_GAMES["basketball"]
        
        print(f"🎮 Game: {basketball['name']}")
        print(f"📝 Description: {basketball['description']}")
        print(f"🎯 Options: {basketball['options']}")
        print(f"📋 Option Names: {basketball['option_names']}")
        print()
        
        # Show multipliers
        print("💰 MULTIPLIER TABLE:")
        for selections in range(1, 3):
            mult = calculate_multiplier("basketball", selections)
            print(f"  {selections} selection(s): {mult:.3f}x")
        print()
        
        # Show clean outcome displays
        print("🎯 CLEAN OUTCOME DISPLAYS:")
        for outcome in basketball['options']:
            display = format_outcome_display("basketball", outcome)
            print(f"  {outcome.upper()}: {display}")
        print()
        
        # Simulate emoji animation results
        print("🏀 EMOJI ANIMATION SIMULATION:")
        print("Basketball emoji animation values (1-5) map to outcomes:")
        
        mapping = {
            1: "miss",
            2: "miss", 
            3: "stuck",
            4: "in",
            5: "in"
        }
        
        for value in range(1, 6):
            outcome = mapping[value]
            display = format_outcome_display("basketball", outcome)
            print(f"  Animation value {value} → {outcome.upper()}: {display}")
        print()
        
        # Show sample games
        print("🎲 SAMPLE GAMES:")
        for i in range(3):
            print(f"\nGame {i+1}:")
            
            # Random player selection
            num_selections = random.randint(1, 2)
            if num_selections == 1:
                selections = [random.randint(0, 2)]
            else:
                selections = random.sample(range(3), 2)
            
            selected_options = [basketball['options'][j] for j in selections]
            selected_names = [basketball['option_names'][j] for j in selections]
            
            # Simulate animation result
            animation_value = random.randint(1, 5)
            outcome = mapping[animation_value]
            outcome_display = format_outcome_display("basketball", outcome)
            
            # Check if won
            won = outcome in selected_options
            multiplier = calculate_multiplier("basketball", len(selections))
            
            print(f"  🎯 Player predicted: {', '.join(selected_names)}")
            print(f"  🏀 Animation value: {animation_value}")
            print(f"  📊 Actual outcome: {outcome_display}")
            print(f"  💰 Multiplier: {multiplier:.3f}x")
            print(f"  🏆 Result: {'WIN! 🎉' if won else 'LOSS 💔'}")
        
        print("\n" + "=" * 50)
        print("✅ Demo completed successfully!")
        print("🎮 The basketball prediction game is clean and ready!")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()

def show_ui_improvements():
    """Show the UI improvements made."""
    print("\n🎨 UI IMPROVEMENTS SUMMARY:")
    print("=" * 50)
    
    print("✅ BEFORE vs AFTER Comparison:")
    print("\nBEFORE (messy with excessive emojis):")
    print("  Options: ['🔴 Stuck', '❌ Miss', '✅ In']")
    print("  Displays: '🏀 🔴 Stuck on rim!', '🏀 ❌ Complete miss!'")
    
    print("\nAFTER (clean and professional):")
    print("  Options: ['Stuck', 'Miss', 'In']") 
    print("  Displays: 'Stuck on rim!', 'Complete miss!', 'Swish! Nothing but net!'")
    
    print("\n✨ Key improvements:")
    print("  • Removed redundant emojis from option names")
    print("  • Cleaned up outcome displays") 
    print("  • Fixed encoding issues")
    print("  • Made UI more professional and readable")
    print("  • Maintained emoji animation integration for outcome determination")

def main():
    """Run the demo."""
    demonstrate_basketball_game()
    show_ui_improvements()

if __name__ == "__main__":
    main()
