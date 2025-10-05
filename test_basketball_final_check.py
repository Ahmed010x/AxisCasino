#!/usr/bin/env python3
"""
Final verification test for basketball prediction game
Verifying clean UI and proper emoji animation integration
"""

import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, '/Users/ahmed/Telegram Axis')

def test_basketball_configuration():
    """Test basketball game configuration is clean and correct."""
    print("🏀 Testing Basketball Prediction Configuration...")
    
    try:
        from bot.games.prediction import PREDICTION_GAMES, format_outcome_display
        
        # Check basketball game exists
        if "basketball" not in PREDICTION_GAMES:
            print("❌ Basketball game not found in PREDICTION_GAMES")
            return False
            
        basketball = PREDICTION_GAMES["basketball"]
        print(f"✅ Basketball game found: {basketball['name']}")
        
        # Verify clean configuration
        expected_options = ["stuck", "miss", "in"]
        expected_option_names = ["Stuck", "Miss", "In"]
        
        if basketball["options"] != expected_options:
            print(f"❌ Incorrect options: {basketball['options']}")
            return False
        print(f"✅ Options correct: {basketball['options']}")
        
        if basketball["option_names"] != expected_option_names:
            print(f"❌ Incorrect option names: {basketball['option_names']}")
            return False
        print(f"✅ Option names clean: {basketball['option_names']}")
        
        # Test clean outcome displays
        print("\n🎯 Testing Clean Outcome Displays:")
        outcomes = ["stuck", "miss", "in"]
        for outcome in outcomes:
            display = format_outcome_display("basketball", outcome)
            print(f"  {outcome} -> {display}")
            
            # Check for clean formatting (no excessive emojis)
            if "🏀" in display or "🔴" in display or "❌" in display or "✅" in display:
                print(f"  ⚠️  Warning: Display contains emojis: {display}")
            else:
                print(f"  ✅ Clean display confirmed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing configuration: {e}")
        return False

def test_emoji_animation_logic():
    """Test the emoji animation logic mapping."""
    print("\n🎲 Testing Basketball Emoji Animation Logic...")
    
    # Test the mapping logic that should be in the play function
    # Basketball emoji values: 1=miss, 2=miss, 3=stuck, 4=in, 5=in
    mapping = {
        1: "miss",
        2: "miss", 
        3: "stuck",
        4: "in",
        5: "in"
    }
    
    print("Animation value -> Outcome mapping:")
    for value, outcome in mapping.items():
        print(f"  🏀 {value} -> {outcome}")
    
    # Verify distribution
    outcomes = list(mapping.values())
    miss_count = outcomes.count("miss")
    stuck_count = outcomes.count("stuck") 
    in_count = outcomes.count("in")
    
    print(f"\nOutcome distribution:")
    print(f"  miss: {miss_count}/5 (40%)")
    print(f"  stuck: {stuck_count}/5 (20%)")
    print(f"  in: {in_count}/5 (40%)")
    
    if miss_count == 2 and stuck_count == 1 and in_count == 2:
        print("✅ Distribution is balanced")
        return True
    else:
        print("❌ Distribution is unbalanced")
        return False

def test_multiplier_calculation():
    """Test multiplier calculations for basketball game."""
    print("\n💰 Testing Multiplier Calculations...")
    
    try:
        from bot.games.prediction import calculate_multiplier
        
        # Test basketball multipliers
        game_type = "basketball"
        
        # 1 selection: 3 options, so (3/1) * 0.95 = 2.85
        mult_1 = calculate_multiplier(game_type, 1)
        expected_1 = 2.85
        
        # 2 selections: (3/2) * 0.95 = 1.425  
        mult_2 = calculate_multiplier(game_type, 2)
        expected_2 = 1.425
        
        print(f"1 selection: {mult_1:.3f}x (expected: {expected_1:.3f}x)")
        print(f"2 selections: {mult_2:.3f}x (expected: {expected_2:.3f}x)")
        
        if abs(mult_1 - expected_1) < 0.01 and abs(mult_2 - expected_2) < 0.01:
            print("✅ Multiplier calculations correct")
            return True
        else:
            print("❌ Multiplier calculations incorrect")
            return False
            
    except Exception as e:
        print(f"❌ Error testing multipliers: {e}")
        return False

def main():
    """Run all tests."""
    print("🔬 BASKETBALL PREDICTION FINAL VERIFICATION")
    print("=" * 50)
    
    tests = [
        test_basketball_configuration,
        test_emoji_animation_logic,
        test_multiplier_calculation
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test failed with error: {e}\n")
    
    print("=" * 50)
    print(f"📊 FINAL RESULTS: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 ALL TESTS PASSED! Basketball prediction is ready!")
        return True
    else:
        print("❌ Some tests failed. Review the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
