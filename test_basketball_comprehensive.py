#!/usr/bin/env python3
"""
Comprehensive test for basketball emoji prediction integration
"""

import sys
import os

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

# Test main module integration
try:
    import main
    print("✅ Successfully imported main module")
except ImportError as e:
    print(f"❌ Main module import failed: {e}")
    sys.exit(1)

# Test prediction module
try:
    from games.prediction import PREDICTION_GAMES, handle_prediction_callback
    print("✅ Successfully imported prediction functions")
except ImportError as e:
    print(f"❌ Prediction module import failed: {e}")
    sys.exit(1)

def test_game_availability():
    """Test that both dice and basketball games are available"""
    print("\n🎮 Testing Game Availability:")
    
    available_games = list(PREDICTION_GAMES.keys())
    print(f"Available games: {available_games}")
    
    assert "dice" in available_games, "Dice game should be available"
    assert "basketball" in available_games, "Basketball game should be available"
    assert len(available_games) == 2, f"Should have exactly 2 games, got {len(available_games)}"
    
    print("✅ Both dice and basketball games are available")

def test_basketball_emoji_outcomes():
    """Test basketball emoji-based outcomes"""
    print("\n🏀 Testing Basketball Emoji Outcomes:")
    
    basketball = PREDICTION_GAMES["basketball"]
    
    # Verify the emoji outcomes
    print(f"Basketball options: {basketball['options']}")
    print(f"Basketball option names: {basketball['option_names']}")
    
    # Check that we have exactly 3 emoji-based outcomes
    assert basketball['options'] == ["stuck", "miss", "in"], "Basketball should have emoji-based outcomes"
    assert len(basketball['options']) == 3, "Basketball should have exactly 3 outcomes"
    
    # Check multipliers are appropriate for 3 outcomes
    base_mult = basketball['base_multiplier']
    assert base_mult == 3.0, f"Basketball base multiplier should be 3.0, got {base_mult}"
    
    print("✅ Basketball is using correct emoji outcomes")

def test_prediction_rules_content():
    """Test that prediction rules reflect the new basketball format"""
    print("\n📚 Testing Prediction Rules Content:")
    
    # Import the rules function
    from games.prediction import show_prediction_rules
    
    # Read the rules content from the source (since we can't easily call the async function)
    import inspect
    rules_source = inspect.getsource(show_prediction_rules)
    
    # Check that rules mention the new basketball format
    assert "3 outcomes" in rules_source, "Rules should mention 3 outcomes for basketball"
    assert "Stuck" in rules_source, "Rules should mention Stuck outcome"
    assert "Miss" in rules_source, "Rules should mention Miss outcome"
    assert "successful shot" in rules_source, "Rules should mention successful shot"
    
    print("✅ Prediction rules reflect the new basketball format")

def simulate_basketball_gameplay():
    """Simulate basketball gameplay scenarios"""
    print("\n🎲 Simulating Basketball Gameplay:")
    
    from games.prediction import get_random_outcome, format_outcome_display, calculate_multiplier
    
    # Test 100 games to ensure all outcomes can occur
    outcomes = {"stuck": 0, "miss": 0, "in": 0}
    
    for _ in range(100):
        outcome = get_random_outcome("basketball")
        outcomes[outcome] += 1
        
        # Test outcome display
        display = format_outcome_display("basketball", outcome)
        assert "🏀" in display, f"Display should include basketball emoji: {display}"
    
    print(f"Outcome distribution over 100 games: {outcomes}")
    
    # Verify all outcomes occurred
    for outcome in ["stuck", "miss", "in"]:
        assert outcomes[outcome] > 0, f"Outcome '{outcome}' should occur at least once in 100 games"
    
    # Test multiplier calculations
    single_mult = calculate_multiplier("basketball", 1)
    double_mult = calculate_multiplier("basketball", 2)
    
    print(f"Single selection multiplier: {single_mult:.2f}x")
    print(f"Double selection multiplier: {double_mult:.2f}x")
    
    # Verify multipliers make sense
    assert single_mult > double_mult, "Single selection should have higher multiplier"
    assert 2.5 < single_mult < 3.0, "Single selection multiplier should be around 2.85x"
    assert 1.3 < double_mult < 1.5, "Double selection multiplier should be around 1.42x"
    
    print("✅ Basketball gameplay simulation successful")

def main():
    """Run comprehensive tests"""
    print("🧪 Comprehensive Basketball Emoji Prediction Test")
    print("=" * 55)
    
    try:
        test_game_availability()
        test_basketball_emoji_outcomes()
        test_prediction_rules_content()
        simulate_basketball_gameplay()
        
        print("\n" + "=" * 55)
        print("🎉 ALL COMPREHENSIVE TESTS PASSED!")
        print("\n📋 Summary of Changes:")
        print("   • Basketball prediction now uses emoji outcomes")
        print("   • 3 outcomes: Stuck (🔴), Miss (❌), In (✅)")
        print("   • Multipliers adjusted for 3-outcome system")
        print("   • Rules updated to reflect new format")
        print("   • All integration points working correctly")
        print("\n🚀 The basketball emoji prediction system is ready!")
        
    except Exception as e:
        print(f"\n❌ COMPREHENSIVE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
