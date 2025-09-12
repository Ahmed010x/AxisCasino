#!/usr/bin/env python3
"""
Test script to verify Mini App Centre functionality
"""

import asyncio
import aiosqlite
from datetime import datetime

async def test_mini_app_centre():
    """Test the Mini App Centre functionality"""
    print("🧪 Testing Mini App Centre...")
    
    # Test database operations that the Mini App Centre uses
    db_path = "casino.db"
    test_user_id = 999999
    
    try:
        # Test database connection
        async with aiosqlite.connect(db_path) as db:
            # Test user creation (same as Mini App Centre)
            current_time = datetime.now().isoformat()
            await db.execute("""
                INSERT OR IGNORE INTO users 
                (id, username, balance, created_at, last_active) 
                VALUES (?, ?, ?, ?, ?)
            """, (test_user_id, "test_user", 1000, current_time, current_time))
            await db.commit()
            
            # Test user retrieval (same as Mini App Centre)
            db.row_factory = aiosqlite.Row
            cur = await db.execute("""
                SELECT id, username, balance, games_played, total_wagered, total_won, created_at, last_active 
                FROM users WHERE id = ?
            """, (test_user_id,))
            row = await cur.fetchone()
            
            if row:
                user_data = dict(row)
                print(f"✅ Database operations working - User: {user_data['username']}, Balance: {user_data['balance']}")
                
                # Clean up test user
                await db.execute("DELETE FROM users WHERE id = ?", (test_user_id,))
                await db.commit()
                
                return True
            else:
                print("❌ Database test failed - No user found")
                return False
                
    except Exception as e:
        print(f"❌ Database test error: {e}")
        return False

async def test_webapp_url():
    """Test WebApp URL accessibility"""
    import aiohttp
    
    print("🧪 Testing WebApp URL accessibility...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:5001/") as response:
                if response.status == 200:
                    content = await response.text()
                    if "Stake Casino" in content:
                        print("✅ WebApp URL accessible and serving Mini App")
                        return True
                    else:
                        print("⚠️ WebApp URL accessible but content might be wrong")
                        return False
                else:
                    print(f"❌ WebApp URL returned status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ WebApp URL test error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🎰 Mini App Centre - Component Tests")
    print("="*40)
    
    tests = [
        ("Database Operations", test_mini_app_centre()),
        ("WebApp URL", test_webapp_url())
    ]
    
    results = []
    for test_name, test_coro in tests:
        print(f"\n🔍 Testing {test_name}...")
        result = await test_coro
        results.append((test_name, result))
    
    # Results
    print("\n" + "="*40)
    print("📊 TEST RESULTS:")
    print("="*40)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Mini App Centre should be working.")
        print("\nNext steps to test:")
        print("1. Send /start to your Telegram bot")
        print("2. Click '🎮 Mini App Centre'")
        print("3. Click '🚀 PLAY IN WEBAPP'")
    else:
        print(f"\n❌ {total - passed} test(s) failed. Check the issues above.")

if __name__ == "__main__":
    asyncio.run(main())
