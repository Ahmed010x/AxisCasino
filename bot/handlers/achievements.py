# bot/handlers/achievements.py
"""
Achievement System
Gamification features to increase user engagement
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Achievement definitions
ACHIEVEMENTS = {
    'first_game': {
        'name': '🎰 First Spin',
        'description': 'Play your first game',
        'reward': 5.0,
        'condition': lambda stats: stats['games_played'] >= 1
    },
    'big_winner': {
        'name': '💰 Big Winner',
        'description': 'Win $100 in a single game',
        'reward': 25.0,
        'condition': lambda stats: stats['biggest_win'] >= 100
    },
    'hot_streak_3': {
        'name': '🔥 Hot Streak',
        'description': 'Win 3 games in a row',
        'reward': 10.0,
        'condition': lambda stats: stats['max_win_streak'] >= 3
    },
    'hot_streak_5': {
        'name': '🔥🔥 Blazing Streak',
        'description': 'Win 5 games in a row',
        'reward': 30.0,
        'condition': lambda stats: stats['max_win_streak'] >= 5
    },
    'high_roller': {
        'name': '💎 High Roller',
        'description': 'Place a $500 bet',
        'reward': 50.0,
        'condition': lambda stats: stats['biggest_bet'] >= 500
    },
    'dedicated_player': {
        'name': '🎮 Dedicated Player',
        'description': 'Play 100 games',
        'reward': 50.0,
        'condition': lambda stats: stats['games_played'] >= 100
    },
    'casino_veteran': {
        'name': '🏆 Casino Veteran',
        'description': 'Play 500 games',
        'reward': 200.0,
        'condition': lambda stats: stats['games_played'] >= 500
    },
    'profit_king': {
        'name': '📈 Profit King',
        'description': 'Reach $1000 total profit',
        'reward': 100.0,
        'condition': lambda stats: stats['net_profit'] >= 1000
    },
    'wagering_champion': {
        'name': '💸 Wagering Champion',
        'description': 'Wager $10,000 total',
        'reward': 150.0,
        'condition': lambda stats: stats['total_wagered'] >= 10000
    },
    'prediction_master': {
        'name': '🔮 Prediction Master',
        'description': 'Win 50 Prediction games',
        'reward': 40.0,
        'condition': lambda stats: stats.get('prediction_wins', 0) >= 50
    },
    'referral_pro': {
        'name': '👥 Referral Pro',
        'description': 'Refer 10 friends',
        'reward': 100.0,
        'condition': lambda stats: stats.get('referral_count', 0) >= 10
    },
    'early_bird': {
        'name': '🌅 Early Bird',
        'description': 'Play a game before 8 AM',
        'reward': 15.0,
        'condition': lambda stats: stats.get('played_early_morning', False)
    },
    'night_owl': {
        'name': '🦉 Night Owl',
        'description': 'Play a game after midnight',
        'reward': 15.0,
        'condition': lambda stats: stats.get('played_late_night', False)
    },
    'deposit_master': {
        'name': '💳 Deposit Master',
        'description': 'Make your first deposit',
        'reward': 20.0,
        'condition': lambda stats: stats.get('total_deposited', 0) > 0
    },
    'withdrawal_success': {
        'name': '🏦 Cashout King',
        'description': 'Make your first withdrawal',
        'reward': 25.0,
        'condition': lambda stats: stats.get('total_withdrawn', 0) > 0
    }
}

async def check_and_award_achievements(user_id: int, context: ContextTypes.DEFAULT_TYPE = None):
    """Check if user has unlocked any new achievements"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, update_balance, DB_PATH
    import aiosqlite
    
    user = await get_user(user_id)
    if not user:
        return []
    
    # Get user statistics
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Get existing achievements
            cursor = await db.execute("""
                SELECT achievement_id FROM user_achievements
                WHERE user_id = ?
            """, (user_id,))
            unlocked_ids = [row[0] for row in await cursor.fetchall()]
            
            # Get game statistics
            cursor = await db.execute("""
                SELECT 
                    MAX(bet_amount) as biggest_bet,
                    SUM(CASE WHEN game_type = 'prediction' AND win_amount > bet_amount THEN 1 ELSE 0 END) as prediction_wins,
                    SUM(win_amount - bet_amount) as net_profit
                FROM game_sessions
                WHERE user_id = ?
            """, (user_id,))
            game_stats = await cursor.fetchone()
            
            # Build stats dictionary
            stats = {
                'games_played': user.get('games_played', 0),
                'biggest_win': user.get('biggest_win', 0.0),
                'max_win_streak': user.get('max_win_streak', 0),
                'total_wagered': user.get('total_wagered', 0.0),
                'biggest_bet': game_stats[0] if game_stats and game_stats[0] else 0.0,
                'prediction_wins': game_stats[1] if game_stats and game_stats[1] else 0,
                'net_profit': game_stats[2] if game_stats and game_stats[2] else 0.0,
                'referral_count': user.get('referral_count', 0),
                'total_deposited': user.get('total_deposited', 0.0),
                'total_withdrawn': user.get('total_withdrawn', 0.0)
            }
            
            # Check each achievement
            newly_unlocked = []
            for achievement_id, achievement in ACHIEVEMENTS.items():
                if achievement_id not in unlocked_ids:
                    if achievement['condition'](stats):
                        # Unlock achievement
                        await db.execute("""
                            INSERT INTO user_achievements 
                            (user_id, achievement_id, achievement_name, description, reward_amount)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            user_id,
                            achievement_id,
                            achievement['name'],
                            achievement['description'],
                            achievement['reward']
                        ))
                        
                        # Award reward
                        await update_balance(user_id, achievement['reward'])
                        
                        newly_unlocked.append(achievement)
                        
                        logger.info(f"User {user_id} unlocked achievement: {achievement['name']}")
            
            await db.commit()
            
            # Notify user if context is available
            if newly_unlocked and context:
                for achievement in newly_unlocked:
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"🎉 <b>ACHIEVEMENT UNLOCKED!</b> 🎉\n\n"
                                 f"{achievement['name']}\n"
                                 f"<i>{achievement['description']}</i>\n\n"
                                 f"💰 Reward: ${achievement['reward']:.2f}",
                            parse_mode=ParseMode.HTML
                        )
                    except Exception as e:
                        logger.error(f"Error sending achievement notification: {e}")
            
            return newly_unlocked
            
    except Exception as e:
        logger.error(f"Error checking achievements: {e}")
        return []

async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's achievements"""
    query = update.callback_query
    if query:
        await query.answer()
        user_id = query.from_user.id
        message_edit = True
    else:
        user_id = update.message.from_user.id
        message_edit = False
    
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, DB_PATH
    import aiosqlite
    
    user = await get_user(user_id)
    if not user:
        text = "❌ User not found. Please use /start"
        if message_edit:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Get unlocked achievements
            cursor = await db.execute("""
                SELECT achievement_id, achievement_name, reward_amount, unlocked_at
                FROM user_achievements
                WHERE user_id = ?
                ORDER BY unlocked_at DESC
            """, (user_id,))
            unlocked = await cursor.fetchall()
            
            unlocked_ids = [row[0] for row in unlocked]
            total_rewards = sum(row[2] for row in unlocked)
            
    except Exception as e:
        logger.error(f"Error fetching achievements: {e}")
        unlocked = []
        unlocked_ids = []
        total_rewards = 0.0
    
    # Build message
    text = f"""
🏆 <b>ACHIEVEMENTS</b> 🏆

Unlocked: {len(unlocked)}/{len(ACHIEVEMENTS)}
Total Rewards: ${total_rewards:.2f}

"""
    
    if unlocked:
        text += "✅ <b>UNLOCKED</b>\n"
        for ach in unlocked[:10]:  # Show last 10
            unlock_date = datetime.fromisoformat(ach[3]).strftime('%b %d')
            text += f"{ach[1]} - ${ach[2]:.0f} ({unlock_date})\n"
        
        if len(unlocked) > 10:
            text += f"\n<i>...and {len(unlocked) - 10} more</i>\n"
    
    # Show locked achievements
    locked = [a for aid, a in ACHIEVEMENTS.items() if aid not in unlocked_ids]
    if locked:
        text += "\n🔒 <b>LOCKED</b>\n"
        for achievement in locked[:5]:  # Show first 5
            text += f"{achievement['name']} - ${achievement['reward']:.0f}\n<i>{achievement['description']}</i>\n\n"
        
        if len(locked) > 5:
            text += f"<i>...and {len(locked) - 5} more to unlock!</i>\n"
    
    text += "\n💡 <i>Complete achievements to earn rewards!</i>"
    
    # Create keyboard
    keyboard = [
        [InlineKeyboardButton("📊 Your Stats", callback_data="stats")],
        [InlineKeyboardButton("🎮 Play Games", callback_data="games")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="start")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if message_edit:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
