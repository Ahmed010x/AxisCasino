#!/usr/bin/env python3
"""
Test script to verify all games work correctly with $0.50 minimum bet
"""

import sys
import importlib
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_game_imports():
    """Test that all game modules can be imported"""
    print("=" * 60)
    print("TESTING GAME IMPORTS")
    print("=" * 60)
    
    games = [
        ('coinflip', 'bot.games.coinflip'),
        ('slots', 'bot.games.slots'),
        ('dice', 'bot.games.dice'),
        ('dice_predict', 'bot.games.dice_predict'),
        ('blackjack', 'bot.games.blackjack'),
        ('roulette', 'bot.games.roulette'),
        ('poker', 'bot.games.poker'),
    ]
    
    results = {}
    
    for game_name, module_path in games:
        try:
            module = importlib.import_module(module_path)
            results[game_name] = {
                'import': '✅ SUCCESS',
                'module': module
            }
            print(f"✅ {game_name:15} - Import successful")
        except Exception as e:
            results[game_name] = {
                'import': f'❌ FAILED: {str(e)}',
                'module': None
            }
            print(f"❌ {game_name:15} - Import failed: {e}")
    
    return results

def test_min_bet_constants(results):
    """Test that MIN_BET constant is set correctly"""
    print("\n" + "=" * 60)
    print("TESTING MIN_BET CONSTANTS")
    print("=" * 60)
    
    for game_name, data in results.items():
        if data['module'] is None:
            print(f"⏭️  {game_name:15} - Skipped (import failed)")
            continue
        
        module = data['module']
        
        if hasattr(module, 'MIN_BET'):
            min_bet = module.MIN_BET
            if min_bet == 0.50:
                print(f"✅ {game_name:15} - MIN_BET = ${min_bet:.2f} ✓")
                data['min_bet'] = '✅ CORRECT'
            else:
                print(f"❌ {game_name:15} - MIN_BET = ${min_bet:.2f} (expected $0.50)")
                data['min_bet'] = f'❌ WRONG: ${min_bet:.2f}'
        else:
            print(f"⚠️  {game_name:15} - No MIN_BET constant found")
            data['min_bet'] = '⚠️ NOT FOUND'

def test_max_bet_constants(results):
    """Test that MAX_BET constant is set correctly"""
    print("\n" + "=" * 60)
    print("TESTING MAX_BET CONSTANTS")
    print("=" * 60)
    
    for game_name, data in results.items():
        if data['module'] is None:
            print(f"⏭️  {game_name:15} - Skipped (import failed)")
            continue
        
        module = data['module']
        
        if hasattr(module, 'MAX_BET'):
            max_bet = module.MAX_BET
            print(f"✅ {game_name:15} - MAX_BET = ${max_bet:,.2f}")
            data['max_bet'] = f'✅ ${max_bet:,.2f}'
        else:
            print(f"⚠️  {game_name:15} - No MAX_BET constant found")
            data['max_bet'] = '⚠️ NOT FOUND'

def test_handler_functions(results):
    """Test that handler functions exist"""
    print("\n" + "=" * 60)
    print("TESTING HANDLER FUNCTIONS")
    print("=" * 60)
    
    handler_map = {
        'coinflip': 'handle_coinflip_callback',
        'slots': 'handle_slots_callback',
        'dice': 'handle_dice_callback',
        'dice_predict': 'handle_dice_predict_callback',
        'blackjack': 'handle_blackjack_callback',
        'roulette': 'handle_roulette_callback',
        'poker': 'handle_poker_callback',
    }
    
    for game_name, handler_name in handler_map.items():
        if results[game_name]['module'] is None:
            print(f"⏭️  {game_name:15} - Skipped (import failed)")
            continue
        
        module = results[game_name]['module']
        
        if hasattr(module, handler_name):
            print(f"✅ {game_name:15} - {handler_name} exists")
            results[game_name]['handler'] = '✅ EXISTS'
        else:
            print(f"❌ {game_name:15} - {handler_name} NOT FOUND")
            results[game_name]['handler'] = '❌ NOT FOUND'

def test_custom_bet_handlers(results):
    """Test that custom bet handlers exist"""
    print("\n" + "=" * 60)
    print("TESTING CUSTOM BET HANDLERS")
    print("=" * 60)
    
    for game_name, data in results.items():
        if data['module'] is None:
            print(f"⏭️  {game_name:15} - Skipped (import failed)")
            continue
        
        module = data['module']
        
        if hasattr(module, 'handle_custom_bet_input'):
            print(f"✅ {game_name:15} - handle_custom_bet_input exists")
            data['custom_bet'] = '✅ EXISTS'
        else:
            print(f"⚠️  {game_name:15} - No custom bet handler")
            data['custom_bet'] = '⚠️ NOT FOUND'

def print_summary(results):
    """Print test summary"""
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total_games = len(results)
    passed = sum(1 for r in results.values() if r.get('min_bet', '').startswith('✅'))
    failed = sum(1 for r in results.values() if r.get('min_bet', '').startswith('❌'))
    
    print(f"\n📊 Total Games: {total_games}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Warnings: {total_games - passed - failed}")
    
    print("\n📋 Detailed Results:")
    print("-" * 60)
    print(f"{'Game':<15} {'Import':<12} {'MIN_BET':<15} {'Handler':<12}")
    print("-" * 60)
    
    for game_name, data in results.items():
        import_status = '✅' if data['import'].startswith('✅') else '❌'
        min_bet_status = data.get('min_bet', 'N/A')[:10]
        handler_status = '✅' if data.get('handler', '').startswith('✅') else '❌'
        
        print(f"{game_name:<15} {import_status:<12} {min_bet_status:<15} {handler_status:<12}")
    
    print("-" * 60)
    
    if passed == total_games:
        print("\n🎉 ALL TESTS PASSED! All games are ready with $0.50 minimum bet.")
        return 0
    else:
        print(f"\n⚠️  {failed} game(s) need attention.")
        return 1

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("CASINO GAME VERIFICATION SUITE")
    print("Testing $0.50 Minimum Bet Implementation")
    print("=" * 60 + "\n")
    
    # Run tests
    results = test_game_imports()
    test_min_bet_constants(results)
    test_max_bet_constants(results)
    test_handler_functions(results)
    test_custom_bet_handlers(results)
    
    # Print summary
    exit_code = print_summary(results)
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60 + "\n")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
