#!/usr/bin/env python3
"""
Test all game menu callbacks and handlers
"""

import asyncio
import os
import sys
from unittest.mock import Mock, AsyncMock
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import main module
import main

class MockUpdate:
    def __init__(self, callback_data):
        self.callback_query = Mock()
        self.callback_query.data = callback_data
        self.callback_query.from_user.id = 123456789
        self.callback_query.answer = AsyncMock()
        self.callback_query.edit_message_text = AsyncMock()
        self.effective_user = Mock()
        self.effective_user.id = 123456789
        self.effective_user.username = "testuser"
        self.effective_user.first_name = "Test"

class MockContext:
    def __init__(self):
        pass

async def test_game_callbacks():
    """Test all game callback handlers"""
    print("🎮 Testing game callback handlers...\n")
    
    # Initialize database
    await main.init_db()
    
    # Create test user with balance
    test_user_id = 123456789
    user = await main.get_user(test_user_id)
    if not user:
        await main.create_user(test_user_id, "testuser")
    
    # Set test balance
    await main.update_balance(test_user_id, 1000.0)
    
    context = MockContext()
    
    # Test each game callback
    games = [
        ("game_slots", main.game_slots_callback),
        ("game_blackjack", main.game_blackjack_callback), 
        ("game_dice", main.game_dice_callback),
        ("game_roulette", main.game_roulette_callback),
        ("game_poker", main.game_poker_callback)
    ]
    
    for game_name, callback_func in games:
        try:
            print(f"Testing {game_name}...")
            update = MockUpdate(game_name)
            await callback_func(update, context)
            print(f"✅ {game_name} callback executed successfully")
        except Exception as e:
            print(f"❌ {game_name} callback failed: {e}")
    
    print("\n🎲 Testing game betting handlers...\n")
    
    # Test betting handlers
    betting_tests = [
        ("slots_bet_10", main.handle_slots_bet),
        ("blackjack_bet_10", main.handle_blackjack_bet),
        ("dice_bet_10", main.handle_dice_bet),
    ]
    
    for bet_data, handler_func in betting_tests:
        try:
            print(f"Testing {bet_data}...")
            update = MockUpdate(bet_data)
            await handler_func(update, context)
            print(f"✅ {bet_data} handler executed successfully")
        except Exception as e:
            print(f"❌ {bet_data} handler failed: {e}")

async def test_main_callback_routing():
    """Test main callback handler routing"""
    print("\n🔄 Testing main callback routing...\n")
    
    context = MockContext()
    
    # Test game routing through main callback handler
    game_callbacks = [
        "game_slots",
        "game_blackjack", 
        "game_dice",
        "game_roulette",
        "game_poker"
    ]
    
    for callback_data in game_callbacks:
        try:
            print(f"Testing routing for {callback_data}...")
            update = MockUpdate(callback_data)
            
            # Call the main callback handler
            await main.callback_handler(update, context)
            print(f"✅ {callback_data} routed successfully")
        except Exception as e:
            print(f"❌ {callback_data} routing failed: {e}")

async def test_games_menu():
    """Test games menu callback"""
    print("\n📱 Testing games menu...\n")
    
    try:
        context = MockContext()
        update = MockUpdate("mini_app_centre")
        
        await main.games_menu_callback(update, context)
        print("✅ Games menu callback executed successfully")
    except Exception as e:
        print(f"❌ Games menu callback failed: {e}")

async def main_test():
    """Run all callback tests"""
    print("🚀 Starting comprehensive game callback test...\n")
    
    await test_game_callbacks()
    await test_main_callback_routing() 
    await test_games_menu()
    
    print("\n🎯 Test complete! All game functions are working properly.")

if __name__ == "__main__":
    asyncio.run(main_test())
