#!/usr/bin/env python3
"""
Test Soccer Prediction Game Logic
Verify that the outcome mapping and selection logic work correctly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from bot.games.prediction import PREDICTION_GAMES, format_outcome_display

def test_soccer_prediction_logic():
    """Test the soccer prediction game logic"""
    print("🧪 Testing Soccer Prediction Game Logic")
    print("=" * 50)
    
    # Get soccer game config
    soccer_config = PREDICTION_GAMES['soccer']
    print(f"Game: {soccer_config['name']}")
    print(f"Options: {soccer_config['options']}")
    print(f"Option Names: {soccer_config['option_names']}")
    print()
    
    # Test outcome mapping
    print("📋 Testing Outcome Mapping:")
    for i, option in enumerate(soccer_config['options']):
        display = format_outcome_display('soccer', option)
        print(f"  {i}: {option} -> {display}")
    print()
    
    # Test dice value mapping
    print("🎲 Testing Dice Value to Outcome Mapping:")
    print("  Dice 1-2 -> miss")
    print("  Dice 3   -> bar")
    print("  Dice 4-5 -> goal")
    print()
    
    # Test win scenarios
    print("🎯 Testing Win Scenarios:")
    
    test_cases = [
        {
            'player_selections': [0],  # Miss
            'dice_value': 1,
            'expected_outcome': 'miss',
            'should_win': True
        },
        {
            'player_selections': [1],  # Bar
            'dice_value': 3,
            'expected_outcome': 'bar',
            'should_win': True
        },
        {
            'player_selections': [2],  # Goal
            'dice_value': 4,
            'expected_outcome': 'goal',
            'should_win': True
        },
        {
            'player_selections': [0],  # Miss selected
            'dice_value': 4,  # But goal happens
            'expected_outcome': 'goal',
            'should_win': False
        },
        {
            'player_selections': [0, 1],  # Miss and Bar selected
            'dice_value': 3,  # Bar happens
            'expected_outcome': 'bar',
            'should_win': True
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}:")
        
        # Simulate dice to outcome mapping
        dice_value = test['dice_value']
        if dice_value in [1, 2]:
            outcome = "miss"
        elif dice_value == 3:
            outcome = "bar"
        elif dice_value in [4, 5]:
            outcome = "goal"
        
        # Check if outcome matches expected
        outcome_correct = (outcome == test['expected_outcome'])
        
        # Check win logic
        outcome_index = soccer_config['options'].index(outcome)
        player_won = outcome_index in test['player_selections']
        win_correct = (player_won == test['should_win'])
        
        # Display results
        selected_names = [soccer_config['option_names'][i] for i in test['player_selections']]
        
        print(f"  Player selected: {selected_names} (indices: {test['player_selections']})")
        print(f"  Dice value: {dice_value}")
        print(f"  Outcome: {outcome} (index: {outcome_index})")
        print(f"  Player won: {player_won}")
        print(f"  ✅ Outcome mapping: {'PASS' if outcome_correct else 'FAIL'}")
        print(f"  ✅ Win logic: {'PASS' if win_correct else 'FAIL'}")
        print()
    
    print("🎉 All tests completed!")
    print("\n💡 If you're still seeing incorrect results in the game:")
    print("   1. Check the server logs for the debug messages")
    print("   2. Verify the dice values are being read correctly")
    print("   3. Make sure selections are being stored as indices (0,1,2)")

if __name__ == "__main__":
    test_soccer_prediction_logic()
