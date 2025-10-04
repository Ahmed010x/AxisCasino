# bot/handlers/statistics.py
"""
Enhanced Statistics Handler
Provides detailed player statistics, analytics, and insights
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show enhanced player statistics"""
    query = update.callback_query
    if query:
        await query.answer()
        user_id = query.from_user.id
        message_edit = True
    else:
        user_id = update.message.from_user.id
        message_edit = False
    
    # Import here to avoid circular dependency
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, format_usd
    import aiosqlite
    
    user = await get_user(user_id)
    if not user:
        text = "❌ User not found. Please use /start"
        if message_edit:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return
    
    # Get database path
    from main import DB_PATH
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Get game statistics
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total_games,
                    SUM(bet_amount) as total_wagered,
                    SUM(win_amount) as total_won,
                    SUM(win_amount - bet_amount) as net_profit,
                    MAX(win_amount) as biggest_win,
                    game_type,
                    COUNT(CASE WHEN win_amount > bet_amount THEN 1 END) as wins,
                    COUNT(CASE WHEN win_amount < bet_amount THEN 1 END) as losses
                FROM game_sessions
                WHERE user_id = ?
                GROUP BY user_id
            """, (user_id,))
            overall_stats = await cursor.fetchone()
            
            # Get game breakdown
            cursor = await db.execute("""
                SELECT 
                    game_type,
                    COUNT(*) as plays,
                    SUM(win_amount - bet_amount) as profit,
                    COUNT(CASE WHEN win_amount > bet_amount THEN 1 END) as wins
                FROM game_sessions
                WHERE user_id = ?
                GROUP BY game_type
                ORDER BY plays DESC
                LIMIT 5
            """, (user_id,))
            game_breakdown = await cursor.fetchall()
            
            # Get recent streak
            cursor = await db.execute("""
                SELECT 
                    CASE WHEN win_amount > bet_amount THEN 1 ELSE 0 END as won
                FROM game_sessions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (user_id,))
            recent_games = await cursor.fetchall()
            
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        overall_stats = None
        game_breakdown = []
        recent_games = []
    
    # Format balance
    balance_str = await format_usd(user['balance'])
    
    # Calculate stats
    total_games = user.get('games_played', 0) or (overall_stats[0] if overall_stats else 0)
    total_wagered = user.get('total_wagered', 0.0) or (overall_stats[1] if overall_stats and overall_stats[1] else 0.0)
    total_won = user.get('total_won', 0.0) or (overall_stats[2] if overall_stats and overall_stats[2] else 0.0)
    net_profit = (overall_stats[3] if overall_stats and overall_stats[3] else 0.0)
    biggest_win = user.get('biggest_win', 0.0) or (overall_stats[4] if overall_stats and overall_stats[4] else 0.0)
    
    wins = overall_stats[6] if overall_stats else 0
    losses = overall_stats[7] if overall_stats else 0
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    
    # Calculate current streak
    current_streak = 0
    streak_type = "neutral"
    if recent_games:
        for game in recent_games:
            if current_streak == 0:
                current_streak = 1
                streak_type = "win" if game[0] == 1 else "loss"
            elif (streak_type == "win" and game[0] == 1) or (streak_type == "loss" and game[0] == 0):
                current_streak += 1
            else:
                break
    
    streak_emoji = "🔥" if streak_type == "win" else "❄️" if streak_type == "loss" else "➖"
    profit_emoji = "📈" if net_profit >= 0 else "📉"
    
    # Build statistics message
    text = f"""
📊 <b>YOUR STATISTICS</b> 📊

💰 <b>Balance:</b> {balance_str}
{profit_emoji} <b>Net Profit:</b> ${net_profit:.2f}

🎮 <b>GAME STATS</b>
Total Games: {total_games}
Total Wagered: ${total_wagered:.2f}
Total Won: ${total_won:.2f}

📈 <b>PERFORMANCE</b>
Win Rate: {win_rate:.1f}%
Wins: {wins} | Losses: {losses}
Biggest Win: ${biggest_win:.2f}
{streak_emoji} Current Streak: {current_streak} {streak_type}s

🎯 <b>GAME BREAKDOWN</b>
"""
    
    # Add game breakdown
    if game_breakdown:
        for game in game_breakdown:
            game_name = game[0].replace('_', ' ').title()
            plays = game[1]
            profit = game[2] if game[2] else 0.0
            game_wins = game[3]
            game_win_rate = (game_wins / plays * 100) if plays > 0 else 0
            profit_symbol = "+" if profit >= 0 else ""
            text += f"\n• {game_name}: {plays} plays ({game_win_rate:.0f}% WR) {profit_symbol}${profit:.2f}"
    else:
        text += "\n<i>No games played yet</i>"
    
    # Add account info
    created_at = datetime.fromisoformat(user['created_at']) if user.get('created_at') else datetime.now()
    days_active = (datetime.now() - created_at).days
    
    text += f"""

👤 <b>ACCOUNT INFO</b>
Member since: {created_at.strftime('%b %d, %Y')}
Days active: {days_active}
Total Deposits: ${user.get('total_deposited', 0.0):.2f}
Total Withdrawals: ${user.get('total_withdrawn', 0.0):.2f}

💡 <i>Keep playing to unlock achievements!</i>
"""
    
    # Create keyboard
    keyboard = [
        [InlineKeyboardButton("🎮 Play Games", callback_data="games")],
        [InlineKeyboardButton("🏆 Achievements", callback_data="achievements")],
        [InlineKeyboardButton("📊 Detailed Report", callback_data="detailed_stats")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="start")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if message_edit:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
