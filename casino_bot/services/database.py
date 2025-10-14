"""
Database service for the casino bot
"""

import logging
import sqlite3
import aiosqlite
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from ..core.config import config

logger = logging.getLogger(__name__)

class DatabaseService:
    """Database operations service"""
    
    def __init__(self):
        self.db_path = config.DB_PATH
    
    async def init_db(self):
        """Initialize the database with required tables"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Enhanced Users table with comprehensive tracking
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT NOT NULL,
                        first_name TEXT,
                        last_name TEXT,
                        balance REAL DEFAULT 0.0,
                        games_played INTEGER DEFAULT 0,
                        total_wagered REAL DEFAULT 0.0,
                        total_won REAL DEFAULT 0.0,
                        total_deposited REAL DEFAULT 0.0,
                        total_withdrawn REAL DEFAULT 0.0,
                        win_streak INTEGER DEFAULT 0,
                        max_win_streak INTEGER DEFAULT 0,
                        loss_streak INTEGER DEFAULT 0,
                        max_loss_streak INTEGER DEFAULT 0,
                        biggest_win REAL DEFAULT 0.0,
                        biggest_loss REAL DEFAULT 0.0,
                        vip_level INTEGER DEFAULT 0,
                        loyalty_points REAL DEFAULT 0.0,
                        referral_code TEXT DEFAULT NULL,
                        referred_by TEXT DEFAULT NULL,
                        referral_earnings REAL DEFAULT 0.0,
                        referral_count INTEGER DEFAULT 0,
                        last_weekly_bonus TEXT DEFAULT NULL,
                        is_banned BOOLEAN DEFAULT FALSE,
                        ban_reason TEXT DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_game_at TIMESTAMP DEFAULT NULL,
                        timezone TEXT DEFAULT 'UTC'
                    )
                """)
                
                # Game sessions table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS game_sessions (
                        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        game_type TEXT NOT NULL,
                        game_variant TEXT DEFAULT NULL,
                        bet_amount REAL NOT NULL,
                        win_amount REAL DEFAULT 0.0,
                        net_result REAL DEFAULT 0.0,
                        multiplier REAL DEFAULT 0.0,
                        game_data TEXT DEFAULT NULL,
                        result TEXT,
                        is_jackpot BOOLEAN DEFAULT FALSE,
                        house_edge REAL DEFAULT 0.0,
                        rtp REAL DEFAULT 0.0,
                        session_duration INTEGER DEFAULT 0,
                        ip_address TEXT DEFAULT NULL,
                        user_agent TEXT DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Transactions table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        subtype TEXT DEFAULT NULL,
                        amount REAL NOT NULL,
                        currency TEXT DEFAULT 'USD',
                        crypto_asset TEXT DEFAULT NULL,
                        crypto_amount REAL DEFAULT NULL,
                        exchange_rate REAL DEFAULT NULL,
                        fee_amount REAL DEFAULT 0.0,
                        net_amount REAL DEFAULT NULL,
                        balance_before REAL DEFAULT 0.0,
                        balance_after REAL DEFAULT 0.0,
                        reference_id TEXT DEFAULT NULL,
                        game_session_id INTEGER DEFAULT NULL,
                        status TEXT DEFAULT 'completed',
                        payment_method TEXT DEFAULT NULL,
                        payment_address TEXT DEFAULT NULL,
                        confirmation_blocks INTEGER DEFAULT NULL,
                        description TEXT,
                        metadata TEXT DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        confirmed_at TIMESTAMP DEFAULT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        FOREIGN KEY (game_session_id) REFERENCES game_sessions (session_id)
                    )
                """)
                
                # Withdrawals table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS withdrawals (
                        withdrawal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        asset TEXT NOT NULL,
                        amount REAL NOT NULL,
                        amount_usd REAL NOT NULL,
                        address TEXT NOT NULL,
                        fee REAL NOT NULL,
                        fee_usd REAL NOT NULL,
                        net_amount REAL NOT NULL,
                        net_amount_usd REAL NOT NULL,
                        rate_usd REAL NOT NULL,
                        status TEXT DEFAULT 'pending',
                        transaction_hash TEXT DEFAULT '',
                        confirmation_blocks INTEGER DEFAULT 0,
                        required_confirmations INTEGER DEFAULT 6,
                        error_msg TEXT DEFAULT '',
                        admin_notes TEXT DEFAULT '',
                        processed_by INTEGER DEFAULT NULL,
                        priority INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_at TIMESTAMP DEFAULT NULL,
                        confirmed_at TIMESTAMP DEFAULT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Deposits table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS deposits (
                        deposit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        asset TEXT NOT NULL,
                        amount REAL NOT NULL,
                        amount_usd REAL NOT NULL,
                        rate_usd REAL NOT NULL,
                        payment_method TEXT NOT NULL,
                        payment_address TEXT DEFAULT NULL,
                        invoice_id TEXT DEFAULT NULL,
                        transaction_hash TEXT DEFAULT NULL,
                        confirmation_blocks INTEGER DEFAULT 0,
                        required_confirmations INTEGER DEFAULT 6,
                        status TEXT DEFAULT 'pending',
                        expires_at TIMESTAMP DEFAULT NULL,
                        bonus_applied REAL DEFAULT 0.0,
                        bonus_type TEXT DEFAULT NULL,
                        metadata TEXT DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        confirmed_at TIMESTAMP DEFAULT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # House balance table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS house_balance (
                        id INTEGER PRIMARY KEY,
                        balance REAL DEFAULT 10000.0,
                        total_player_losses REAL DEFAULT 0.0,
                        total_player_wins REAL DEFAULT 0.0,
                        total_deposits REAL DEFAULT 0.0,
                        total_withdrawals REAL DEFAULT 0.0,
                        total_fees_collected REAL DEFAULT 0.0,
                        total_bonuses_paid REAL DEFAULT 0.0,
                        games_played_today INTEGER DEFAULT 0,
                        revenue_today REAL DEFAULT 0.0,
                        profit_today REAL DEFAULT 0.0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_daily_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Referrals table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS referrals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        referrer_id INTEGER NOT NULL,
                        referee_id INTEGER NOT NULL,
                        referral_code TEXT NOT NULL,
                        bonus_paid_referrer REAL DEFAULT 0.0,
                        bonus_paid_referee REAL DEFAULT 0.0,
                        total_referee_wagered REAL DEFAULT 0.0,
                        commission_earned REAL DEFAULT 0.0,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        activated_at TIMESTAMP DEFAULT NULL,
                        FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                        FOREIGN KEY (referee_id) REFERENCES users (user_id),
                        UNIQUE(referee_id)
                    )
                """)
                
                # Create indexes for better performance
                await self._create_indexes(db)
                
                # Initialize house balance if it doesn't exist
                await db.execute("""
                    INSERT OR IGNORE INTO house_balance (id, balance) VALUES (1, 10000.0)
                """)
                
                await db.commit()
                logger.info("✅ Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    async def _create_indexes(self, db):
        """Create database indexes for better performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
            "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_game_sessions_user_id ON game_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_game_sessions_game_type ON game_sessions(game_type)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)",
            "CREATE INDEX IF NOT EXISTS idx_withdrawals_user_id ON withdrawals(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status)",
            "CREATE INDEX IF NOT EXISTS idx_deposits_user_id ON deposits(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_deposits_status ON deposits(status)",
            "CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id)",
        ]
        
        for index_sql in indexes:
            await db.execute(index_sql)
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data from database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM users WHERE user_id = ?", (user_id,)
                )
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def create_user(self, user_id: int, username: str, first_name: str = None, last_name: str = None) -> bool:
        """Create a new user in the database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                """, (user_id, username, first_name, last_name))
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return False
    
    async def update_balance(self, user_id: int, amount: float, transaction_type: str = None) -> bool:
        """Update user balance"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get current balance
                cursor = await db.execute(
                    "SELECT balance FROM users WHERE user_id = ?", (user_id,)
                )
                result = await cursor.fetchone()
                if not result:
                    return False
                
                old_balance = result[0]
                new_balance = old_balance + amount
                
                # Update balance
                await db.execute("""
                    UPDATE users SET balance = ?, last_active = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (new_balance, user_id))
                
                # Record transaction if type specified
                if transaction_type:
                    await db.execute("""
                        INSERT INTO transactions 
                        (user_id, type, amount, balance_before, balance_after, description)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (user_id, transaction_type, amount, old_balance, new_balance, 
                          f"{transaction_type.title()} transaction"))
                
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating balance for user {user_id}: {e}")
            return False
    
    async def get_user_stats(self, user_id: int) -> Optional[Dict]:
        """Get user statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT 
                        games_played, total_wagered, total_won,
                        win_streak, max_win_streak, biggest_win,
                        vip_level, loyalty_points
                    FROM users WHERE user_id = ?
                """, (user_id,))
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting user stats for {user_id}: {e}")
            return None

# Global database service instance
db_service = DatabaseService()
