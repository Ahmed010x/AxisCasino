#!/usr/bin/env python3
"""
Verification script to confirm sticker IDs have been updated correctly
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the coin flip module
from bot.games.coinflip import BITCOIN_STICKER_ID, ETHEREUM_STICKER_ID

print("🔍 Verifying Coin Flip Sticker ID Updates...")
print("=" * 50)
print(f"Bitcoin Sticker ID:  {BITCOIN_STICKER_ID}")
print(f"Ethereum Sticker ID: {ETHEREUM_STICKER_ID}")
print("=" * 50)

# Expected sticker IDs from user
expected_bitcoin = "CAACAgEAAxkBAAE7-Apo33tf-s6ZkKsrTN6XPoH9A2ZnnwACIAYAAhUgyUYrIh_7ZdalyDYE"
expected_ethereum = "CAACAgEAAxkBAAE7-zto38pyTGfQQ670ZjqdmTffjdIuUgACHwYAAhUgyUaS92CoIHXqcDYE"

# Verify updates
bitcoin_correct = BITCOIN_STICKER_ID == expected_bitcoin
ethereum_correct = ETHEREUM_STICKER_ID == expected_ethereum

print("✅ Verification Results:")
print(f"  Bitcoin:  {'✅ CORRECT' if bitcoin_correct else '❌ INCORRECT'}")
print(f"  Ethereum: {'✅ CORRECT' if ethereum_correct else '❌ INCORRECT'}")

if bitcoin_correct and ethereum_correct:
    print("\n🎉 SUCCESS: All sticker IDs have been updated correctly!")
    print("The coin flip game will now use the new stickers you provided.")
else:
    print("\n❌ ERROR: Sticker IDs do not match expected values")
    if not bitcoin_correct:
        print(f"  Expected Bitcoin:  {expected_bitcoin}")
        print(f"  Current Bitcoin:   {BITCOIN_STICKER_ID}")
    if not ethereum_correct:
        print(f"  Expected Ethereum: {expected_ethereum}")
        print(f"  Current Ethereum:  {ETHEREUM_STICKER_ID}")

print("\n📝 Next Steps:")
print("1. Start your bot with the updated coin flip game")
print("2. Test the coin flip game to confirm stickers are sent correctly")
print("3. Monitor the bot logs for any sticker sending errors")
