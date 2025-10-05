"""
Leaderboard System

Displays top players across various metrics.
"""

from typing import List, Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database.user import get_user
import aiosqlite
from bot.database.db import DATABASE_PATH


async def get_top_players_by_balance(limit: int = 10) -> List[Dict]:
 """Get top players by current balance."""
 async with aiosqlite.connect(DATABASE_PATH) as db:
 db.row_factory = aiosqlite.Row
 async with db.execute(
 """SELECT username, balance, total_games, wins 
 FROM users 
 WHERE total_games > 0
 ORDER BY balance DESC 
 LIMIT ?""", (limit,)
 ) as cursor:
 players = await cursor.fetchall()
 return [dict(row) for row in players]


async def get_top_players_by_games(limit: int = 10) -> List[Dict]:
 """Get most active players by total games played."""
 async with aiosqlite.connect(DATABASE_PATH) as db:
 db.row_factory = aiosqlite.Row
 async with db.execute(
 """SELECT username, balance, total_games, wins 
 FROM users 
 WHERE total_games > 0
 ORDER BY total_games DESC 
 LIMIT ?""", (limit,)
 ) as cursor:
 players = await cursor.fetchall()
 return [dict(row) for row in players]


async def get_top_players_by_winnings(limit: int = 10) -> List[Dict]:
 """Get top players by total winnings."""
 async with aiosqlite.connect(DATABASE_PATH) as db:
 db.row_factory = aiosqlite.Row
 async with db.execute(
 """SELECT username, balance, total_winnings, total_games 
 FROM users 
 WHERE total_games > 0
 ORDER BY total_winnings DESC 
 LIMIT ?""", (limit,)
 ) as cursor:
 players = await cursor.fetchall()
 return [dict(row) for row in players]


async def get_user_rank(user_id: int, metric: str = 'balance') -> Optional[int]:
 """Get user's rank in a specific metric."""
 async with aiosqlite.connect(DATABASE_PATH) as db:
 if metric == 'balance':
 query = """
 SELECT COUNT(*) + 1 as rank
 FROM users 
 WHERE balance > (SELECT balance FROM users WHERE user_id = ?)
 AND total_games > 0
 """
 elif metric == 'games':
 query = """
 SELECT COUNT(*) + 1 as rank
 FROM users 
 WHERE total_games > (SELECT total_games FROM users WHERE user_id = ?)
 AND total_games > 0
 """
 elif metric == 'winnings':
 query = """
 SELECT COUNT(*) + 1 as rank
 FROM users 
 WHERE total_winnings > (SELECT total_winnings FROM users WHERE user_id = ?)
 AND total_games > 0
 """
 else:
 return None
 
 async with db.execute(query, (user_id,)) as cursor:
 result = await cursor.fetchone()
 return result[0] if result else None


