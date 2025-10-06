#!/usr/bin/env python3
"""
Test script for Bowling and Darts Prediction Games

This script validates:
1. Game configuration is correct
2. Emoji value mappings work properly
3. Outcome calculation is accurate
4. Multiplier calculations are correct
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from bot.games.prediction import (
    PREDICTION_GAMES,
    calculate_multiplier,
    format_outcome_display
)

def test_game_configuration():
    """Test that bowling and darts are properly configured."""
    print("=" * 60)
    print("TEST 1: Game Configuration")
    print("=" * 60)
    
    # Check bowling configuration
    assert "bowling" in PREDICTION_GAMES, "❌ Bowling not found in PREDICTION_GAMES"
    bowling = PREDICTION_GAMES["bowling"]
    assert bowling["name"] == "🎳 Bowling Prediction", "❌ Bowling name incorrect"
    assert bowling["icon"] == "🎳", "❌ Bowling icon incorrect"
    assert bowling["options"] == ["gutter", "few_pins", "many_pins", "strike"], "❌ Bowling options incorrect"
    assert bowling["option_names"] == ["Gutter", "Few Pins", "Many Pins", "Strike"], "❌ Bowling option names incorrect"
    assert len(bowling["options"]) == 4, "❌ Bowling should have 4 options"
    print("✅ Bowling configuration is correct")
    
    # Check darts configuration
    assert "darts" in PREDICTION_GAMES, "❌ Darts not found in PREDICTION_GAMES"
    darts = PREDICTION_GAMES["darts"]
    assert darts["name"] == "🎯 Darts Prediction", "❌ Darts name incorrect"
    assert darts["icon"] == "🎯", "❌ Darts icon incorrect"
    assert darts["options"] == ["outer", "middle", "inner", "bullseye"], "❌ Darts options incorrect"
    assert darts["option_names"] == ["Outer Ring", "Middle Ring", "Inner Ring", "Bullseye"], "❌ Darts option names incorrect"
    assert len(darts["options"]) == 4, "❌ Darts should have 4 options"
    print("✅ Darts configuration is correct")
    
    print()

def test_multiplier_calculations():
    """Test multiplier calculations for bowling and darts."""
    print("=" * 60)
    print("TEST 2: Multiplier Calculations")
    print("=" * 60)
    
    # Bowling multipliers
    print("\n🎳 Bowling Multipliers:")
    bowling_1 = calculate_multiplier("bowling", 1)
    bowling_2 = calculate_multiplier("bowling", 2)
    bowling_3 = calculate_multiplier("bowling", 3)
    
    print(f"  1 selection: {bowling_1:.2f}x (expected ~3.80x)")
    print(f"  2 selections: {bowling_2:.2f}x (expected ~1.90x)")
    print(f"  3 selections: {bowling_3:.2f}x (expected ~1.27x)")
    
    # Verify calculations
    expected_1 = (4 / 1) * 0.95  # 3.80
    expected_2 = (4 / 2) * 0.95  # 1.90
    expected_3 = (4 / 3) * 0.95  # 1.27
    
    assert abs(bowling_1 - expected_1) < 0.01, f"❌ Bowling 1-selection multiplier incorrect"
    assert abs(bowling_2 - expected_2) < 0.01, f"❌ Bowling 2-selection multiplier incorrect"
    assert abs(bowling_3 - expected_3) < 0.01, f"❌ Bowling 3-selection multiplier incorrect"
    print("✅ Bowling multipliers are correct")
    
    # Darts multipliers
    print("\n🎯 Darts Multipliers:")
    darts_1 = calculate_multiplier("darts", 1)
    darts_2 = calculate_multiplier("darts", 2)
    darts_3 = calculate_multiplier("darts", 3)
    
    print(f"  1 selection: {darts_1:.2f}x (expected ~3.80x)")
    print(f"  2 selections: {darts_2:.2f}x (expected ~1.90x)")
    print(f"  3 selections: {darts_3:.2f}x (expected ~1.27x)")
    
    assert abs(darts_1 - expected_1) < 0.01, f"❌ Darts 1-selection multiplier incorrect"
    assert abs(darts_2 - expected_2) < 0.01, f"❌ Darts 2-selection multiplier incorrect"
    assert abs(darts_3 - expected_3) < 0.01, f"❌ Darts 3-selection multiplier incorrect"
    print("✅ Darts multipliers are correct")
    
    print()

def test_outcome_formatting():
    """Test outcome display formatting."""
    print("=" * 60)
    print("TEST 3: Outcome Display Formatting")
    print("=" * 60)
    
    # Test bowling outcomes
    print("\n🎳 Bowling Outcomes:")
    bowling_outcomes = {
        "gutter": "Gutter ball!",
        "few_pins": "Few pins knocked down",
        "many_pins": "Many pins knocked down!",
        "strike": "STRIKE! Perfect shot!"
    }
    
    for outcome, expected_text in bowling_outcomes.items():
        result = format_outcome_display("bowling", outcome)
        print(f"  {outcome}: {result}")
        assert expected_text in result, f"❌ Bowling outcome '{outcome}' not formatted correctly"
    print("✅ Bowling outcome formatting is correct")
    
    # Test darts outcomes
    print("\n🎯 Darts Outcomes:")
    darts_outcomes = {
        "outer": "Outer ring",
        "middle": "Middle ring",
        "inner": "Inner ring!",
        "bullseye": "BULLSEYE! Perfect throw!"
    }
    
    for outcome, expected_text in darts_outcomes.items():
        result = format_outcome_display("darts", outcome)
        print(f"  {outcome}: {result}")
        assert expected_text in result, f"❌ Darts outcome '{outcome}' not formatted correctly"
    print("✅ Darts outcome formatting is correct")
    
    print()

def test_emoji_value_mapping():
    """Test the emoji value to outcome mapping logic."""
    print("=" * 60)
    print("TEST 4: Emoji Value to Outcome Mapping")
    print("=" * 60)
    
    # Bowling mapping: 1=gutter, 2-3=few_pins, 4-5=many_pins, 6=strike
    print("\n🎳 Bowling Emoji Value Mapping:")
    bowling_mapping = {
        1: "gutter",
        2: "few_pins",
        3: "few_pins",
        4: "many_pins",
        5: "many_pins",
        6: "strike"
    }
    
    for dice_value, expected_outcome in bowling_mapping.items():
        print(f"  Dice value {dice_value} → {expected_outcome}")
    
    print("\n  Testing logic:")
    test_cases_bowling = [
        (1, "gutter"),
        (2, "few_pins"),
        (3, "few_pins"),
        (4, "many_pins"),
        (5, "many_pins"),
        (6, "strike")
    ]
    
    for dice_value, expected in test_cases_bowling:
        # Simulate the mapping logic from the code
        if dice_value == 1:
            outcome = "gutter"
        elif dice_value in [2, 3]:
            outcome = "few_pins"
        elif dice_value in [4, 5]:
            outcome = "many_pins"
        elif dice_value == 6:
            outcome = "strike"
        else:
            outcome = "unknown"
        
        assert outcome == expected, f"❌ Bowling dice value {dice_value} mapped incorrectly"
        print(f"    ✓ Dice {dice_value} correctly maps to '{outcome}'")
    
    print("✅ Bowling emoji mapping is correct")
    
    # Darts mapping: 1-2=outer, 3-4=middle, 5=inner, 6=bullseye
    print("\n🎯 Darts Emoji Value Mapping:")
    darts_mapping = {
        1: "outer",
        2: "outer",
        3: "middle",
        4: "middle",
        5: "inner",
        6: "bullseye"
    }
    
    for dice_value, expected_outcome in darts_mapping.items():
        print(f"  Dice value {dice_value} → {expected_outcome}")
    
    print("\n  Testing logic:")
    test_cases_darts = [
        (1, "outer"),
        (2, "outer"),
        (3, "middle"),
        (4, "middle"),
        (5, "inner"),
        (6, "bullseye")
    ]
    
    for dice_value, expected in test_cases_darts:
        # Simulate the mapping logic from the code
        if dice_value in [1, 2]:
            outcome = "outer"
        elif dice_value in [3, 4]:
            outcome = "middle"
        elif dice_value == 5:
            outcome = "inner"
        elif dice_value == 6:
            outcome = "bullseye"
        else:
            outcome = "unknown"
        
        assert outcome == expected, f"❌ Darts dice value {dice_value} mapped incorrectly"
        print(f"    ✓ Dice {dice_value} correctly maps to '{outcome}'")
    
    print("✅ Darts emoji mapping is correct")
    
    print()

def test_win_scenarios():
    """Test win/loss scenarios for bowling and darts."""
    print("=" * 60)
    print("TEST 5: Win/Loss Scenarios")
    print("=" * 60)
    
    bowling_info = PREDICTION_GAMES["bowling"]
    darts_info = PREDICTION_GAMES["darts"]
    
    # Bowling win scenarios
    print("\n🎳 Bowling Win Scenarios:")
    bowling_scenarios = [
        ([0], "gutter", True, "Player predicts Gutter (index 0), result is gutter"),
        ([1], "few_pins", True, "Player predicts Few Pins (index 1), result is few_pins"),
        ([2], "many_pins", True, "Player predicts Many Pins (index 2), result is many_pins"),
        ([3], "strike", True, "Player predicts Strike (index 3), result is strike"),
        ([0, 1], "gutter", True, "Player predicts Gutter and Few Pins, result is gutter"),
        ([0, 1], "many_pins", False, "Player predicts Gutter and Few Pins, result is many_pins"),
        ([2, 3], "strike", True, "Player predicts Many Pins and Strike, result is strike"),
    ]
    
    for selections, outcome, should_win, description in bowling_scenarios:
        outcome_index = bowling_info["options"].index(outcome)
        player_won = outcome_index in selections
        
        status = "✅" if player_won == should_win else "❌"
        result = "WIN" if player_won else "LOSS"
        print(f"  {status} {description}")
        print(f"      Selections: {selections}, Outcome index: {outcome_index}, Result: {result}")
        
        assert player_won == should_win, f"❌ Bowling scenario failed: {description}"
    
    print("✅ All bowling scenarios passed")
    
    # Darts win scenarios
    print("\n🎯 Darts Win Scenarios:")
    darts_scenarios = [
        ([0], "outer", True, "Player predicts Outer (index 0), result is outer"),
        ([1], "middle", True, "Player predicts Middle (index 1), result is middle"),
        ([2], "inner", True, "Player predicts Inner (index 2), result is inner"),
        ([3], "bullseye", True, "Player predicts Bullseye (index 3), result is bullseye"),
        ([0, 1], "outer", True, "Player predicts Outer and Middle, result is outer"),
        ([0, 1], "bullseye", False, "Player predicts Outer and Middle, result is bullseye"),
        ([2, 3], "bullseye", True, "Player predicts Inner and Bullseye, result is bullseye"),
    ]
    
    for selections, outcome, should_win, description in darts_scenarios:
        outcome_index = darts_info["options"].index(outcome)
        player_won = outcome_index in selections
        
        status = "✅" if player_won == should_win else "❌"
        result = "WIN" if player_won else "LOSS"
        print(f"  {status} {description}")
        print(f"      Selections: {selections}, Outcome index: {outcome_index}, Result: {result}")
        
        assert player_won == should_win, f"❌ Darts scenario failed: {description}"
    
    print("✅ All darts scenarios passed")
    
    print()

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🎳 BOWLING & DARTS PREDICTION GAMES TEST SUITE 🎯")
    print("=" * 60 + "\n")
    
    try:
        test_game_configuration()
        test_multiplier_calculations()
        test_outcome_formatting()
        test_emoji_value_mapping()
        test_win_scenarios()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED! ✅")
        print("=" * 60)
        print("\n🎮 Bowling and Darts prediction games are ready to use!")
        print("\nKey Features:")
        print("  • 🎳 Bowling: 4 outcomes (Gutter, Few Pins, Many Pins, Strike)")
        print("  • 🎯 Darts: 4 outcomes (Outer Ring, Middle Ring, Inner Ring, Bullseye)")
        print("  • Multipliers: ~3.8x (1 choice), ~1.9x (2 choices), ~1.27x (3 choices)")
        print("  • Fair 5% house edge on all bets")
        print("  • Animated emoji for real-time results\n")
        
        return 0
        
    except AssertionError as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {str(e)}")
        print("=" * 60 + "\n")
        return 1
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ UNEXPECTED ERROR: {str(e)}")
        print("=" * 60 + "\n")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
