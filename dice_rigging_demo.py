#!/usr/bin/env python3
"""
Demonstration of Dice Rigging System
Shows how the casino bot can be configured to favor the house
"""

print("🎲 DICE RIGGING SYSTEM DEMONSTRATION 🎲")
print("=" * 50)

# Simulate different house edge scenarios
import random

def simulate_dice_game(house_edge, num_games=1000):
    """Simulate dice games with specified house edge"""
    bot_wins = 0
    player_wins = 0
    ties = 0
    
    for _ in range(num_games):
        # Player rolls (1-6)
        player_roll = random.randint(1, 6)
        
        # Bot's rigged logic
        bot_should_win = random.random() < house_edge
        
        if bot_should_win:
            # Bot tries to win
            if player_roll < 6:
                bot_roll = random.randint(player_roll + 1, 6)
            else:
                bot_roll = 6 if random.random() < 0.5 else random.randint(1, 5)
        else:
            # Let player win
            if player_roll > 1:
                bot_roll = random.randint(1, player_roll - 1)
            else:
                bot_roll = random.randint(2, 6)
        
        # Determine winner
        if bot_roll > player_roll:
            bot_wins += 1
        elif bot_roll < player_roll:
            player_wins += 1
        else:
            ties += 1
    
    return bot_wins, player_wins, ties

# Test different house edge configurations
configurations = [
    (0.50, "Fair Game"),
    (0.60, "Slight House Edge"),
    (0.65, "Default Configuration"),
    (0.75, "Heavy Rigging"),
    (0.85, "Extreme Rigging"),
    (0.30, "Player Favored")
]

print("\n🎯 SIMULATION RESULTS (1000 games each):")
print("-" * 60)

for house_edge, description in configurations:
    bot_wins, player_wins, ties = simulate_dice_game(house_edge)
    
    bot_win_rate = (bot_wins / 1000) * 100
    player_win_rate = (player_wins / 1000) * 100
    tie_rate = (ties / 1000) * 100
    
    print(f"\n📊 {description} (House Edge: {house_edge:.0%})")
    print(f"   🤖 Bot Wins: {bot_wins} ({bot_win_rate:.1f}%)")
    print(f"   👤 Player Wins: {player_wins} ({player_win_rate:.1f}%)")
    print(f"   🤝 Ties: {ties} ({tie_rate:.1f}%)")

print("\n" + "=" * 50)
print("🎰 CASINO IMPLEMENTATION FEATURES:")
print("=" * 50)

features = [
    "✅ Configurable house edge (10-90%)",
    "✅ Admin controls with /setdice command", 
    "✅ Real Telegram dice animations (appears fair)",
    "✅ Rigged logic behind the scenes",
    "✅ Betting system with balance management",
    "✅ Game statistics and tracking",
    "✅ Professional casino appearance",
    "✅ Audit trail for all games"
]

for feature in features:
    print(feature)

print("\n🎯 HOW THE RIGGING WORKS:")
print("-" * 30)
print("1. Player rolls genuine Telegram dice")
print("2. Bot calculates if it should win (based on house edge)")
print("3. Bot rolls genuine dice (for appearance)")
print("4. Game logic uses rigged calculation, not actual dice")
print("5. Player sees 'fair' dice but experiences rigged outcomes")

print("\n⚖️ LEGAL & ETHICAL CONSIDERATIONS:")
print("-" * 40)
print("⚠️  This is for educational/demo purposes only")
print("⚠️  Real gambling with rigged outcomes may be illegal")
print("⚠️  Always disclose house edge in real applications")
print("⚠️  Consider regulatory requirements in your jurisdiction")

print("\n🎮 ADMIN COMMANDS:")
print("-" * 20)
print("/setdice 50  - Set fair 50/50 odds")
print("/setdice 65  - Set default house edge")
print("/setdice 80  - Heavy rigging in favor of house")
print("/dicestats   - View detailed game statistics")

print("\n💡 The system maintains the illusion of fairness while")
print("   ensuring the house wins at the configured rate!")
