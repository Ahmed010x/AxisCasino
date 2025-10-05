"""
Account Management Handlers

Handles user account related commands like balance, daily bonus, and statistics.
"""

from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from bot.database.user import get_user, update_balance, get_user_stats, update_last_daily


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
 """Handle the /balance command."""
 user_id = update.effective_user.id
 user_data = await get_user(user_id)
 
 if not user_data:
 await update.message.reply_text("❌ User not found. Please use /start first.")
 return
 
 balance_text = f"""
<b>Your Casino Balance</b>

Current Balance: </b>{user_data['balance']} chips</b>
Total Games Played: </b>{user_data.get('games_played', 0)}</b>
Total Winnings: </b>{user_data.get('total_winnings', 0)} chips</b>

Keep playing to earn more chips!
"""
 
 await update.message.reply_text(balance_text, parse_mode='Markdown')


async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
 """Handle the /daily command for daily bonus."""
 user_id = update.effective_user.id
 user_data = await get_user(user_id)
 
 if not user_data:
 await update.message.reply_text("❌ User not found. Please use /start first.")
 return
 
 # Check if user already claimed today
 last_daily = user_data.get('last_daily')
 now = datetime.now()
 
 if last_daily:
 last_daily_date = datetime.fromisoformat(last_daily)
 if (now - last_daily_date).days == 0:
 next_claim = last_daily_date + timedelta(days=1)
 hours_left = int((next_claim - now).total_seconds() / 3600)
 await update.message.reply_text(
 f"You already claimed your daily bonus today!\n"
 f"Come back in {hours_left} hours for your next bonus."
 )
 return
 
 # Give daily bonus
 bonus_amount = 500
 await update_balance(user_id, user_data['balance'] + bonus_amount)
 await update_last_daily(user_id, now.isoformat())
 
 bonus_text = f"""
🎁 </b>Daily Bonus Claimed!</b>

You received: </b>{bonus_amount} chips</b>
New Balance: </b>{user_data['balance'] + bonus_amount} chips</b>

Come back tomorrow for another bonus! 
"""
 
 await update.message.reply_text(bonus_text, parse_mode='Markdown')


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
 """Handle the /stats command."""
 user_id = update.effective_user.id
 user_stats = await get_user_stats(user_id)
 
 if not user_stats:
 await update.message.reply_text("❌ No statistics found. Start playing some games!")
 return
 
 # Calculate win rate
 total_games = user_stats.get('total_games', 0)
 wins = user_stats.get('wins', 0)
 win_rate = (wins / total_games * 100) if total_games > 0 else 0
 
 stats_text = f"""
<b>Your Casino Statistics</b>

<b>Overall Stats:</b>
Total Games Played: </b>{total_games}</b>
Games Won: </b>{wins}</b>
Games Lost: </b>{total_games - wins}</b>
Win Rate: </b>{win_rate:.1f}%</b>

<b>Financial Stats:</b>
Current Balance: </b>{user_stats.get('balance', 0)} chips</b>
Total Winnings: </b>{user_stats.get('total_winnings', 0)} chips</b>
Total Losses: </b>{user_stats.get('total_losses', 0)} chips</b>
Net Profit: </b>{user_stats.get('total_winnings', 0) - user_stats.get('total_losses', 0)} chips</b>

<b>Game Breakdown:</b>
Slots: </b>{user_stats.get('slots_played', 0)} games</b>
Blackjack: </b>{user_stats.get('blackjack_played', 0)} games</b>
Roulette: </b>{user_stats.get('roulette_played', 0)} games</b>
Dice: </b>{user_stats.get('dice_played', 0)} games</b>

Keep playing to improve your stats! 🍀
"""
 
 await update.message.reply_text(stats_text, parse_mode='Markdown')
