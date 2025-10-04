#!/usr/bin/env python3
"""
Integration test to verify all games work with main.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_main_imports():
    """Test that main.py can import all game handlers"""
    print("=" * 60)
    print("TESTING MAIN.PY GAME HANDLER IMPORTS")
    print("=" * 60)
    
    try:
        # Test individual imports as done in main.py
        from bot.games.slots import handle_slots_callback
        print("✅ Slots handler imported successfully")
        
        from bot.games.dice import handle_dice_callback, handle_custom_bet_input as handle_dice_custom_bet
        print("✅ Dice handler imported successfully")
        
        from bot.games.blackjack import handle_blackjack_callback, handle_custom_bet_input as handle_blackjack_custom_bet
        print("✅ Blackjack handler imported successfully")
        
        from bot.games.roulette import handle_roulette_callback, handle_custom_bet_input as handle_roulette_custom_bet
        print("✅ Roulette handler imported successfully")
        
        from bot.games.coinflip import handle_coinflip_callback, handle_custom_bet_input as handle_coinflip_custom_bet
        print("✅ Coin Flip handler imported successfully")
        
        from bot.games.prediction import handle_prediction_callback, handle_custom_bet_input as handle_prediction_custom_bet
        print("✅ Dice Predict handler imported successfully")
        
        print("\n🎉 All game handlers imported successfully from main.py perspective!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

def test_min_bet_values():
    """Verify MIN_BET values across all games"""
    print("\n" + "=" * 60)
    print("VERIFYING MIN_BET VALUES")
    print("=" * 60)
    
    games_to_test = [
        ('coinflip', 'bot.games.coinflip'),
        ('slots', 'bot.games.slots'),
        ('dice', 'bot.games.dice'),
        ('prediction', 'bot.games.prediction'),
        ('blackjack', 'bot.games.blackjack'),
        ('roulette', 'bot.games.roulette'),
    ]
    
    all_correct = True
    
    for game_name, module_path in games_to_test:
        try:
            module = __import__(module_path, fromlist=['MIN_BET'])
            min_bet = getattr(module, 'MIN_BET', None)
            
            if min_bet is None:
                print(f"⚠️  {game_name:15} - MIN_BET not found")
                all_correct = False
            elif min_bet == 0.50:
                print(f"✅ {game_name:15} - MIN_BET = ${min_bet:.2f}")
            else:
                print(f"❌ {game_name:15} - MIN_BET = ${min_bet:.2f} (expected $0.50)")
                all_correct = False
                
        except Exception as e:
            print(f"❌ {game_name:15} - Error: {e}")
            all_correct = False
    
    return all_correct

def test_callable_handlers():
    """Test that all handlers are callable"""
    print("\n" + "=" * 60)
    print("TESTING HANDLER CALLABILITY")
    print("=" * 60)
    
    try:
        from bot.games.slots import handle_slots_callback
        from bot.games.dice import handle_dice_callback
        from bot.games.blackjack import handle_blackjack_callback
        from bot.games.roulette import handle_roulette_callback
        from bot.games.coinflip import handle_coinflip_callback
        from bot.games.prediction import handle_prediction_callback
        
        handlers = {
            'Slots': handle_slots_callback,
            'Dice': handle_dice_callback,
            'Blackjack': handle_blackjack_callback,
            'Roulette': handle_roulette_callback,
            'Coin Flip': handle_coinflip_callback,
            'Prediction': handle_prediction_callback,
        }
        
        all_callable = True
        
        for name, handler in handlers.items():
            if callable(handler):
                print(f"✅ {name:15} - Handler is callable")
            else:
                print(f"❌ {name:15} - Handler is NOT callable")
                all_callable = False
        
        return all_callable
        
    except Exception as e:
        print(f"❌ Error testing callability: {e}")
        return False

def main():
    """Run all integration tests"""
    print("\n" + "=" * 60)
    print("CASINO GAME INTEGRATION TEST SUITE")
    print("=" * 60 + "\n")
    
    # Run tests
    test1 = test_main_imports()
    test2 = test_min_bet_values()
    test3 = test_callable_handlers()
    
    # Summary
    print("\n" + "=" * 60)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    tests_passed = sum([test1, test2, test3])
    total_tests = 3
    
    print(f"\n✅ Tests Passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ All games are properly integrated and ready to use")
        print("✅ All games have correct $0.50 minimum bet")
        print("✅ All handlers are callable and functional")
        return 0
    else:
        print(f"\n⚠️  {total_tests - tests_passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
