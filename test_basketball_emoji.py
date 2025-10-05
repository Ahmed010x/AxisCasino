#!/usr/bin/env python3
"""
Test script for the new basketball emoji prediction outcomes
"""

import sys
import os

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

# Test imports
try:
    from games.prediction import (
        PREDICTION_GAMES, 
        calculate_multiplier, 
        get_random_outcome, 
        format_outcome_display
    )
    print("✅ Successfully imported prediction game functions")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

def test_basketball_config():
    """Test basketball game configuration"""
    print("\n🏀 Testing Basketball Configuration:")
    
    basketball = PREDICTION_GAMES["basketball"]
    print(f"Name: {basketball['name']}")
    print(f"Description: {basketball['description']}")
    print(f"Options: {basketball['options']}")
    print(f"Option Names: {basketball['option_names']}")
    print(f"Base Multiplier: {basketball['base_multiplier']}")
    print(f"Max Selections: {basketball['max_selections']}")
    
    # Verify we have exactly 3 outcomes
    assert len(basketball['options']) == 3, f"Expected 3 options, got {len(basketball['options'])}"
    assert len(basketball['option_names']) == 3, f"Expected 3 option names, got {len(basketball['option_names'])}"
    
    # Verify the emoji outcomes
    expected_options = ["stuck", "miss", "in"]
    assert basketball['options'] == expected_options, f"Expected {expected_options}, got {basketball['options']}"
    
    expected_names = ["� Stuck", "❌ Miss", "✅ In"]
    assert basketball['option_names'] == expected_names, f"Expected {expected_names}, got {basketball['option_names']}"
    
    print("✅ Basketball configuration is correct")

def test_multipliers():
    """Test multiplier calculations for basketball"""
    print("\n📊 Testing Basketball Multipliers:")
    
    # Test single selection (highest risk)
    single_mult = calculate_multiplier("basketball", 1)
    print(f"1 selection: {single_mult:.2f}x")
    
    # Test two selections (lower risk)
    double_mult = calculate_multiplier("basketball", 2)
    print(f"2 selections: {double_mult:.2f}x")
    
    # Verify multipliers are reasonable
    assert 2.5 < single_mult < 3.0, f"Single selection multiplier should be ~2.85x, got {single_mult:.2f}x"
    assert 1.3 < double_mult < 1.5, f"Double selection multiplier should be ~1.43x, got {double_mult:.2f}x"
    
    print("✅ Multipliers are correct")

def test_random_outcomes():
    """Test random outcome generation"""
    print("\n🎲 Testing Random Outcomes:")
    
    outcomes = set()
    for i in range(100):
        outcome = get_random_outcome("basketball")
        outcomes.add(outcome)
    
    print(f"Generated outcomes: {sorted(outcomes)}")
    
    # Verify all possible outcomes can be generated
    expected_outcomes = {"stuck", "miss", "in"}
    assert outcomes == expected_outcomes, f"Expected {expected_outcomes}, got {outcomes}"
    
    print("✅ Random outcome generation is working")

def test_outcome_display():
    """Test outcome display formatting"""
    print("\n🎨 Testing Outcome Display:")
    
    outcomes = ["stuck", "miss", "in"]
    
    for outcome in outcomes:
        display = format_outcome_display("basketball", outcome)
        print(f"{outcome} -> {display}")
    
    # Test specific formats
    stuck_display = format_outcome_display("basketball", "stuck")
    miss_display = format_outcome_display("basketball", "miss")
    in_display = format_outcome_display("basketball", "in")
    
    assert "�" in stuck_display and "Stuck on rim" in stuck_display
    assert "❌" in miss_display and "Complete miss" in miss_display
    assert "✅" in in_display and "Swish" in in_display
    
    print("✅ Outcome display formatting is correct")

def main():
    """Run all tests"""
    print("🧪 Testing Basketball Emoji Prediction Changes")
    print("=" * 50)
    
    try:
        test_basketball_config()
        test_multipliers()
        test_random_outcomes()
        test_outcome_display()
        
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED!")
        print("\n🏀 Basketball prediction is now using emoji outcomes:")
        print("   🚫 Stuck - Ball gets stuck on the rim")
        print("   ❌ Miss - Complete miss of the basket")
        print("   ✅ In - Successful shot (swish!)")
        print("\n📊 Multipliers:")
        print(f"   1 selection: ~{calculate_multiplier('basketball', 1):.2f}x")
        print(f"   2 selections: ~{calculate_multiplier('basketball', 2):.2f}x")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
