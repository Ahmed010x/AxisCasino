#!/usr/bin/env python3
"""
Test Coin Flip Custom Emoji Display
This script tests the custom emoji format for Telegram
"""

# Custom Telegram Emoji IDs
HEADS_EMOJI_ID = "5886663771962743061"
TAILS_EMOJI_ID = "5886234567290918532"

def test_emoji_format():
    """Test the custom emoji HTML format"""
    
    print("Testing Custom Emoji Format for Coin Flip Game\n")
    print("=" * 60)
    
    # Test Heads emoji
    heads_emoji = f'<tg-emoji emoji-id="{HEADS_EMOJI_ID}">🪙</tg-emoji>'
    print(f"\n🟡 HEADS Emoji:")
    print(f"   ID: {HEADS_EMOJI_ID}")
    print(f"   HTML: {heads_emoji}")
    
    # Test Tails emoji
    tails_emoji = f'<tg-emoji emoji-id="{TAILS_EMOJI_ID}">🪙</tg-emoji>'
    print(f"\n🔵 TAILS Emoji:")
    print(f"   ID: {TAILS_EMOJI_ID}")
    print(f"   HTML: {tails_emoji}")
    
    # Test result display (Heads)
    print("\n" + "=" * 60)
    print("\nExample Result Message (HEADS):")
    print("=" * 60)
    result_heads = f"""
🎰 <b>COIN FLIP RESULT</b> 🎰

{'🟡' * 10}

{heads_emoji * 3}  <b>HEADS</b>  {heads_emoji * 3}

{'🟡' * 10}
"""
    print(result_heads)
    
    # Test result display (Tails)
    print("\n" + "=" * 60)
    print("\nExample Result Message (TAILS):")
    print("=" * 60)
    result_tails = f"""
🎰 <b>COIN FLIP RESULT</b> 🎰

{'🔵' * 10}

{tails_emoji * 3}  <b>TAILS</b>  {tails_emoji * 3}

{'🔵' * 10}
"""
    print(result_tails)
    
    # Test win message
    print("\n" + "=" * 60)
    print("\nExample Win Message:")
    print("=" * 60)
    win_msg = f"""
🎉 <b>YOU WIN!</b> 🎉

🟡 <b>Result: {heads_emoji} HEADS</b>

💰 <b>Bet:</b> $10.00
💵 <b>Won:</b> $19.50
📈 <b>Profit:</b> $9.50

💳 <b>New Balance:</b> $109.50

<i>🎊 Congratulations! You predicted correctly!</i>
"""
    print(win_msg)
    
    print("\n" + "=" * 60)
    print("✅ Custom emoji format test complete!")
    print("\nNOTE: The custom emoji will only display correctly in Telegram.")
    print("In console, you'll see the fallback emoji (🪙).")
    print("=" * 60)

if __name__ == "__main__":
    test_emoji_format()
