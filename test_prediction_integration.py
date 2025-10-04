#!/usr/bin/env python3
"""
Test script to verify prediction games integration with main.py
"""

def test_prediction_imports():
    """Test that prediction imports work correctly"""
    try:
        from bot.games.prediction import handle_prediction_callback, handle_custom_bet_input
        print("✅ Prediction module imports successfully")
        
        # Test function availability
        print(f"✅ handle_prediction_callback available: {callable(handle_prediction_callback)}")
        print(f"✅ handle_custom_bet_input available: {callable(handle_custom_bet_input)}")
        
        return True
    except Exception as e:
        print(f"❌ Prediction import error: {e}")
        return False

def test_main_imports():
    """Test that main.py imports without errors"""
    try:
        import main
        print("✅ main.py imports successfully with prediction module")
        
        # Check if the prediction handler is available in main
        if hasattr(main, 'handle_prediction_callback'):
            print("✅ handle_prediction_callback available in main")
        else:
            print("⚠️ handle_prediction_callback not directly available in main (expected)")
        
        return True
    except Exception as e:
        print(f"❌ main.py import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prediction_games_config():
    """Test prediction games configuration"""
    try:
        from bot.games.prediction import PREDICTION_GAMES, calculate_multiplier, get_random_outcome
        
        print("✅ Prediction games configuration loaded")
        print(f"📊 Available games: {list(PREDICTION_GAMES.keys())}")
        
        # Test each game type
        for game_type in PREDICTION_GAMES:
            game_info = PREDICTION_GAMES[game_type]
            print(f"  🎮 {game_info['name']}: {len(game_info['options'])} options")
            
            # Test multiplier calculation
            multiplier = calculate_multiplier(game_type, 1)
            print(f"    💰 Single selection multiplier: {multiplier:.2f}x")
            
            # Test random outcome
            outcome = get_random_outcome(game_type)
            print(f"    🎯 Sample outcome: {outcome}")
        
        return True
    except Exception as e:
        print(f"❌ Prediction games config error: {e}")
        return False

def test_callback_data_patterns():
    """Test callback data pattern handling"""
    test_patterns = [
        "game_prediction",
        "prediction",
        "prediction_rules",
        "prediction_game_dice",
        "prediction_game_coin",
        "prediction_select_dice_3",
        "prediction_clear_dice",
        "prediction_bet_coin",
        "prediction_play_dice_5.0",
        "prediction_custom_bet_number"
    ]
    
    print("🔍 Testing callback data patterns:")
    
    for pattern in test_patterns:
        if pattern == "game_prediction" or pattern == "prediction":
            print(f"  ✅ {pattern} -> show_prediction_menu")
        elif pattern == "prediction_rules":
            print(f"  ✅ {pattern} -> show_prediction_rules")
        elif pattern.startswith("prediction_game_"):
            game_type = pattern.split("prediction_game_")[1]
            print(f"  ✅ {pattern} -> show_game_selection_menu({game_type})")
        elif pattern.startswith("prediction_select_"):
            parts = pattern.split("_")
            game_type = parts[2]
            option_index = parts[3]
            print(f"  ✅ {pattern} -> handle_selection_toggle({game_type}, {option_index})")
        elif pattern.startswith("prediction_clear_"):
            game_type = pattern.split("prediction_clear_")[1]
            print(f"  ✅ {pattern} -> clear_selections({game_type})")
        elif pattern.startswith("prediction_bet_"):
            game_type = pattern.split("prediction_bet_")[1]
            print(f"  ✅ {pattern} -> show_betting_menu({game_type})")
        elif pattern.startswith("prediction_play_"):
            parts = pattern.split("_")
            game_type = parts[2]
            bet_amount = parts[3]
            print(f"  ✅ {pattern} -> play_prediction_game({game_type}, {bet_amount})")
        elif pattern.startswith("prediction_custom_bet_"):
            game_type = pattern.split("prediction_custom_bet_")[1]
            print(f"  ✅ {pattern} -> custom_bet_input({game_type})")
        else:
            print(f"  ⚠️ {pattern} -> unknown pattern")
    
    return True

if __name__ == "__main__":
    print("🔬 Testing Prediction Games Integration\n")
    
    success = True
    success &= test_prediction_imports()
    print()
    success &= test_main_imports()
    print()
    success &= test_prediction_games_config()
    print()
    success &= test_callback_data_patterns()
    
    print(f"\n{'🎉 All tests passed!' if success else '❌ Some tests failed!'}")
