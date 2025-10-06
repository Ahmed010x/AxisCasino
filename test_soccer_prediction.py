#!/usr/bin/env python3
"""
Test Soccer Prediction Logic
Debug the prediction matching issue
"""

# Test the soccer prediction logic
def test_soccer_prediction_logic():
    # Soccer game configuration
    soccer_config = {
        "name": "⚽ Soccer Prediction",
        "description": "Predict soccer emoji animation outcomes",
        "icon": "⚽",
        "options": ["miss", "bar", "goal"],
        "option_names": ["Miss", "Bar", "Goal"],
        "base_multiplier": 3.0,
        "min_selections": 1,
        "max_selections": 2
    }
    
    print("🧪 Testing Soccer Prediction Logic")
    print("=" * 50)
    
    # Test scenarios
    test_cases = [
        {
            "dice_value": 1,
            "expected_outcome": "miss",
            "player_selections": [0],  # Player selected "miss" (index 0)
            "should_win": True
        },
        {
            "dice_value": 2,
            "expected_outcome": "miss",
            "player_selections": [0],  # Player selected "miss" (index 0)
            "should_win": True
        },
        {
            "dice_value": 3,
            "expected_outcome": "bar",
            "player_selections": [1],  # Player selected "bar" (index 1)
            "should_win": True
        },
        {
            "dice_value": 4,
            "expected_outcome": "goal",
            "player_selections": [2],  # Player selected "goal" (index 2)
            "should_win": True
        },
        {
            "dice_value": 5,
            "expected_outcome": "goal",
            "player_selections": [2],  # Player selected "goal" (index 2)
            "should_win": True
        },
        {
            "dice_value": 3,
            "expected_outcome": "bar",
            "player_selections": [0, 2],  # Player selected "miss" and "goal" (indices 0, 2)
            "should_win": False  # Should lose because bar (index 1) is not in [0, 2]
        },
        {
            "dice_value": 4,
            "expected_outcome": "goal",
            "player_selections": [0, 2],  # Player selected "miss" and "goal" (indices 0, 2)
            "should_win": True   # Should win because goal (index 2) is in [0, 2]
        }
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\nTest Case {i+1}:")
        print(f"  Dice Value: {case['dice_value']}")
        print(f"  Expected Outcome: {case['expected_outcome']}")
        print(f"  Player Selections: {case['player_selections']} -> {[soccer_config['options'][idx] for idx in case['player_selections']]}")
        
        # Simulate the actual game logic
        dice_value = case['dice_value']
        
        # Map soccer dice values to outcomes (same as in the code)
        if dice_value in [1, 2]:
            outcome = "miss"
        elif dice_value == 3:
            outcome = "bar"
        elif dice_value in [4, 5]:
            outcome = "goal"
        else:
            outcome = "miss"  # fallback
        
        # Get outcome index
        outcome_index = soccer_config['options'].index(outcome)
        
        # Check if player won
        player_selections = case['player_selections']
        player_won = outcome_index in player_selections
        
        print(f"  Actual Outcome: {outcome} (index {outcome_index})")
        print(f"  Player Won: {player_won}")
        print(f"  Expected to Win: {case['should_win']}")
        
        if player_won == case['should_win']:
            print(f"  ✅ CORRECT")
        else:
            print(f"  ❌ INCORRECT - Logic Error Detected!")
            print(f"     Expected: {case['should_win']}, Got: {player_won}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_soccer_prediction_logic()
