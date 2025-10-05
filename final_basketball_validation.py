#!/usr/bin/env python3
"""
Final validation test for basketball emoji prediction
"""

import sys
import os

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

def final_validation():
    """Run final validation of basketball emoji prediction"""
    print("🏁 Final Validation of Basketball Emoji Prediction")
    print("=" * 50)
    
    try:
        # Test imports
        from games.prediction import PREDICTION_GAMES, calculate_multiplier, get_random_outcome, format_outcome_display
        print("✅ All imports successful")
        
        # Validate basketball configuration
        basketball = PREDICTION_GAMES["basketball"]
        assert basketball["options"] == ["stuck", "miss", "in"]
        assert len(basketball["option_names"]) == 3
        assert basketball["base_multiplier"] == 3.0
        print("✅ Basketball configuration validated")
        
        # Test multiplier calculations
        single_mult = calculate_multiplier("basketball", 1)
        double_mult = calculate_multiplier("basketball", 2)
        assert abs(single_mult - 2.85) < 0.01, f"Single multiplier should be ~2.85, got {single_mult}"
        assert abs(double_mult - 1.42) < 0.05, f"Double multiplier should be ~1.42, got {double_mult}"
        print(f"✅ Multipliers validated: 1 sel = {single_mult:.2f}x, 2 sel = {double_mult:.2f}x")
        
        # Test random outcomes
        outcomes = set()
        for _ in range(50):
            outcome = get_random_outcome("basketball")
            outcomes.add(outcome)
        assert outcomes == {"stuck", "miss", "in"}, f"All outcomes should be generated, got {outcomes}"
        print("✅ Random outcome generation validated")
        
        # Test outcome displays
        displays = {}
        for outcome in ["stuck", "miss", "in"]:
            display = format_outcome_display("basketball", outcome)
            displays[outcome] = display
            assert "🏀" in display, f"Display should contain basketball emoji: {display}"
        
        print("✅ Outcome displays validated:")
        for outcome, display in displays.items():
            print(f"   {outcome}: {display}")
        
        print("\n" + "=" * 50)
        print("🎉 FINAL VALIDATION PASSED!")
        print("\n🏀 Basketball Emoji Prediction Summary:")
        print("   🔴 Stuck - Ball gets stuck on the rim")
        print("   ❌ Miss - Complete miss of the basket") 
        print("   ✅ In - Successful shot (swish!)")
        print(f"\n📊 Payout Structure:")
        print(f"   Single prediction: {single_mult:.2f}x multiplier")
        print(f"   Double prediction: {double_mult:.2f}x multiplier")
        print("\n🚀 System ready for deployment!")
        
    except Exception as e:
        print(f"❌ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = final_validation()
    sys.exit(0 if success else 1)
