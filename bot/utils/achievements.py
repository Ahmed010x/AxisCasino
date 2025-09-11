"""
Achievement System

Tracks and rewards player achievements across all casino games.
"""

from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database.user import get_user, update_balance
import aiosqlite
from bot.database.db import DATABASE_PATH


# Achievement definitions
ACHIEVEMENTS = {
    'first_spin': {
        'name': '🎰 First Spin',
        'description': 'Play your first slot machine',
        'reward': 100,
        'requirement': {'slots_played': 1}
    },
    'slots_veteran': {
        'name': '🎰 Slot Veteran',
        'description': 'Play 50 slot games',
        'reward': 500,
        'requirement': {'slots_played': 50}
    },
    'slots_master': {
        'name': '🎰 Slot Master',
        'description': 'Play 200 slot games',
        'reward': 2000,
        'requirement': {'slots_played': 200}
    },
    'card_shark': {
        'name': '🃏 Card Shark',
        'description': 'Win 10 blackjack games',
        'reward': 300,
        'requirement': {'blackjack_wins': 10}
    },
    'blackjack_pro': {
        'name': '🃏 Blackjack Pro',
        'description': 'Play 100 blackjack games',
        'reward': 1000,
        'requirement': {'blackjack_played': 100}
    },
    'roulette_rookie': {
        'name': '🎲 Roulette Rookie',
        'description': 'Play your first roulette game',
        'reward': 150,
        'requirement': {'roulette_played': 1}
    },
    'high_roller': {
        'name': '💎 High Roller',
        'description': 'Accumulate 10,000+ chips',
        'reward': 1000,
        'requirement': {'max_balance': 10000}
    },
    'millionaire': {
        'name': '💰 Millionaire',
        'description': 'Accumulate 100,000+ chips',
        'reward': 10000,
        'requirement': {'max_balance': 100000}
    },
    'lucky_seven': {
        'name': '🍀 Lucky Seven',
        'description': 'Win 7 games in a row',
        'reward': 777,
        'requirement': {'win_streak': 7}
    },
    'big_winner': {
        'name': '🏆 Big Winner',
        'description': 'Win 1000+ chips in a single game',
        'reward': 500,
        'requirement': {'single_win': 1000}
    },
    'game_master': {
        'name': '🎮 Game Master',
        'description': 'Play all 4 casino games',
        'reward': 800,
        'requirement': {'all_games': True}
    },
    'daily_player': {
        'name': '📅 Daily Player',
        'description': 'Claim daily bonus 7 days in a row',
        'reward': 1000,
        'requirement': {'daily_streak': 7}
    },
    'comeback_kid': {
        'name': '🔄 Comeback Kid',
        'description': 'Win after losing 5 games in a row',
        'reward': 400,
        'requirement': {'comeback': True}
    },
    'dice_master': {
        'name': '🎯 Dice Master',
        'description': 'Win 3 exact number bets in dice',
        'reward': 600,
        'requirement': {'dice_exact_wins': 3}
    }
}


async def init_achievements_db():
    """Initialize achievements table."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                user_id INTEGER,
                achievement_id TEXT,
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, achievement_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_stats_extended (
                user_id INTEGER PRIMARY KEY,
                max_balance INTEGER DEFAULT 0,
                current_win_streak INTEGER DEFAULT 0,
                current_loss_streak INTEGER DEFAULT 0,
                best_win_streak INTEGER DEFAULT 0,
                single_biggest_win INTEGER DEFAULT 0,
                blackjack_wins INTEGER DEFAULT 0,
                dice_exact_wins INTEGER DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                last_game_result TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        await db.commit()


async def get_user_achievements(user_id: int) -> List[str]:
    """Get list of earned achievements for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT achievement_id FROM user_achievements WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            achievements = await cursor.fetchall()
            return [row[0] for row in achievements]


