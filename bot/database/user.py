"""
User database operations.

Handles all user-related database operations like creating users,
updating balances, and retrieving user statistics.
"""

import aiosqlite
from typing import Optional, Dict, Any
from bot.database.db import get_db, DATABASE_PATH


async def create_user(user_id: int, username: str) -> bool:
    """Create a new user if they don't exist."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )
            await db.commit()
            return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user data by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def update_balance(user_id: int, new_balance: int) -> bool:
    """Update user's balance."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                "UPDATE users SET balance = ? WHERE user_id = ?",
                (new_balance, user_id)
            )
            await db.commit()
            return True
        except Exception as e:
            print(f"Error updating balance: {e}")
            return False


async def update_last_daily(user_id: int, timestamp: str) -> bool:
    """Update user's last daily bonus claim timestamp."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                "UPDATE users SET last_daily = ? WHERE user_id = ?",
                (timestamp, user_id)
            )
            await db.commit()
            return True
        except Exception as e:
            print(f"Error updating last daily: {e}")
            return False


async def add_game_result(user_id: int, game_type: str, bet_amount: int, 
                         win_amount: int, result: str) -> bool:
    """Add a game result to history and update user stats."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            # Add to game history
            await db.execute(
                """INSERT INTO game_history 
                   (user_id, game_type, bet_amount, win_amount, result) 
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, game_type, bet_amount, win_amount, result)
            )
            
            # Update user stats
            is_win = win_amount > bet_amount
            
            # Update general stats
            if is_win:
                await db.execute(
                    """UPDATE users SET 
                       total_games = total_games + 1,
                       wins = wins + 1,
                       total_winnings = total_winnings + ?,
                       balance = balance + ?
                       WHERE user_id = ?""",
                    (win_amount - bet_amount, win_amount - bet_amount, user_id)
                )
            else:
                await db.execute(
                    """UPDATE users SET 
                       total_games = total_games + 1,
                       total_losses = total_losses + ?,
                       balance = balance - ?
                       WHERE user_id = ?""",
                    (bet_amount, bet_amount, user_id)
                )
            
            # Update game-specific stats
            game_column = f"{game_type}_played"
            await db.execute(
                f"UPDATE users SET {game_column} = {game_column} + 1 WHERE user_id = ?",
                (user_id,)
            )
            
            await db.commit()
            return True
        except Exception as e:
            print(f"Error adding game result: {e}")
            return False


async def get_user_stats(user_id: int) -> Optional[Dict[str, Any]]:
    """Get comprehensive user statistics."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT balance, total_games, wins, total_winnings, total_losses,
                      slots_played, blackjack_played, roulette_played, dice_played
               FROM users WHERE user_id = ?""", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def save_game_session(session_id: str, user_id: int, game_type: str, 
                           game_data: str, bet_amount: int) -> bool:
    """Save an ongoing game session."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                """INSERT OR REPLACE INTO game_sessions 
                   (session_id, user_id, game_type, game_data, bet_amount) 
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, user_id, game_type, game_data, bet_amount)
            )
            await db.commit()
            return True
        except Exception as e:
            print(f"Error saving game session: {e}")
            return False


async def get_game_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get an ongoing game session."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM game_sessions WHERE session_id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def delete_game_session(session_id: str) -> bool:
    """Delete a completed game session."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                "DELETE FROM game_sessions WHERE session_id = ?", (session_id,)
            )
            await db.commit()
            return True
        except Exception as e:
            print(f"Error deleting game session: {e}")
            return False
