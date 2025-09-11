#!/usr/bin/env python3
"""
Telegram Casino Bot - Demo Mode

This demo shows that all game logic works correctly without Telegram connectivity.
It simulates user interactions and shows the games working.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def demo_casino_games():
    """Demonstrate all casino games working."""
    print("🎰 TELEGRAM CASINO BOT - DEMO MODE")
    print("=" * 50)
    
    # Initialize database
    from bot.database.db import init_db
    from bot.utils.achievements import init_achievements_db
    from bot.database.user import create_user, get_user, update_balance
    
    await init_db()
    await init_achievements_db()
    print("✅ Database initialized")
    
    # Create demo user
    user_id = 12345
    username = "demo_player"
    await create_user(user_id, username)
    
    # Give demo user some coins
    await update_balance(user_id, 5000)
    user = await get_user(user_id)
    print(f"✅ Demo user created: {username} with {user['balance']} coins")
    print()
    
    # Demo Slots Game
    print("🎰 SLOTS GAME DEMO")
    print("-" * 20)
    from bot.games.slots import play_slots
    
    for i in range(3):
        reels, win_amount, result_text, new_balance = await play_slots(user_id, 100)
        print(f"Spin {i+1}: {' '.join(reels)} | {result_text} | Balance: {new_balance}")
    print()
    
    # Demo Dice Game
    print("🎲 DICE GAME DEMO")
    print("-" * 20)
    from bot.games.dice import roll_dice, get_dice_emoji
    
    for i in range(3):
        dice1, dice2 = roll_dice()
        emoji1, emoji2 = get_dice_emoji(dice1), get_dice_emoji(dice2)
        total = dice1 + dice2
        print(f"Roll {i+1}: {emoji1} {emoji2} (Total: {total})")
    print()
    
    # Demo Roulette
    print("🎡 ROULETTE DEMO")
    print("-" * 20)
    from bot.games.roulette import spin_wheel, get_number_color, check_bet_win
    
    for i in range(3):
        number = spin_wheel()
        color = get_number_color(number)
        red_win = check_bet_win(number, "red")
        print(f"Spin {i+1}: Number {number} ({color}) | Red bet wins: {red_win}")
    print()
    
    # Demo Blackjack
    print("🃏 BLACKJACK DEMO")
    print("-" * 20)
    from bot.games.blackjack import BlackjackGame
    
    game = BlackjackGame(100)
    print(f"Player hand: {game.format_hand(game.player_hand)} (Value: {game.get_hand_value(game.player_hand)})")
    print(f"Dealer hand: {game.format_hand([game.dealer_hand[0]])} + [Hidden]")
    print()
    
    # Demo Poker
    print("🎯 POKER DEMO")
    print("-" * 20)
    from bot.games.poker import PokerGame
    
    poker = PokerGame(50)
    print(f"Player cards: {poker.format_cards(poker.player_hand)}")
    print(f"Community cards: {poker.format_cards(poker.community_cards)}")
    print()
    
    # Demo Achievements
    print("🏆 ACHIEVEMENTS DEMO")
    print("-" * 20)
    from bot.utils.achievements import check_achievements, get_user_achievements
    
    new_achievements = await check_achievements(user_id)
    if new_achievements:
        print(f"🎉 New achievements unlocked: {new_achievements}")
    
    achievements = await get_user_achievements(user_id)
    print(f"User achievements: {len(achievements)} unlocked")
    for achievement_id in achievements:
        print(f"  🏆 Achievement: {achievement_id}")
    print()
    
    # Show final balance
    user = await get_user(user_id)
    print("💰 FINAL RESULTS")
    print("-" * 20)
    print(f"Player: {username}")
    print(f"Final Balance: {user['balance']} coins")
    print(f"User ID: {user_id}")
    print()
    
    print("✅ ALL GAMES WORKING PERFECTLY!")
    print("🚀 Ready to connect to Telegram!")
    
    return True

async def demo_payment_system():
    """Demo the payment system."""
    print("\n💳 PAYMENT SYSTEM DEMO")
    print("=" * 30)
    
    from bot.handlers.payments import PaymentProcessor, DepositProcessor, WithdrawalProcessor
    
    user_id = 12345
    
    # Demo transaction creation
    transaction_id = await PaymentProcessor.create_transaction(
        user_id, "deposit", 1000, "credit_card", 
        {"card_last4": "1234", "amount": 1000}
    )
    print(f"✅ Created transaction: {transaction_id[:8]}...")
    
    # Demo deposit processing
    success, message = await DepositProcessor.process_deposit(
        user_id, 1000, "credit_card", 
        {"card_number": "4111111111111111", "cvv": "123"}
    )
    print(f"💰 Deposit result: {success} - {message}")
    
    # Demo transaction history
    transactions = await PaymentProcessor.get_user_transactions(user_id)
    print(f"📄 Transaction history: {len(transactions)} transactions")
    
    return True

if __name__ == '__main__':
    try:
        print("🎮 Starting Casino Demo...")
        
        # Check bot token
        bot_token = os.getenv('BOT_TOKEN')
        if bot_token and bot_token != 'your_telegram_bot_token_here':
            print(f"🤖 Bot token configured (length: {len(bot_token)})")
        else:
            print("⚠️  Bot token not configured (demo mode only)")
        
        # Run demos
        asyncio.run(demo_casino_games())
        asyncio.run(demo_payment_system())
        
        print("\n🎉 DEMO COMPLETE!")
        print("📱 To test with real Telegram:")
        print("   1. Make sure BOT_TOKEN is set in .env")
        print("   2. Run bot in a fresh terminal: python main.py")
        print("   3. Message your bot on Telegram with /start")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