async def award_achievement(user_id: int, achievement_id: str) -> bool:
    """Award an achievement to a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO user_achievements (user_id, achievement_id) VALUES (?, ?)",
                (user_id, achievement_id)
            )
            
            # Give reward chips
            reward = ACHIEVEMENTS[achievement_id]['reward']
            user_data = await get_user(user_id)
            if user_data:
                await update_balance(user_id, user_data['balance'] + reward)
            
            await db.commit()
            return True
        except Exception as e:
            print(f"Error awarding achievement: {e}")
            return False


async def check_achievements(user_id: int) -> List[str]:
    """Check and award any newly earned achievements."""
    user_data = await get_user(user_id)
    if not user_data:
        return []
    
    earned_achievements = await get_user_achievements(user_id)
    newly_earned = []
    
    # Get extended stats
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_stats_extended WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            extended_stats = await cursor.fetchone()
            if extended_stats:
                extended_stats = dict(extended_stats)
            else:
                extended_stats = {}
    
    for achievement_id, achievement in ACHIEVEMENTS.items():
        if achievement_id in earned_achievements:
            continue
        
        requirement = achievement['requirement']
        earned = True
        
        for stat, required_value in requirement.items():
            if stat == 'slots_played':
                if user_data.get('slots_played', 0) < required_value:
                    earned = False
                    break
            elif stat == 'blackjack_played':
                if user_data.get('blackjack_played', 0) < required_value:
                    earned = False
                    break
            elif stat == 'roulette_played':
                if user_data.get('roulette_played', 0) < required_value:
                    earned = False
                    break
            elif stat == 'dice_played':
                if user_data.get('dice_played', 0) < required_value:
                    earned = False
                    break
            elif stat == 'max_balance':
                if extended_stats.get('max_balance', 0) < required_value:
                    earned = False
                    break
            elif stat == 'blackjack_wins':
                if extended_stats.get('blackjack_wins', 0) < required_value:
                    earned = False
                    break
            elif stat == 'win_streak':
                if extended_stats.get('best_win_streak', 0) < required_value:
                    earned = False
                    break
            elif stat == 'single_win':
                if extended_stats.get('single_biggest_win', 0) < required_value:
                    earned = False
                    break
            elif stat == 'dice_exact_wins':
                if extended_stats.get('dice_exact_wins', 0) < required_value:
                    earned = False
                    break
            elif stat == 'all_games':
                games_played = [
                    user_data.get('slots_played', 0) > 0,
                    user_data.get('blackjack_played', 0) > 0,
                    user_data.get('roulette_played', 0) > 0,
                    user_data.get('dice_played', 0) > 0
                ]
                if not all(games_played):
                    earned = False
                    break
        
        if earned:
            await award_achievement(user_id, achievement_id)
            newly_earned.append(achievement_id)
    
    return newly_earned


async def update_extended_stats(user_id: int, game_type: str, won: bool, win_amount: int):
    """Update extended user statistics for achievements."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Ensure user exists in extended stats
        await db.execute(
            "INSERT OR IGNORE INTO user_stats_extended (user_id) VALUES (?)",
            (user_id,)
        )
        
        # Get current stats
        async with db.execute(
            "SELECT * FROM user_stats_extended WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            stats = await cursor.fetchone()
            if stats:
                stats = dict(stats)
            else:
                stats = {}
        
        # Update balance tracking
        user_data = await get_user(user_id)
        current_balance = user_data['balance'] if user_data else 0
        max_balance = max(stats.get('max_balance', 0), current_balance)
        
        # Update win/loss streaks
        if won:
            current_win_streak = stats.get('current_win_streak', 0) + 1
            current_loss_streak = 0
            best_win_streak = max(stats.get('best_win_streak', 0), current_win_streak)
            
            # Track specific wins
            if game_type == 'blackjack':
                blackjack_wins = stats.get('blackjack_wins', 0) + 1
            else:
                blackjack_wins = stats.get('blackjack_wins', 0)
            
            # Track biggest single win
            net_win = win_amount - (win_amount // 2)  # Rough calculation
            single_biggest_win = max(stats.get('single_biggest_win', 0), net_win)
        else:
            current_win_streak = 0
            current_loss_streak = stats.get('current_loss_streak', 0) + 1
            best_win_streak = stats.get('best_win_streak', 0)
            blackjack_wins = stats.get('blackjack_wins', 0)
            single_biggest_win = stats.get('single_biggest_win', 0)
        
        # Update database
        await db.execute("""
            UPDATE user_stats_extended SET
                max_balance = ?,
                current_win_streak = ?,
                current_loss_streak = ?,
                best_win_streak = ?,
                single_biggest_win = ?,
                blackjack_wins = ?,
                last_game_result = ?
            WHERE user_id = ?
        """, (
            max_balance, current_win_streak, current_loss_streak,
            best_win_streak, single_biggest_win, blackjack_wins,
            'win' if won else 'loss', user_id
        ))
        
        await db.commit()


async def show_achievements_menu(update: Update, user_id: int):
    """Show achievements menu."""
    earned_achievements = await get_user_achievements(user_id)
    total_achievements = len(ACHIEVEMENTS)
    earned_count = len(earned_achievements)
    
    # Calculate total rewards earned
    total_rewards = sum(ACHIEVEMENTS[ach]['reward'] for ach in earned_achievements)
    
    achievements_text = f"""
🏆 **ACHIEVEMENTS** 🏆

**Progress:** {earned_count}/{total_achievements} completed
**Total Rewards Earned:** {total_rewards} chips

**Your Achievements:**
"""
    
    # Show earned achievements
    for achievement_id in earned_achievements:
        achievement = ACHIEVEMENTS[achievement_id]
        achievements_text += f"✅ {achievement['name']} - {achievement['reward']} chips\n"
    
    achievements_text += "\n**Available Achievements:**\n"
    
    # Show unearned achievements
    for achievement_id, achievement in ACHIEVEMENTS.items():
        if achievement_id not in earned_achievements:
            achievements_text += f"⭕ {achievement['name']} - {achievement['reward']} chips\n"
            achievements_text += f"   └ {achievement['description']}\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="achievements_refresh")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="help")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(achievements_text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_achievement_notification(update: Update, achievement_ids: List[str]):
    """Show notification for newly earned achievements."""
    if not achievement_ids:
        return
    
    notification_text = "🎉 **NEW ACHIEVEMENT(S) UNLOCKED!** 🎉\n\n"
    
    total_reward = 0
    for achievement_id in achievement_ids:
        achievement = ACHIEVEMENTS[achievement_id]
        notification_text += f"🏆 **{achievement['name']}**\n"
        notification_text += f"   {achievement['description']}\n"
        notification_text += f"   Reward: **{achievement['reward']} chips**\n\n"
        total_reward += achievement['reward']
    
    notification_text += f"**Total Bonus:** {total_reward} chips added to your balance!"
    
    keyboard = [
        [InlineKeyboardButton("🏆 View All Achievements", callback_data="check_achievements")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="help")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send as a new message
    await update.effective_chat.send_message(
        notification_text, 
        reply_markup=reply_markup, 
        parse_mode='Markdown'
    )


async def handle_achievements_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle achievement-related callbacks."""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    if data == "check_achievements":
        await show_achievements_menu(update, user_id)
    elif data == "achievements_refresh":
        # Check for new achievements
        newly_earned = await check_achievements(user_id)
        if newly_earned:
            await show_achievement_notification(update, newly_earned)
        else:
            await query.answer("No new achievements earned yet!")
        
        # Refresh the menu
        await show_achievements_menu(update, user_id)
