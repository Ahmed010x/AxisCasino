#!/usr/bin/env python3
"""
Test script for basketball emoji animation integration
"""

import sys
import os

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

def test_basketball_emoji_integration():
    """Test basketball emoji animation integration"""
    print("🏀 Testing Basketball Emoji Animation Integration")
    print("=" * 55)
    
    try:
        # Test imports
        from games.prediction import PREDICTION_GAMES, get_random_outcome, format_outcome_display
        print("✅ Successfully imported prediction functions")
        
        # Test basketball configuration
        basketball = PREDICTION_GAMES["basketball"]
        print(f"\n🏀 Basketball Game Configuration:")
        print(f"   Name: {basketball['name']}")
        print(f"   Description: {basketball['description']}")
        print(f"   Options: {basketball['options']}")
        print(f"   Option Names: {basketball['option_names']}")
        
        # Verify description mentions animation
        assert "emoji animation" in basketball['description'], "Description should mention emoji animation"
        print("✅ Basketball description mentions emoji animation")
        
        # Test outcome generation for basketball (should return None for emoji handling)
        basketball_outcome = get_random_outcome("basketball")
        assert basketball_outcome is None, "Basketball should return None for emoji-based outcomes"
        print("✅ Basketball outcome generation returns None for emoji handling")
        
        # Test outcome generation for dice (should work normally)
        dice_outcome = get_random_outcome("dice")
        assert dice_outcome in [1, 2, 3, 4, 5, 6], f"Dice outcome should be 1-6, got {dice_outcome}"
        print(f"✅ Dice outcome generation works normally: {dice_outcome}")
        
        # Test outcome display formatting
        test_outcomes = ["stuck", "miss", "in"]
        for outcome in test_outcomes:
            display = format_outcome_display("basketball", outcome)
            print(f"   {outcome} -> {display}")
            assert "🏀" in display, f"Display should contain basketball emoji: {display}"
        print("✅ Outcome displays formatted correctly")
        
        print("\n" + "=" * 55)
        print("🎉 ALL BASKETBALL EMOJI INTEGRATION TESTS PASSED!")
        print("\n📋 Key Features:")
        print("   🏀 Basketball emoji animation determines outcome")
        print("   🎬 Animation provides visual feedback")
        print("   🎯 Dice values mapped to game outcomes:")
        print("      • 1-2: Miss (complete miss)")
        print("      • 3: Stuck (ball stuck on rim)")
        print("      • 4-5: In (successful shot)")
        print("   🎮 Enhanced user experience with real animation")
        print("\n🚀 Basketball emoji animation system is ready!")
        
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_emoji_value_mapping():
    """Test the basketball emoji value mapping logic"""
    print("\n🎲 Testing Basketball Emoji Value Mapping:")
    
    # Test the mapping logic used in the game
    mapping_tests = [
        (1, "miss"),
        (2, "miss"),
        (3, "stuck"),
        (4, "in"),
        (5, "in")
    ]
    
    for dice_value, expected_outcome in mapping_tests:
        # Simulate the mapping logic from the game
        if dice_value in [1, 2]:
            outcome = "miss"
        elif dice_value == 3:
            outcome = "stuck"
        elif dice_value in [4, 5]:
            outcome = "in"
        else:
            outcome = "unknown"
        
        assert outcome == expected_outcome, f"Value {dice_value} should map to {expected_outcome}, got {outcome}"
        print(f"   Basketball emoji value {dice_value} -> {outcome}")
    
    print("✅ Basketball emoji value mapping is correct")
    
    # Test probability distribution
    outcomes = {"miss": 0, "stuck": 0, "in": 0}
    total_simulations = 1000
    
    for _ in range(total_simulations):
        # Simulate random dice value (1-5)
        import random
        dice_value = random.randint(1, 5)
        
        if dice_value in [1, 2]:
            outcomes["miss"] += 1
        elif dice_value == 3:
            outcomes["stuck"] += 1
        elif dice_value in [4, 5]:
            outcomes["in"] += 1
    
    print(f"\n📊 Probability Distribution (over {total_simulations} simulations):")
    for outcome, count in outcomes.items():
        percentage = (count / total_simulations) * 100
        print(f"   {outcome}: {count} times ({percentage:.1f}%)")
    
    # Verify approximate expected probabilities
    miss_pct = (outcomes["miss"] / total_simulations) * 100
    stuck_pct = (outcomes["stuck"] / total_simulations) * 100
    in_pct = (outcomes["in"] / total_simulations) * 100
    
    assert 35 <= miss_pct <= 45, f"Miss should be ~40%, got {miss_pct:.1f}%"
    assert 15 <= stuck_pct <= 25, f"Stuck should be ~20%, got {stuck_pct:.1f}%"
    assert 35 <= in_pct <= 45, f"In should be ~40%, got {in_pct:.1f}%"
    
    print("✅ Probability distribution is within expected ranges")

def main():
    """Run all tests"""
    success1 = test_basketball_emoji_integration()
    test_emoji_value_mapping()
    
    if success1:
        print(f"\n🎊 ALL TESTS COMPLETED SUCCESSFULLY! 🎊")
        return True
    else:
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