async def show_leaderboard_menu(update: Update):
 """Show leaderboard selection menu."""
 leaderboard_text = """
</b>CASINO LEADERBOARDS</b>

Choose which leaderboard to view:
"""
 
 keyboard = [
 [
 InlineKeyboardButton("Richest Players", callback_data="leaderboard_balance"),
 InlineKeyboardButton("Most Active", callback_data="leaderboard_games")
 ],
 [
 InlineKeyboardButton("💎 Biggest Winners", callback_data="leaderboard_winnings"),
 InlineKeyboardButton("My Ranks", callback_data="leaderboard_my_rank")
 ],
 [
 InlineKeyboardButton("🏠 Main Menu", callback_data="help")
 ]
 ]
 
 reply_markup = InlineKeyboardMarkup(keyboard)
 await update.message.reply_text(leaderboard_text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_balance_leaderboard(query):
 """Show richest players leaderboard."""
 players = await get_top_players_by_balance()
 
 leaderboard_text = "</b>RICHEST PLAYERS</b>\n\n"
 
 for i, player in enumerate(players, 1):
 medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
 win_rate = (player['wins'] / player['total_games'] * 100) if player['total_games'] > 0 else 0
 
 leaderboard_text += f"{medal} </b>{player['username']}</b>\n"
 leaderboard_text += f" {player['balance']:,} chips\n"
 leaderboard_text += f" {player['total_games']} games ({win_rate:.1f}% win rate)\n\n"
 
 if not players:
 leaderboard_text += "No players found yet. Start playing to appear here!"
 
 keyboard = [
 [InlineKeyboardButton("Refresh", callback_data="leaderboard_balance")],
 [InlineKeyboardButton("⬅️ Back", callback_data="leaderboard_menu")]
 ]
 
 reply_markup = InlineKeyboardMarkup(keyboard)
 await query.edit_message_text(leaderboard_text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_games_leaderboard(query):
 """Show most active players leaderboard."""
 players = await get_top_players_by_games()
 
 leaderboard_text = "</b>MOST ACTIVE PLAYERS</b>\n\n"
 
 for i, player in enumerate(players, 1):
 medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
 win_rate = (player['wins'] / player['total_games'] * 100) if player['total_games'] > 0 else 0
 
 leaderboard_text += f"{medal} </b>{player['username']}</b>\n"
 leaderboard_text += f" {player['total_games']} games played\n"
 leaderboard_text += f" {player['balance']:,} chips ({win_rate:.1f}% win rate)\n\n"
 
 if not players:
 leaderboard_text += "No players found yet. Start playing to appear here!"
 
 keyboard = [
 [InlineKeyboardButton("Refresh", callback_data="leaderboard_games")],
 [InlineKeyboardButton("⬅️ Back", callback_data="leaderboard_menu")]
 ]
 
 reply_markup = InlineKeyboardMarkup(keyboard)
 await query.edit_message_text(leaderboard_text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_winnings_leaderboard(query):
 """Show biggest winners leaderboard."""
 players = await get_top_players_by_winnings()
 
 leaderboard_text = "💎 </b>BIGGEST WINNERS</b> 💎\n\n"
 
 for i, player in enumerate(players, 1):
 medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
 
 leaderboard_text += f"{medal} </b>{player['username']}</b>\n"
 leaderboard_text += f" 💎 {player['total_winnings']:,} chips won\n"
 leaderboard_text += f" {player['balance']:,} current balance\n"
 leaderboard_text += f" {player['total_games']} games played\n\n"
 
 if not players:
 leaderboard_text += "No players found yet. Start playing to appear here!"
 
 keyboard = [
 [InlineKeyboardButton("Refresh", callback_data="leaderboard_winnings")],
 [InlineKeyboardButton("⬅️ Back", callback_data="leaderboard_menu")]
 ]
 
 reply_markup = InlineKeyboardMarkup(keyboard)
 await query.edit_message_text(leaderboard_text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_user_ranks(query, user_id: int):
 """Show user's ranks across all leaderboards."""
 user_data = await get_user(user_id)
 if not user_data:
 await query.edit_message_text("❌ User not found.")
 return
 
 balance_rank = await get_user_rank(user_id, 'balance')
 games_rank = await get_user_rank(user_id, 'games')
 winnings_rank = await get_user_rank(user_id, 'winnings')
 
 ranks_text = f"""
</b>YOUR LEADERBOARD RANKS</b>

</b>Player:</b> {user_data['username']}
</b>Current Balance:</b> {user_data['balance']:,} chips

</b>Your Rankings:</b>
</b>Richest Players:</b> #{balance_rank or 'N/A'}
</b>Most Active:</b> #{games_rank or 'N/A'}
💎 </b>Biggest Winners:</b> #{winnings_rank or 'N/A'}

</b>Your Stats:</b>
• Total Games: {user_data['total_games']}
• Games Won: {user_data['wins']}
• Total Winnings: {user_data['total_winnings']:,} chips
• Win Rate: {(user_data['wins'] / user_data['total_games'] * 100) if user_data['total_games'] > 0 else 0:.1f}%

Keep playing to climb the rankings! 🚀
"""
 
 keyboard = [
 [InlineKeyboardButton("Refresh", callback_data="leaderboard_my_rank")],
 [InlineKeyboardButton("⬅️ Back", callback_data="leaderboard_menu")]
 ]
 
 reply_markup = InlineKeyboardMarkup(keyboard)
 await query.edit_message_text(ranks_text, reply_markup=reply_markup, parse_mode='Markdown')


async def handle_leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
 """Handle leaderboard callbacks."""
 query = update.callback_query
 user_id = update.effective_user.id
 data = query.data
 
 if data == "leaderboard_menu":
 await show_leaderboard_menu(update)
 elif data == "leaderboard_balance":
 await show_balance_leaderboard(query)
 elif data == "leaderboard_games":
 await show_games_leaderboard(query)
 elif data == "leaderboard_winnings":
 await show_winnings_leaderboard(query)
 elif data == "leaderboard_my_rank":
 await show_user_ranks(query, user_id)


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
 """Handle the /leaderboard command."""
 await show_leaderboard_menu(update)
