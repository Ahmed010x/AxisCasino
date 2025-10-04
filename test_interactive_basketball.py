#!/usr/bin/env python3
"""
Test script for the interactive basketball game using emoji animations.
"""

import asyncio
import sys
import os

# Add the main directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.games.basketball import play_basketball_1v1_interactive, get_shot_result, send_basketball_emoji

def test_shot_results():
    """Test the shot result logic."""
    print("🏀 Testing shot result logic...")
    
    # Test all possible dice values
    for dice_value in range(1, 6):
        points, desc, emoji = get_shot_result(dice_value)
        print(f"  Dice {dice_value}: {points} points, {desc} {emoji}")
    
    print("✅ Shot result logic test passed!\n")

async def test_interactive_game_logic():
    """Test the interactive game logic (without actual Telegram calls)."""
    print("🏀 Testing interactive basketball game logic...")
    
    # Test game with simulated dice rolls
    class MockUpdate:
        class MockMessage:
            async def reply_text(self, text, parse_mode=None):
                print(f"📱 Bot message: {text[:100]}{'...' if len(text) > 100 else ''}")
        
        effective_message = MockMessage()
    
    class MockContext:
        class MockBot:
            async def send_dice(self, chat_id, emoji):
                import random
                class MockMessage:
                    class MockDice:
                        value = random.randint(1, 5)
                    dice = MockDice()
                return MockMessage()
        
        bot = MockBot()
    
    # Test game with 1.0 bet amount
    user_id = 12345
    bet_amount = 1.0
    
    print(f"  Starting test game: User {user_id}, Bet ${bet_amount}")
    
    # Mock the main module imports
    import importlib.util
    import types
    
    # Create mock main module
    main_module = types.ModuleType('main')
    
    async def mock_get_user(user_id):
        return {'balance': 100.0}
    
    async def mock_update_balance(user_id, amount):
        print(f"  Balance update: User {user_id}, Amount {amount:+.2f}")
        return True
    
    async def mock_deduct_balance(user_id, amount):
        print(f"  Balance deduct: User {user_id}, Amount {amount:.2f}")
        return True
    
    async def mock_log_game_session(user_id, game_type, bet_amount, win_amount, result):
        print(f"  Game logged: {game_type}, Bet ${bet_amount:.2f}, Win ${win_amount:.2f}, Result: {result}")
    
    async def mock_format_usd(amount):
        return f"${amount:.2f}"
    
    main_module.get_user = mock_get_user
    main_module.update_balance = mock_update_balance
    main_module.deduct_balance = mock_deduct_balance
    main_module.log_game_session = mock_log_game_session
    main_module.format_usd = mock_format_usd
    
    # Add to sys.modules
    sys.modules['main'] = main_module
    
    try:
        # Test the game function
        mock_update = MockUpdate()
        mock_context = MockContext()
        
        result = await play_basketball_1v1_interactive(mock_update, mock_context, user_id, bet_amount)
        
        print(f"  Game result:")
        print(f"    Player won: {result['player_won']}")
        print(f"    Final score: {result['player_score']}-{result['bot_score']}")
        print(f"    Total rounds: {result['total_rounds']}")
        print(f"    Bet amount: ${result['bet_amount']:.2f}")
        print(f"    Win amount: ${result['win_amount']:.2f}")
        print(f"    Net result: ${result['net_result']:+.2f}")
        
        # Validate results
        assert isinstance(result['player_won'], bool)
        assert result['player_score'] >= 0
        assert result['bot_score'] >= 0
        assert result['total_rounds'] > 0
        assert result['bet_amount'] == bet_amount
        
        if result['player_won']:
            assert result['win_amount'] > 0
            assert result['net_result'] > 0
        else:
            assert result['win_amount'] == 0
            assert result['net_result'] == -bet_amount
        
        print("✅ Interactive game logic test passed!\n")
        
    except Exception as e:
        print(f"❌ Interactive game test failed: {e}")
        raise
    finally:
        # Clean up
        if 'main' in sys.modules:
            del sys.modules['main']

def main():
    """Run all tests."""
    print("🚀 Starting basketball game tests...\n")
    
    # Test shot results
    test_shot_results()
    
    # Test interactive game logic
    asyncio.run(test_interactive_game_logic())
    
    print("🎉 All basketball game tests passed successfully!")
    print("\n🏀 Interactive basketball game is ready!")
    print("   • Both user and bot send basketball emojis")
    print("   • Animation results determine shot outcomes")
    print("   • Real-time round-by-round gameplay")
    print("   • First to 3 points wins!")

if __name__ == "__main__":
    main()
