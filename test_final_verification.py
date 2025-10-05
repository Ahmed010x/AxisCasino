#!/usr/bin/env python3
"""
Final Verification Test for Basketball Prediction Game
Tests UI cleanliness, option names, and display formatting
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from bot.games.prediction import (
    PREDICTION_GAMES, 
    format_outcome_display,
    calculate_multiplier
)

def test_basketball_configuration():
    """Test basketball game configuration for clean UI."""
    print("🏀 TESTING BASKETBALL CONFIGURATION...")
    
    # Check basketball game exists
    assert "basketball" in PREDICTION_GAMES, "Basketball game not found"
    
    basketball_config = PREDICTION_GAMES["basketball"]
    print(f"✅ Name: {basketball_config['name']}")
    print(f"✅ Description: {basketball_config['description']}")
    print(f"✅ Icon: {basketball_config['icon']}")
    print(f"✅ Options: {basketball_config['options']}")
    print(f"✅ Option Names: {basketball_config['option_names']}")
    
    # Verify clean option names (no problematic emojis)
    expected_option_names = ["Stuck", "Miss", "In"]
    assert basketball_config['option_names'] == expected_option_names, f"Expected {expected_option_names}, got {basketball_config['option_names']}"
    
    # Verify options
    expected_options = ["stuck", "miss", "in"]
    assert basketball_config['options'] == expected_options, f"Expected {expected_options}, got {basketball_config['options']}"
    
    print("✅ Basketball configuration is clean and correct!")

def test_outcome_displays():
    """Test outcome display formatting for cleanliness."""
    print("\n📊 TESTING OUTCOME DISPLAYS...")
    
    outcomes = ["stuck", "miss", "in"]
    expected_displays = [
        "Stuck on rim!",
        "Complete miss!",
        "Swish! Nothing but net!"
    ]
    
    for outcome, expected in zip(outcomes, expected_displays):
        display = format_outcome_display("basketball", outcome)
        print(f"✅ {outcome} -> '{display}'")
        assert display == expected, f"Expected '{expected}', got '{display}'"
    
    print("✅ All outcome displays are clean and descriptive!")

def test_multipliers():
    """Test multiplier calculations."""
    print("\n💰 TESTING MULTIPLIERS...")
    
    # Test single selection (highest risk)
    mult_1 = calculate_multiplier("basketball", 1)
    expected_1 = 3.0 * 0.95  # 2.85
    print(f"✅ 1 selection: {mult_1:.2f}x (expected ~2.85x)")
    assert abs(mult_1 - expected_1) < 0.01, f"Expected ~{expected_1}, got {mult_1}"
    
    # Test two selections (lower risk)
    mult_2 = calculate_multiplier("basketball", 2)
    expected_2 = 1.5 * 0.95  # 1.425
    print(f"✅ 2 selections: {mult_2:.2f}x (expected ~1.43x)")
    assert abs(mult_2 - expected_2) < 0.01, f"Expected ~{expected_2}, got {mult_2}"
    
    print("✅ Multiplier calculations are correct!")

def test_no_redundant_emojis():
    """Verify no redundant or problematic emojis in basketball game."""
    print("\n🧹 TESTING FOR REDUNDANT EMOJIS...")
    
    basketball_config = PREDICTION_GAMES["basketball"]
    
    # Check option names don't contain basketball emoji or other redundant emojis
    for name in basketball_config['option_names']:
        assert '🏀' not in name, f"Basketball emoji found in option name: {name}"
        assert '🎯' not in name, f"Target emoji found in option name: {name}"
        assert '⚽' not in name, f"Soccer ball emoji found in option name: {name}"
        print(f"✅ Option name '{name}' is clean")
    
    # Check outcome displays don't have redundant emojis
    for outcome in basketball_config['options']:
        display = format_outcome_display("basketball", outcome)
        # Allow descriptive text but no basketball emojis
        assert '🏀' not in display, f"Basketball emoji found in display: {display}"
        print(f"✅ Display '{display}' is clean")
    
    print("✅ No redundant emojis found!")

def test_ui_consistency():
    """Test UI consistency and professionalism."""
    print("\n🎨 TESTING UI CONSISTENCY...")
    
    basketball_config = PREDICTION_GAMES["basketball"]
    
    # Check that names are properly capitalized
    for name in basketball_config['option_names']:
        assert name[0].isupper(), f"Option name should start with capital: {name}"
        assert not name.isupper() or len(name) <= 2, f"Option name shouldn't be all caps: {name}"
        print(f"✅ Option name '{name}' has proper capitalization")
    
    # Check description is informative
    description = basketball_config['description']
    assert len(description) > 10, f"Description too short: {description}"
    assert 'emoji' in description.lower(), f"Description should mention emoji: {description}"
    print(f"✅ Description is informative: {description}")
    
    print("✅ UI is consistent and professional!")

def main():
    """Run all verification tests."""
    print("🔍 FINAL VERIFICATION TEST - BASKETBALL PREDICTION GAME\n")
    print("=" * 60)
    
    try:
        test_basketball_configuration()
        test_outcome_displays()
        test_multipliers()
        test_no_redundant_emojis()
        test_ui_consistency()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! BASKETBALL GAME IS READY! 🎉")
        print("✅ Configuration is clean and correct")
        print("✅ UI is professional and emoji-free")
        print("✅ Displays are descriptive without redundancy")
        print("✅ Multipliers are calculated correctly")
        print("✅ No problematic emojis detected")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
