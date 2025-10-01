#!/usr/bin/env python3
"""
Test script for house balance system
Tests database creation, balance updates, and calculations
"""

import asyncio
import sys
import os
sys.path.append('.')

# Import functions from main.py
from main import (
    init_db, get_house_balance, update_house_balance_on_game,
    update_house_balance_on_deposit, update_house_balance_on_withdrawal,
    get_house_profit_loss, get_house_balance_display, format_usd
)

async def test_house_balance_system():
    """Test the house balance system"""
    print("🧪 Testing House Balance System...")
    
    try:
        # Initialize database
        print("\n1. Initializing database...")
        await init_db()
        print("✅ Database initialized")
        
        # Get initial house balance
        print("\n2. Getting initial house balance...")
        initial_balance = await get_house_balance()
        print(f"✅ Initial balance: ${initial_balance['balance']:.2f}")
        
        # Test deposit (house gains funds)
        print("\n3. Testing deposit (+$100)...")
        deposit_success = await update_house_balance_on_deposit(100.0)
        print(f"✅ Deposit update: {'Success' if deposit_success else 'Failed'}")
        
        balance_after_deposit = await get_house_balance()
        print(f"   Balance after deposit: ${balance_after_deposit['balance']:.2f}")
        
        # Test game where player loses (house wins)
        print("\n4. Testing game - player loses ($50 bet, $0 win)...")
        game_success = await update_house_balance_on_game(50.0, 0.0)
        print(f"✅ Game update: {'Success' if game_success else 'Failed'}")
        
        balance_after_loss = await get_house_balance()
        print(f"   Balance after player loss: ${balance_after_loss['balance']:.2f}")
        
        # Test game where player wins (house loses)
        print("\n5. Testing game - player wins ($30 bet, $60 win)...")
        game_success = await update_house_balance_on_game(30.0, 60.0)
        print(f"✅ Game update: {'Success' if game_success else 'Failed'}")
        
        balance_after_win = await get_house_balance()
        print(f"   Balance after player win: ${balance_after_win['balance']:.2f}")
        
        # Test withdrawal (house loses funds)
        print("\n6. Testing withdrawal (-$75)...")
        withdrawal_success = await update_house_balance_on_withdrawal(75.0)
        print(f"✅ Withdrawal update: {'Success' if withdrawal_success else 'Failed'}")
        
        balance_after_withdrawal = await get_house_balance()
        print(f"   Balance after withdrawal: ${balance_after_withdrawal['balance']:.2f}")
        
        # Get profit/loss statistics
        print("\n7. Getting profit/loss statistics...")
        stats = await get_house_profit_loss()
        print(f"✅ Statistics calculated:")
        print(f"   Current Balance: ${stats['current_balance']:.2f}")
        print(f"   Total Deposits: ${stats['total_deposits']:.2f}")
        print(f"   Total Withdrawals: ${stats['total_withdrawals']:.2f}")
        print(f"   Player Losses: ${stats['total_player_losses']:.2f}")
        print(f"   Player Wins: ${stats['total_player_wins']:.2f}")
        print(f"   Net Profit: ${stats['net_profit']:.2f}")
        print(f"   House Edge: {stats['house_edge_percent']:.2f}%")
        
        # Test display formatting
        print("\n8. Testing display formatting...")
        display = await get_house_balance_display()
        print("✅ Display format:")
        print(display)
        
        # Verify calculations
        print("\n9. Verifying calculations...")
        expected_balance = 10000.0 + 100.0 + 50.0 - 30.0 - 75.0  # Initial + deposit + player_loss - house_loss - withdrawal
        actual_balance = balance_after_withdrawal['balance']
        
        print(f"   Expected final balance: ${expected_balance:.2f}")
        print(f"   Actual final balance: ${actual_balance:.2f}")
        
        if abs(expected_balance - actual_balance) < 0.01:
            print("✅ Balance calculations are correct!")
        else:
            print("❌ Balance calculations don't match!")
            return False
        
        print("\n🎉 All house balance tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_multiple_games():
    """Test house balance with multiple game scenarios"""
    print("\n🎮 Testing Multiple Game Scenarios...")
    
    try:
        # Simulate 10 games with various outcomes
        games = [
            (10.0, 0.0),    # Player loses $10
            (20.0, 40.0),   # Player wins $20 (bet $20, win $40)
            (5.0, 0.0),     # Player loses $5
            (15.0, 30.0),   # Player wins $15 (bet $15, win $30)
            (25.0, 0.0),    # Player loses $25
            (8.0, 16.0),    # Player wins $8 (bet $8, win $16)
            (30.0, 0.0),    # Player loses $30
            (12.0, 0.0),    # Player loses $12
            (18.0, 36.0),   # Player wins $18 (bet $18, win $36)
            (22.0, 0.0),    # Player loses $22
        ]
        
        initial_balance = await get_house_balance()
        print(f"Initial house balance: ${initial_balance['balance']:.2f}")
        
        house_net_change = 0.0
        
        for i, (bet, win) in enumerate(games, 1):
            await update_house_balance_on_game(bet, win)
            house_change = bet - win  # Positive = house gains, negative = house loses
            house_net_change += house_change
            print(f"Game {i}: Bet ${bet:.2f}, Win ${win:.2f} -> House {'+' if house_change >= 0 else ''}${house_change:.2f}")
        
        final_balance = await get_house_balance()
        expected_final = initial_balance['balance'] + house_net_change
        
        print(f"\nTotal house change: ${house_net_change:+.2f}")
        print(f"Expected final balance: ${expected_final:.2f}")
        print(f"Actual final balance: ${final_balance['balance']:.2f}")
        
        if abs(expected_final - final_balance['balance']) < 0.01:
            print("✅ Multiple game calculations are correct!")
        else:
            print("❌ Multiple game calculations don't match!")
            
        # Show final stats
        stats = await get_house_profit_loss()
        print(f"\nFinal Statistics:")
        print(f"House Edge: {stats['house_edge_percent']:.2f}%")
        print(f"Net Profit: ${stats['net_profit']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Multiple games test failed: {e}")
        return False

async def main():
    """Run all house balance tests"""
    print("🏦 House Balance System Test Suite")
    print("=" * 50)
    
    # Test basic functionality
    basic_test = await test_house_balance_system()
    
    if basic_test:
        # Test with multiple games
        games_test = await test_multiple_games()
        
        if games_test:
            print("\n🎉 All tests passed! House balance system is working correctly.")
            return True
    
    print("\n❌ Some tests failed. Please check the implementation.")
    return False

if __name__ == "__main__":
    asyncio.run(main())
