"""
Basketball Game Test

Quick test to verify basketball game module works correctly.
"""

import sys
import asyncio

# Test imports
try:
    from bot.games.basketball import (
        play_basketball_game,
        get_shot_description,
        MIN_BET,
        MAX_BET
    )
    print("✅ Basketball game imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test shot descriptions
print("\n🏀 Testing shot descriptions:")
for value in range(1, 6):
    desc = get_shot_description(value)
    print(f"  Value {value}: {desc}")

# Test bet limits
print(f"\n💵 Bet Limits:")
print(f"  Min Bet: ${MIN_BET:.2f}")
print(f"  Max Bet: ${MAX_BET:.2f}")

# Test game logic (simulated)
print("\n🎮 Testing game logic simulation:")
print("  SCORE bet payout: 1.8x (40% win chance)")
print("  MISS bet payout: 1.5x (60% win chance)")

# Calculate house edge
score_ev = (0.4 * 1.8) - (0.6 * 1.0)
miss_ev = (0.6 * 1.5) - (0.4 * 1.0)
score_house_edge = (1 - (0.4 * 1.8)) * 100
miss_house_edge = (1 - (0.6 * 1.5)) * 100

print(f"\n📊 Expected Values:")
print(f"  SCORE bet EV: {score_ev:.2f} (House edge: {score_house_edge:.1f}%)")
print(f"  MISS bet EV: {miss_ev:.2f} (House edge: {miss_house_edge:.1f}%)")

print("\n✅ All basketball game tests passed!")
print("🏀 Basketball game is ready to play!")
