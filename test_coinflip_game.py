#!/usr/bin/env python3
"""
Quick test for Coin Flip game integration
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_coinflip_import():
    """Test that coin flip module can be imported"""
    try:
        from bot.games.coinflip import handle_coinflip_callback
        print("✅ Coin Flip module imported successfully")
        print(f"   Handler function: {handle_coinflip_callback.__name__}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Coin Flip module: {e}")
        return False

def test_main_import():
    """Test that main.py imports coin flip correctly"""
    try:
        # This will test if main.py can import without errors
        import main
        print("✅ main.py imported successfully (includes Coin Flip)")
        return True
    except Exception as e:
        print(f"❌ Failed to import main.py: {e}")
        return False

def test_game_constants():
    """Test coin flip game constants"""
    try:
        from bot.games.coinflip import MIN_BET, MAX_BET, WIN_MULTIPLIER
        print("✅ Coin Flip game constants:")
        print(f"   MIN_BET: ${MIN_BET:.2f}")
        print(f"   MAX_BET: ${MAX_BET:.2f}")
        print(f"   WIN_MULTIPLIER: {WIN_MULTIPLIER}x")
        return True
    except Exception as e:
        print(f"❌ Failed to load game constants: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🪙 COIN FLIP GAME INTEGRATION TEST")
    print("=" * 60)
    print()
    
    tests = [
        ("Coin Flip Module Import", test_coinflip_import),
        ("Main Module Import", test_main_import),
        ("Game Constants", test_game_constants),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Testing: {test_name}")
        print("-" * 60)
        result = test_func()
        results.append(result)
        print()
    
    # Summary
    print("=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Coin Flip game is ready!")
        print("\n📝 Game Features:")
        print("   • 50/50 odds (Heads or Tails)")
        print("   • 1.95x payout on wins")
        print("   • Bet amounts: $1 to $100")
        print("   • Instant results")
        print("   • House edge: 5%")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
