#!/usr/bin/env python3
"""
Database migration script to fix schema incompatibility
"""
import asyncio
import aiosqlite
import shutil
from datetime import datetime

DB_PATH = "casino.db"
BACKUP_PATH = f"casino_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

async def migrate_database():
    """Migrate database to use user_id instead of id"""
    print("🔧 Database Migration Starting...")
    print("=" * 40)
    
    # 1. Create backup
    print(f"\n📁 Creating backup: {BACKUP_PATH}")
    try:
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print("   Backup created successfully ✅")
    except Exception as e:
        print(f"   Backup failed: {e} ❌")
        return False
    
    # 2. Read existing data
    print("\n📖 Reading existing user data...")
    users_data = []
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT id, username, balance, total_wagered, total_won, 
                       games_played, vip_level, created_at, last_active,
                       is_banned, referrer_id, daily_bonus_claimed,
                       security_level, weekly_bonus_claimed, total_deposited,
                       deposit_count, last_deposit_amount, last_deposit_date,
                       vip_tier, ai_preferences
                FROM users
            """)
            rows = await cursor.fetchall()
            
            for row in rows:
                users_data.append({
                    'user_id': row[0],
                    'username': row[1] or 'unknown',
                    'balance': float(row[2] or 0) / 100000000.0,  # Convert from satoshis to LTC
                    'total_wagered': float(row[3] or 0) / 100000000.0,
                    'total_won': float(row[4] or 0) / 100000000.0,
                    'games_played': row[5] or 0,
                    'created_at': row[7] or datetime.now().isoformat(),
                    'last_active': row[8] or datetime.now().isoformat()
                })
            
            print(f"   Read {len(users_data)} users ✅")
            for user in users_data:
                print(f"     User {user['user_id']}: {user['username']}, Balance: {user['balance']:.8f} LTC")
                
    except Exception as e:
        print(f"   Reading data failed: {e} ❌")
        return False
    
    # 3. Drop old tables and create new schema
    print("\n🔧 Updating database schema...")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Drop existing tables
            await db.execute("DROP TABLE IF EXISTS users")
            await db.execute("DROP TABLE IF EXISTS withdrawals")
            await db.execute("DROP TABLE IF EXISTS game_sessions")
            
            # Create new schema with correct column names
            await db.execute("""
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    balance REAL DEFAULT 0.0,
                    games_played INTEGER DEFAULT 0,
                    total_wagered REAL DEFAULT 0.0,
                    total_withdrawn REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.execute("""
                CREATE TABLE withdrawals (
                    withdrawal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    asset TEXT NOT NULL,
                    amount REAL NOT NULL,
                    address TEXT NOT NULL,
                    fee REAL NOT NULL,
                    net_amount REAL NOT NULL,
                    rate_usd REAL NOT NULL,
                    amount_usd REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    transaction_hash TEXT DEFAULT '',
                    error_msg TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            await db.execute("""
                CREATE TABLE game_sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    game_type TEXT NOT NULL,
                    bet_amount REAL NOT NULL,
                    win_amount REAL DEFAULT 0.0,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            await db.commit()
            print("   New schema created ✅")
            
    except Exception as e:
        print(f"   Schema update failed: {e} ❌")
        return False
    
    # 4. Insert migrated data
    print("\n📝 Inserting migrated user data...")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            for user in users_data:
                await db.execute("""
                    INSERT INTO users 
                    (user_id, username, balance, games_played, total_wagered, total_withdrawn, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user['user_id'],
                    user['username'], 
                    user['balance'],
                    user['games_played'],
                    user['total_wagered'],
                    user['total_won'],  # Using total_won as total_withdrawn for now
                    user['created_at'],
                    user['last_active']
                ))
            
            await db.commit()
            print(f"   Inserted {len(users_data)} users ✅")
            
    except Exception as e:
        print(f"   Data insertion failed: {e} ❌")
        return False
    
    # 5. Verify migration
    print("\n✅ Verifying migration...")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            count = (await cursor.fetchone())[0]
            print(f"   Users in new database: {count}")
            
            cursor = await db.execute("SELECT user_id, username, balance FROM users LIMIT 5")
            samples = await cursor.fetchall()
            print("   Sample users:")
            for sample in samples:
                print(f"     User {sample[0]}: {sample[1]}, Balance: {sample[2]:.8f} LTC")
                
    except Exception as e:
        print(f"   Verification failed: {e} ❌")
        return False
    
    print(f"\n🎉 Migration completed successfully!")
    print(f"   Backup saved as: {BACKUP_PATH}")
    print(f"   Database ready for casino bot!")
    return True

async def main():
    success = await migrate_database()
    if not success:
        print(f"\n❌ Migration failed. Database backup available at: {BACKUP_PATH}")
    else:
        print(f"\n✅ Database is now compatible with the casino bot!")

if __name__ == "__main__":
    asyncio.run(main())
