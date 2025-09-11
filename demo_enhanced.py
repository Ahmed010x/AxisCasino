#!/usr/bin/env python3
"""
Comprehensive Demo Script for Enhanced Telegram Casino Bot

This script demonstrates all the new features and capabilities.
"""

import asyncio
import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.database.db import init_db
from bot.database.user import create_user, get_user, add_game_result
from bot.utils.achievements import init_achievements_db, check_achievements, ACHIEVEMENTS
from bot.handlers.leaderboard import get_top_players_by_balance
from bot.games.poker import PokerGame
from bot.games.slots import generate_reels, calculate_win


async def demo_enhanced_casino():
    """Demonstrate all enhanced casino features."""
    print("🎰" + "="*60 + "🎰")
    print("    ENHANCED TELEGRAM CASINO BOT DEMONSTRATION")
    print("🎰" + "="*60 + "🎰")
    
    # Initialize everything
    await init_db()
    await init_achievements_db()
    print("✅ Database systems initialized")
    
    # Create demo user
    demo_user_id = 99999
    demo_username = "DemoPlayer"
    await create_user(demo_user_id, demo_username)
    print(f"✅ Created demo user: {demo_username}")
    
    print("\n" + "🎮" + "-"*50 + "🎮")
    print("               GAME DEMONSTRATIONS")
    print("🎮" + "-"*50 + "🎮")
    
    # 1. Slots Demo
    print("\n🎰 SLOT MACHINE DEMO:")
    for i in range(3):
        reels = generate_reels()
        win_amount, result = calculate_win(reels, 50)
        status = "WIN! 🎉" if win_amount > 0 else "LOSE 😔"
        print(f"  Spin {i+1}: {' | '.join(reels)} = {status}")
        if win_amount > 0:
            print(f"    └─ {result} (Won {win_amount} chips)")
    
    # 2. Poker Demo
    print("\n🃏 POKER DEMO:")
    poker_game = PokerGame(25)
    print(f"  Player Hand: {poker_game.format_cards(poker_game.player_hand)}")
    print(f"  Dealer Hand: {poker_game.format_hidden_cards(2)}")
    
    # Deal community cards for demo
    poker_game.deal_flop()
    poker_game.deal_turn()
    poker_game.deal_river()
    print(f"  Community: {poker_game.format_cards(poker_game.community_cards)}")
    
    # Evaluate hands
    player_rank, player_hand, _ = poker_game.evaluate_hand(poker_game.player_hand)
    dealer_rank, dealer_hand, _ = poker_game.evaluate_hand(poker_game.dealer_hand)
    print(f"  Player: {player_hand}")
    print(f"  Dealer: {dealer_hand}")
    
    winner, result = poker_game.get_winner()
    print(f"  Result: {result}")
    
    print("\n" + "🏆" + "-"*50 + "🏆")
    print("             ACHIEVEMENT SYSTEM DEMO")
    print("🏆" + "-"*50 + "🏆")
    
    # Simulate some game results to trigger achievements
    print("\nSimulating games to unlock achievements...")
    
    # Add game results
    await add_game_result(demo_user_id, 'slots', 50, 100, 'WIN! Cherries')
    await add_game_result(demo_user_id, 'blackjack', 100, 200, 'WIN! Player 20, Dealer 18')
    await add_game_result(demo_user_id, 'roulette', 25, 50, 'WIN! Red')
    
    # Check achievements
    new_achievements = await check_achievements(demo_user_id)
    print(f"🎉 Unlocked {len(new_achievements)} achievements!")
    
    for ach_id in new_achievements:
        achievement = ACHIEVEMENTS[ach_id]
        print(f"  ✨ {achievement['name']} - {achievement['description']} (+{achievement['reward']} chips)")
    
    print("\n📊 All Available Achievements:")
    for ach_id, achievement in ACHIEVEMENTS.items():
        print(f"  🏆 {achievement['name']} - {achievement['reward']} chips")
        print(f"     └─ {achievement['description']}")
    
    print("\n" + "📊" + "-"*50 + "📊")
    print("              LEADERBOARD DEMO")
    print("📊" + "-"*50 + "📊")
    
    # Create more demo users for leaderboard
    demo_users = [
        (88888, "HighRoller", 5000),
        (77777, "LuckyPlayer", 3500),
        (66666, "CardShark", 2800),
        (55555, "SlotMaster", 2200)
    ]
    
    for user_id, username, balance in demo_users:
        await create_user(user_id, username)
        await add_game_result(user_id, 'slots', 100, balance, 'Demo game')
    
    # Show leaderboard
    top_players = await get_top_players_by_balance(5)
    print("\n💰 Richest Players Leaderboard:")
    for i, player in enumerate(top_players, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        print(f"  {medal} {player['username']} - {player['balance']:,} chips")
    
    print("\n" + "🎯" + "-"*50 + "🎯")
    print("              FEATURE SUMMARY")
    print("🎯" + "-"*50 + "🎯")
    
    features = [
        "🎰 Advanced Slot Machine - 5 symbols, multiple betting options",
        "🃏 Complete Blackjack - Hit, stand, double down with proper logic",
        "🎲 European Roulette - All betting types with realistic payouts",
        "🎯 Multi-Mode Dice Games - High/Low, Exact Sum, Triple Dice",
        "🃏 Texas Hold'em Poker - Full implementation with betting rounds",
        "🏆 Achievement System - 14 achievements with automatic tracking",
        "📊 Leaderboards - Multiple categories and personal rankings", 
        "💾 Persistent Sessions - Save complex games like poker",
        "🎁 Daily Bonuses - Streak tracking and rewards",
        "📈 Advanced Statistics - Win streaks, biggest wins tracking",
        "🔔 Real-time Notifications - Achievement unlocks and updates",
        "🎮 Interactive UI - Inline keyboards for seamless gameplay"
    ]
    
    for feature in features:
        print(f"  ✅ {feature}")
    
    print("\n" + "🎊" + "-"*50 + "🎊")
    print("         DEMO COMPLETE - BOT READY TO LAUNCH!")
    print("🎊" + "-"*50 + "🎊")
    
    print("\nNext Steps:")
    print("1. 🔧 Add your BOT_TOKEN to .env file")
    print("2. 🚀 Run: python main.py")
    print("3. 🎮 Start playing and enjoy all the enhanced features!")
    print("\n💡 Pro Tip: The bot now supports complex game states,")
    print("   achievement tracking, and competitive leaderboards!")


if __name__ == "__main__":
    asyncio.run(demo_enhanced_casino())
