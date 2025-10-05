"""
Database initialization and management.

Handles SQLite database setup and connection management.
"""

import aiosqlite
import os
from typing import Optional

DATABASE_PATH = os.getenv('DATABASE_URL', 'casino.db')


async def init_db() -> None:
    """Initialize the database with required tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 1000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_daily TEXT,
                total_games INTEGER DEFAULT 0,
                total_winnings INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                slots_played INTEGER DEFAULT 0,
                blackjack_played INTEGER DEFAULT 0,
                roulette_played INTEGER DEFAULT 0,
                dice_played INTEGER DEFAULT 0
            )
        """)
        
        # Game sessions table (for ongoing games like blackjack)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER,
                game_type TEXT,
                game_data TEXT,
                bet_amount INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Game history table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                game_type TEXT,
                bet_amount INTEGER,
                win_amount INTEGER,
                result TEXT,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Payment transactions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                transaction_type TEXT, -- 'deposit', 'withdrawal', 'bonus', 'game_win', 'game_loss'
                amount INTEGER,
                status TEXT DEFAULT 'pending', -- 'pending', 'completed', 'failed', 'cancelled'
                payment_method TEXT, -- 'crypto', 'card', 'paypal', 'telegram_stars'
                transaction_id TEXT UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Payment methods table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payment_methods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                method_type TEXT, -- 'crypto', 'card', 'paypal'
                method_data TEXT, -- JSON data for payment method
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        await db.commit()


async def get_db() -> aiosqlite.Connection:
    """Get database connection."""
    return await aiosqlite.connect(DATABASE_PATH)


async def close_db(db: aiosqlite.Connection) -> None:
    """Close database connection."""
    await db.close()
