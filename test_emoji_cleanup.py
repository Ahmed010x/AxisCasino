#!/usr/bin/env python3
"""
Test script to verify cleaned up emoji displays in basketball prediction
"""

import sys
import os

# Add the bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

def test_cleaned_emoji_displays():
    """Test that emoji displays have been cleaned up"""
    print("🧹 Testing Cleaned Up Emoji Displays")
    print("=" * 40)
    
    try:
        from games.prediction import PREDICTION_GAMES, format_outcome_display
        
        basketball = PREDICTION_GAMES["basketball"]
        
        print("🏀 Basketball Configuration:")
        print(f"   Name: {basketball['name']}")
        print(f"   Description: {basketball['description']}")
        print(f"   Options: {basketball['options']}")
        print(f"   Option Names: {basketball['option_names']}")
        
        # Test that option names are clean (no problematic emojis)
        option_names = basketball['option_names']
        expected_names = ["Stuck", "Miss", "In"]
        assert option_names == expected_names, f"Expected {expected_names}, got {option_names}"
        print("✅ Option names are clean and simple")
        
        # Test outcome displays are clean
        print(f"\n📋 Outcome Displays:")
        outcomes = ["stuck", "miss", "in"]
        for outcome in outcomes:
            display = format_outcome_display("basketball", outcome)
            print(f"   {outcome}: '{display}'")
            
            # Verify no redundant basketball emojis in outcome displays
            assert not display.startswith("🏀"), f"Display should not start with basketball emoji: {display}"
            
            # Verify displays are descriptive but clean
            if outcome == "stuck":
                assert "Stuck on rim" in display
            elif outcome == "miss":
                assert "Complete miss" in display
            elif outcome == "in":
                assert "Swish" in display
        
        print("✅ Outcome displays are clean (no redundant emojis)")
        
        # Test that emoji displays are still descriptive
        print(f"\n🎯 Verification - Displays are still descriptive:")
        stuck_display = format_outcome_display("basketball", "stuck")
        miss_display = format_outcome_display("basketball", "miss")
        in_display = format_outcome_display("basketball", "in")
        
        assert "rim" in stuck_display.lower(), "Stuck display should mention rim"
        assert "miss" in miss_display.lower(), "Miss display should mention miss"
        assert "swish" in in_display.lower() or "net" in in_display.lower(), "In display should mention swish or net"
        
        print("✅ Displays remain descriptive and clear")
        
        print(f"\n📊 Summary of Changes:")
        print("• Removed redundant basketball emojis from outcome displays")
        print("• Simplified option names (no problematic emoji encoding)")
        print("• Cleaned up result message formatting")
        print("• Maintained descriptive text for clarity")
        print("• Basketball emoji animation still determines outcome")
        
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_display_formatting():
    """Test that display formatting is clean and consistent"""
    print(f"\n🎨 Testing Display Formatting:")
    
    try:
        from games.prediction import format_outcome_display
        
        # Test all game types for consistency
        dice_display = format_outcome_display("dice", 3)
        basketball_stuck = format_outcome_display("basketball", "stuck")
        basketball_miss = format_outcome_display("basketball", "miss")
        basketball_in = format_outcome_display("basketball", "in")
        
        print(f"Dice display: '{dice_display}'")
        print(f"Basketball stuck: '{basketball_stuck}'")
        print(f"Basketball miss: '{basketball_miss}'")
        print(f"Basketball in: '{basketball_in}'")
        
        # Verify dice still has emoji (for consistency)
        assert "🎲" in dice_display, "Dice should still have dice emoji"
        
        # Verify basketball displays are clean but descriptive
        basketball_displays = [basketball_stuck, basketball_miss, basketball_in]
        for display in basketball_displays:
            # Should not have basketball emoji at start (since animation shows it)
            assert not display.startswith("🏀"), f"Basketball display should not start with emoji: {display}"
            # Should still be descriptive
            assert len(display) > 5, f"Display should be descriptive: {display}"
        
        print("✅ Display formatting is consistent and clean")
        return True
        
    except Exception as e:
        print(f"❌ FORMATTING TEST FAILED: {e}")
        return False

def main():
    """Run all cleanup verification tests"""
    success1 = test_cleaned_emoji_displays()
    success2 = test_display_formatting()
    
    if success1 and success2:
        print(f"\n🎉 ALL CLEANUP TESTS PASSED!")
        print(f"\n✨ Basketball prediction displays are now:")
        print("• Clean and simple")
        print("• Free of redundant emojis")
        print("• Still descriptive and clear")
        print("• Focused on the animated emoji for visual appeal")
        return True
    else:
        print(f"\n❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
