#!/usr/bin/env python3
"""
Test script for the comprehensive house balance system
Tests all house balance functions and admin commands
"""

import asyncio
import os
import sys
import tempfile
import aiosqlite
from datetime import datetime, timedelta

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from main.py
from main import (
    init_db,
    get_house_balance,
    update_house_balance_on_game,
    update_house_balance_on_deposit,
    update_house_balance_on_withdrawal,
    get_house_profit_loss,
    get_house_balance_summary,
    get_house_risk_metrics,
    get_house_performance_report,
    adjust_house_balance,
    reset_daily_house_stats,
    update_daily_house_stats,
    get_enhanced_house_balance_display,
    format_usd,
    DB_PATH
)

async def test_house_balance_system():
    """Test all house balance system functions"""
    print("🏦 Testing House Balance System...")
    
    # Use a temporary database for testing
    original_db = DB_PATH
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        test_db = tmp_file.name
    
    # Monkey patch the DB_PATH
    import main
    main.DB_PATH = test_db
    
    try:
        # Initialize database
        print("1️⃣ Initializing test database...")
        await init_db()
        print("✅ Database initialized")
        
        # Test basic house balance operations
        print("\n2️⃣ Testing basic house balance operations...")
        
        # Get initial balance
        initial_balance = await get_house_balance()
        print(f"📊 Initial house balance: {initial_balance}")
        assert initial_balance['balance'] == 10000.0, f"Expected 10000.0, got {initial_balance['balance']}"
        
        # Test game outcome updates
        print("\n3️⃣ Testing game outcome updates...")
        
        # Simulate a game where house wins $50
        success = await update_house_balance_on_game(100.0, 50.0)  # Player bets $100, wins $50
        assert success, "Failed to update house balance on game"
        
        balance = await get_house_balance()
        expected_balance = 10000.0 + (100.0 - 50.0)  # House gains net $50
        assert balance['balance'] == expected_balance, f"Expected {expected_balance}, got {balance['balance']}"
        print(f"✅ Game update: House balance now ${balance['balance']:.2f}")
        
        # Test deposit
        print("\n4️⃣ Testing deposit updates...")
        success = await update_house_balance_on_deposit(200.0)
        assert success, "Failed to update house balance on deposit"
        
        balance = await get_house_balance()
        expected_balance += 200.0
        assert balance['balance'] == expected_balance, f"Expected {expected_balance}, got {balance['balance']}"
        print(f"✅ Deposit update: House balance now ${balance['balance']:.2f}")
        
        # Test withdrawal
        print("\n5️⃣ Testing withdrawal updates...")
        success = await update_house_balance_on_withdrawal(150.0)
        assert success, "Failed to update house balance on withdrawal"
        
        balance = await get_house_balance()
        expected_balance -= 150.0
        assert balance['balance'] == expected_balance, f"Expected {expected_balance}, got {balance['balance']}"
        print(f"✅ Withdrawal update: House balance now ${balance['balance']:.2f}")
        
        # Test profit/loss calculations
        print("\n6️⃣ Testing profit/loss calculations...")
        profit_loss = await get_house_profit_loss()
        print(f"📈 Profit/Loss metrics: {profit_loss}")
        assert profit_loss['net_profit'] > 0, "Expected positive net profit"
        
        # Test house balance summary
        print("\n7️⃣ Testing house balance summary...")
        summary = await get_house_balance_summary()
        print(f"📊 Summary metrics: {summary}")
        assert 'current_balance' in summary, "Summary missing current_balance"
        assert 'net_profit' in summary, "Summary missing net_profit"
        
        # Test risk metrics
        print("\n8️⃣ Testing risk metrics...")
        risk_metrics = await get_house_risk_metrics()
        print(f"🚨 Risk metrics: {risk_metrics}")
        assert 'risk_level' in risk_metrics, "Risk metrics missing risk_level"
        assert 'is_healthy' in risk_metrics, "Risk metrics missing is_healthy"
        
        # Test daily stats
        print("\n9️⃣ Testing daily statistics...")
        success = await update_daily_house_stats(50.0, 25.0)
        assert success, "Failed to update daily stats"
        
        balance = await get_house_balance()
        assert balance.get('games_played_today', 0) == 1, "Daily games count not updated"
        print(f"✅ Daily stats: {balance.get('games_played_today', 0)} games played today")
        
        # Test admin balance adjustment
        print("\n🔟 Testing admin balance adjustment...")
        success = await adjust_house_balance(12345, 500.0, "Test adjustment")
        assert success, "Failed to adjust house balance"
        
        balance = await get_house_balance()
        expected_balance += 500.0
        assert abs(balance['balance'] - expected_balance) < 0.01, f"Expected {expected_balance}, got {balance['balance']}"
        print(f"✅ Admin adjustment: House balance now ${balance['balance']:.2f}")
        
        # Test enhanced display
        print("\n1️⃣1️⃣ Testing enhanced display...")
        display = await get_enhanced_house_balance_display()
        assert len(display) > 100, "Display text too short"
        assert "ENHANCED HOUSE BALANCE" in display, "Display missing title"
        print("✅ Enhanced display generated successfully")
        
        # Test daily reset
        print("\n1️⃣2️⃣ Testing daily reset...")
        success = await reset_daily_house_stats()
        assert success, "Failed to reset daily stats"
        
        balance = await get_house_balance()
        assert balance.get('games_played_today', 0) == 0, "Daily games count not reset"
        print("✅ Daily stats reset successfully")
        
        # Test performance report
        print("\n1️⃣3️⃣ Testing performance report...")
        
        # First, add some game sessions for the report
        async with aiosqlite.connect(test_db) as db:
            await db.execute("""
                INSERT INTO game_sessions (user_id, game_type, bet_amount, win_amount, result, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (123, 'slots', 100.0, 0.0, 'loss', datetime.now().isoformat()))
            
            await db.execute("""
                INSERT INTO game_sessions (user_id, game_type, bet_amount, win_amount, result, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (124, 'blackjack', 50.0, 100.0, 'win', datetime.now().isoformat()))
            
            await db.commit()
        
        performance = await get_house_performance_report(7)
        print(f"📈 Performance report: {performance}")
        assert 'total_games' in performance, "Performance report missing total_games"
        assert performance['total_games'] >= 2, "Performance report should show at least 2 games"
        
        print("\n🎉 All house balance tests passed!")
        
        # Show final state
        final_balance = await get_house_balance()
        final_display = await get_enhanced_house_balance_display()
        
        print(f"\n📊 Final House Balance State:")
        print(f"💰 Balance: ${final_balance['balance']:.2f}")
        print(f"📈 Total Player Losses: ${final_balance.get('total_player_losses', 0):.2f}")
        print(f"📉 Total Player Wins: ${final_balance.get('total_player_wins', 0):.2f}")
        print(f"💳 Total Deposits: ${final_balance.get('total_deposits', 0):.2f}")
        print(f"🏦 Total Withdrawals: ${final_balance.get('total_withdrawals', 0):.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up test database
        try:
            os.unlink(test_db)
        except:
            pass
        
        # Restore original DB_PATH
        main.DB_PATH = original_db

async def main():
    """Run the house balance system tests"""
    print("🚀 Starting House Balance System Tests")
    print("=" * 50)
    
    success = await test_house_balance_system()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ ALL HOUSE BALANCE TESTS PASSED!")
        print("🏦 Your house balance system is fully functional and production-ready!")
    else:
        print("❌ SOME TESTS FAILED!")
        print("🔧 Please check the errors above and fix any issues.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
