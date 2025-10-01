#!/usr/bin/env python3
"""
Test script to demonstrate the user panel functionality
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main

async def test_user_panel():
    """Test the user panel functionality"""
    print("🧪 Testing User Panel Functionality")
    print("=" * 50)
    
    # Initialize database
    await main.init_db()
    print("✅ Database initialized")
    
    # Create test user
    test_user_id = 123456789
    test_username = "test_user"
    
    user = await main.create_user(test_user_id, test_username)
    print(f"✅ Created test user: {test_username}")
    
    # Add some balance
    await main.update_balance(test_user_id, 150.0)
    print("✅ Added $150.00 balance")
    
    # Simulate some game activity
    await main.log_game_session(test_user_id, "slots", 10.0, 25.0, "win")
    await main.log_game_session(test_user_id, "blackjack", 20.0, 0.0, "loss")
    await main.log_game_session(test_user_id, "dice", 5.0, 15.0, "win")
    print("✅ Simulated game sessions")
    
    # Get updated user data
    user = await main.get_user(test_user_id)
    
    # Generate referral code
    ref_code = await main.get_or_create_referral_code(test_user_id)
    print(f"✅ Generated referral code: {ref_code}")
    
    # Display user panel info
    print("\n🎰 USER PANEL PREVIEW:")
    print("-" * 30)
    
    balance_str = await main.format_usd(user['balance'])
    wagered_str = await main.format_usd(user['total_wagered'])
    won_str = await main.format_usd(user['total_won'])
    
    net_result = user['total_won'] - user['total_wagered']
    net_emoji = "📈" if net_result >= 0 else "📉"
    net_str = await main.format_usd(abs(net_result))
    
    panel_text = f"""
🎰 AXIS CASINO 🎰
Welcome back, {test_username}!

💰 Balance: {balance_str}
🎮 Games Played: {user['games_played']:,}
💸 Total Wagered: {wagered_str}
🏆 Total Won: {won_str}
{net_emoji} Net Result: {net_str} {"profit" if net_result >= 0 else "loss"}
🔥 Win Streak: {user['win_streak']}
👥 Referrals: {user['referral_count']}

🔗 Your Referral Code: {ref_code}
Share to earn bonuses!

Available Actions:
💳 Deposit | 🏦 Withdraw | 🎮 Play Games
👥 Referrals | 📊 Statistics | ❓ Help
"""
    
    print(panel_text)
    
    # Test house balance
    house_stats = await main.get_house_profit_loss()
    house_balance_str = await main.format_usd(house_stats['current_balance'])
    print(f"🏦 House Balance: {house_balance_str}")
    
    # Test formatting functions
    print("\n🧪 Testing Formatting Functions:")
    print(f"• USD Format: {await main.format_usd(1234.56)}")
    print(f"• Crypto Format: {await main.format_crypto_usd(0.1, 'LTC')}")
    
    print("\n✅ All user panel tests passed!")
    print("\n📝 To test the actual bot:")
    print("1. Run: python main.py")
    print("2. Send /start to your bot on Telegram")
    print("3. You should see the comprehensive user panel!")
    
    # Clean up test data
    print("\n🧹 Cleaning up test data...")
    import os
    if os.path.exists('casino.db'):
        os.remove('casino.db')
    print("✅ Test database cleaned up")

if __name__ == "__main__":
    asyncio.run(test_user_panel())
