#!/usr/bin/env python3
"""
Debug Soccer Prediction Game
Create a comprehensive test to debug the actual issue
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import the game modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

async def debug_soccer_prediction():
    """Debug the soccer prediction game with detailed logging"""
    print("🐛 Debug Soccer Prediction Game")
    print("=" * 60)
    
    # Import the actual game functions
    from bot.games.prediction import PREDICTION_GAMES, calculate_multiplier, format_outcome_display
    
    # Test configuration
    game_type = "soccer"
    game_info = PREDICTION_GAMES[game_type]
    bet_amount = 10.0
    
    print(f"Game Type: {game_type}")
    print(f"Game Info: {game_info}")
    print(f"Bet Amount: ${bet_amount}")
    print()
    
    # Test scenarios
    scenarios = [
        {
            "name": "Player picks GOAL, dice shows 4 (GOAL)",
            "player_selections": [2],  # goal = index 2
            "dice_value": 4,
            "expected_outcome": "goal",
            "should_win": True
        },
        {
            "name": "Player picks GOAL, dice shows 3 (BAR)",
            "player_selections": [2],  # goal = index 2
            "dice_value": 3,
            "expected_outcome": "bar",
            "should_win": False
        },
        {
            "name": "Player picks BAR, dice shows 3 (BAR)",
            "player_selections": [1],  # bar = index 1
            "dice_value": 3,
            "expected_outcome": "bar",
            "should_win": True
        },
        {
            "name": "Player picks MISS + GOAL, dice shows 4 (GOAL)",
            "player_selections": [0, 2],  # miss=0, goal=2
            "dice_value": 4,
            "expected_outcome": "goal",
            "should_win": True
        },
        {
            "name": "Player picks MISS + GOAL, dice shows 3 (BAR)",
            "player_selections": [0, 2],  # miss=0, goal=2
            "dice_value": 3,
            "expected_outcome": "bar",
            "should_win": False
        }
    ]
    
    for i, scenario in enumerate(scenarios):
        print(f"\n--- Scenario {i+1}: {scenario['name']} ---")
        
        player_selections = scenario['player_selections']
        dice_value = scenario['dice_value']
        
        print(f"Player Selections: {player_selections}")
        print(f"Selected Options: {[game_info['options'][idx] for idx in player_selections]}")
        print(f"Dice Value: {dice_value}")
        
        # Map dice value to outcome (copied from actual game code)
        if dice_value in [1, 2]:
            outcome = "miss"
        elif dice_value == 3:
            outcome = "bar"
        elif dice_value in [4, 5]:
            outcome = "goal"
        else:
            outcome = "miss"  # fallback
        
        print(f"Determined Outcome: {outcome}")
        print(f"Expected Outcome: {scenario['expected_outcome']}")
        
        # Get outcome index (copied from actual game code)
        outcome_index = game_info['options'].index(outcome)
        print(f"Outcome Index: {outcome_index}")
        
        # Check if player won (copied from actual game code)
        player_won = outcome_index in player_selections
        print(f"Player Won: {player_won}")
        print(f"Should Win: {scenario['should_win']}")
        
        # Calculate winnings
        if player_won:
            multiplier = calculate_multiplier(game_type, len(player_selections))
            win_amount = bet_amount * multiplier
            net_profit = win_amount - bet_amount  # This should be the actual profit
            
            print(f"Multiplier: {multiplier:.2f}x")
            print(f"Win Amount: ${win_amount:.2f}")
            print(f"Net Profit: ${net_profit:.2f}")
            
            # Balance calculation (mimicking the actual game)
            initial_balance = 100.0  # Example
            after_bet_deduction = initial_balance - bet_amount
            final_balance = after_bet_deduction + win_amount
            
            print(f"Initial Balance: ${initial_balance:.2f}")
            print(f"After Bet Deduction: ${after_bet_deduction:.2f}")
            print(f"Final Balance: ${final_balance:.2f}")
            print(f"Actual Profit: ${final_balance - initial_balance:.2f}")
        else:
            print(f"No winnings - player lost ${bet_amount:.2f}")
        
        # Verify correctness
        if player_won == scenario['should_win']:
            print("✅ CORRECT LOGIC")
        else:
            print("❌ INCORRECT LOGIC!")
            print(f"  Expected: {scenario['should_win']}")
            print(f"  Got: {player_won}")
        
        print("-" * 50)
    
    print("\n🔍 Potential Issues to Check:")
    print("1. Are you sure you're selecting the right option before playing?")
    print("2. Are you watching the soccer emoji animation to see the actual result?")
    print("3. Is there a display issue where the result message doesn't match the logic?")
    print("4. Are there any house balance integration issues?")
    print("5. Is the dice animation result matching what the code determines?")

if __name__ == "__main__":
    asyncio.run(debug_soccer_prediction())
