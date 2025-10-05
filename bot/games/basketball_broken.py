"""
Basketball Game - 1v1 Player vs Bot

Telegram emoji-based basketball game where player competes against the bot!
Both player and bot take shots using Telegram's basketball dice emoji (🏀).
First to reach the target score wins!
"""

import asyncio
import random
from typing import Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import sys
import os
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Bet limits
MIN_BET = 0.50
MAX_BET = 1000.0

# Game settings
DEFAULT_TARGET_SCORE = 3 # Default target score
WIN_MULTIPLIER = 1.9 # 1.9x payout for winning

# Basketball dice values:
# 1-2: Miss (0 points)
# 3: Near miss (0 points, but close!)
# 4-5: Score! (1 point)

def get_shot_result(dice_value: int) -> Tuple[int, str, str]:
 """
 Get shot result from dice value.
 Returns: (points, description, emoji)
 """
 if dice_value in [1, 2]:
 return 0, "MISS", "🚫"
 elif dice_value == 3:
 return 0, "RIM", "😬"
 else: # 4 or 5
 return 1, "SCORE", "🏀"

# --- Interactive Basketball Emoji Functions ---

async def send_basketball_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE, is_bot: bool = False) -> int:
 """
 Send a basketball emoji and return the animation result.
 
 Args:
 update: Telegram update object
 context: Bot context
 is_bot: Whether this is the bot's shot or player's shot
 
 Returns:
 int: The dice value (1-5) from the basketball animation
 """
 try:
 # Both bot and player shots use the same emoji sending mechanism
 message = await context.bot.send_dice(
 chat_id=update.effective_chat.id,
 emoji="🏀"
 )
 
 # Wait a moment for the animation to complete
 await asyncio.sleep(3)
 
 # Get the dice value from the message
 return message.dice.value
 
 except Exception as e:
 # Fallback to random if emoji fails
 import random
 return random.randint(1, 5)

async def play_basketball_1v1_interactive(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, bet_amount: float, target_score: int = DEFAULT_TARGET_SCORE) -> dict:
 """
 Play an interactive 1v1 basketball game against the bot using real Telegram emojis.
 First to target_score points wins.
 
 Args:
 update: Telegram update object
 context: Bot context
 user_id: User's Telegram ID
 bet_amount: Amount to bet in USD
 target_score: Points needed to win (1, 2, or 3)
 
 Returns:
 dict with complete game results
 """
 from main import get_user, update_balance, deduct_balance, log_game_session, format_usd
 
 # Initialize scores
 player_score = 0
 bot_score = 0
 
 # Game log for display
 game_log = []
 round_num = 1
 
 # Send initial game message
 await update.effective_message.reply_text(
 f"🏀 <b>BASKETBALL 1v1 MATCH STARTING!</b> 🏀\n\n"
 f"Bet: {await format_usd(bet_amount)}\n"
 f"First to {target_score} points wins!\n\n"
 f"<i>Watch the basketball animations to see the results!</i>",
 parse_mode=ParseMode.HTML
 )
 
 # Play until someone reaches target score
 while player_score < target_score and bot_score < target_score:
 # Send round announcement
 await update.effective_message.reply_text(
 f"📢 <b>Round {round_num}</b>\n"
 f"Score: You {player_score} - {bot_score} Bot\n\n"
 f"🏀 Your shot:",
 parse_mode=ParseMode.HTML
 )
 
 # Player's shot
 player_dice = await send_basketball_emoji(update, context, is_bot=False)
 player_points, player_desc, player_emoji = get_shot_result(player_dice)
 player_made_shot = player_points > 0
 
 await asyncio.sleep(1) # Brief pause between shots
 
 # Bot's shot announcement
 await update.effective_message.reply_text(
 f"🤖 Bot's shot:",
 parse_mode=ParseMode.HTML
 )
 
 # Bot's shot
 bot_dice = await send_basketball_emoji(update, context, is_bot=True)
 bot_points, bot_desc, bot_emoji = get_shot_result(bot_dice)
 bot_made_shot = bot_points > 0
 
 # Award points based on who scored
 round_points_player = 0
 round_points_bot = 0
 
 if player_made_shot and not bot_made_shot:
 # Player scores, bot misses = Player gets 1 point
 round_points_player = 1
 player_score += 1
 elif bot_made_shot and not player_made_shot:
 # Bot scores, player misses = Bot gets 1 point
 round_points_bot = 1
 bot_score += 1
 # If both score or both miss, no points awarded (tie round)
 
 # Show round results
 round_result = "PLAYER" if round_points_player > 0 else "BOT" if round_points_bot > 0 else "TIE"
 round_emoji = "🟢" if round_result == "PLAYER" else "🔴" if round_result == "BOT" else "🟡"
 
 result_text = f"<b>Round {round_num} Result:</b> {round_emoji}\n\n"
 result_text += f"👤 You: {player_emoji} {player_desc}"
 if round_points_player > 0:
 result_text += f" (+1 point)"
 result_text += f"\n🤖 Bot: {bot_emoji} {bot_desc}"
 if round_points_bot > 0:
 result_text += f" (+1 point)"
 result_text += f"\n\n<b>Score: You {player_score} - {bot_score} Bot</b>"
 
 await update.effective_message.reply_text(result_text, parse_mode=ParseMode.HTML)
 
 # Log this round
 game_log.append({
 'round': round_num,
 'player_dice': player_dice,
 'player_result': f"{player_emoji} {player_desc}",
 'player_made_shot': player_made_shot,
 'player_round_points': round_points_player,
 'bot_dice': bot_dice,
 'bot_result': f"{bot_emoji} {bot_desc}",
 'bot_made_shot': bot_made_shot,
 'bot_round_points': round_points_bot,
 'player_score': player_score,
 'bot_score': bot_score,
 'round_result': round_result
 })
 
 round_num += 1
 
 # Brief pause before next round
 if player_score < target_score and bot_score < target_score:
 await asyncio.sleep(2)
 
 # Safety check - max 20 rounds (since ties don't count, may take longer)
 if round_num > 20:
 break
 
 # Determine winner
 player_won = player_score >= target_score and player_score > bot_score
 
 # Calculate winnings
 if player_won:
 win_amount = bet_amount * WIN_MULTIPLIER
 net_result = win_amount - bet_amount
 result_text = "PLAYER WINS"
 else:
 win_amount = 0
 net_result = -bet_amount
 result_text = "BOT WINS"
 
 # Update balance
 await update_balance(user_id, net_result)
 
 # Log game session
 await log_game_session(user_id, 'basketball_1v1', bet_amount, win_amount, result_text)
 
 # Get updated balance
 user_data = await get_user(user_id)
 new_balance = user_data['balance'] if user_data else 0
 
 return {
 'player_won': player_won,
 'player_score': player_score,
 'bot_score': bot_score,
 'game_log': game_log,
 'bet_amount': bet_amount,
 'win_amount': win_amount,
 'net_result': net_result,
 'new_balance': new_balance,
 'result_text': result_text,
 'total_rounds': len(game_log)
 }


async def play_basketball_1v1(user_id: int, bet_amount: float, target_score: int = DEFAULT_TARGET_SCORE) -> dict:
 """
 Play a 1v1 basketball game against the bot.
 First to target_score points wins.
 
 Args:
 user_id: User's Telegram ID
 bet_amount: Amount to bet in USD
 target_score: Points needed to win (1, 2, or 3)
 
 Returns:
 dict with complete game results
 """
 from main import get_user, update_balance, deduct_balance, log_game_session, format_usd
 
 # Initialize scores
 player_score = 0
 bot_score = 0
 
 # Game log for display
 game_log = []
 round_num = 1
 
 # Play until someone reaches target score
 while player_score < target_score and bot_score < target_score:
 # Player's shot
 player_dice = random.randint(1, 5)
 player_points, player_desc, player_emoji = get_shot_result(player_dice)
 player_made_shot = player_points > 0
 
 # Bot's shot
 bot_dice = random.randint(1, 5)
 bot_points, bot_desc, bot_emoji = get_shot_result(bot_dice)
 bot_made_shot = bot_points > 0
 
 # Award points based on who scored
 round_points_player = 0
 round_points_bot = 0
 
 if player_made_shot and not bot_made_shot:
 # Player scores, bot misses = Player gets 1 point
 round_points_player = 1
 player_score += 1
 elif bot_made_shot and not player_made_shot:
 # Bot scores, player misses = Bot gets 1 point
 round_points_bot = 1
 bot_score += 1
 # If both score or both miss, no points awarded (tie round)
 
 # Log this round
 game_log.append({
 'round': round_num,
 'player_dice': player_dice,
 'player_result': f"{player_emoji} {player_desc}",
 'player_made_shot': player_made_shot,
 'player_round_points': round_points_player,
 'bot_dice': bot_dice,
 'bot_result': f"{bot_emoji} {bot_desc}",
 'bot_made_shot': bot_made_shot,
 'bot_round_points': round_points_bot,
 'player_score': player_score,
 'bot_score': bot_score,
 'round_result': "PLAYER" if round_points_player > 0 else "BOT" if round_points_bot > 0 else "TIE"
 })
 
 round_num += 1
 
 # Safety check - max 20 rounds (since ties don't count, may take longer)
 if round_num > 20:
 break
 
 # Determine winner
 player_won = player_score >= target_score and player_score > bot_score
 
 # Calculate winnings
 if player_won:
 win_amount = bet_amount * WIN_MULTIPLIER
 net_result = win_amount - bet_amount
 result_text = "PLAYER WINS"
 else:
 win_amount = 0
 net_result = -bet_amount
 result_text = "BOT WINS"
 
 # Update balance
 await update_balance(user_id, net_result)
 
 # Log game session
 await log_game_session(user_id, 'basketball_1v1', bet_amount, win_amount, result_text)
 
 # Get updated balance
 user_data = await get_user(user_id)
 new_balance = user_data['balance'] if user_data else 0
 
 return {
 'player_won': player_won,
 'player_score': player_score,
 'bot_score': bot_score,
 'game_log': game_log,
 'bet_amount': bet_amount,
 'win_amount': win_amount,
 'net_result': net_result,
 'new_balance': new_balance,
 'result_text': result_text,
 'total_rounds': len(game_log)
 }


async def show_basketball_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
 """Show basketball 1v1 game menu."""
 query = update.callback_query
 await query.answer()
 user_id = query.from_user.id
 
 from main import get_user, format_usd
 
 user = await get_user(user_id)
 if not user:
 await query.edit_message_text("❌ User not found. Please use /start first.")
 return
 
 balance_str = await format_usd(user['balance'])
 
 text = f"""
🏀 <b>BASKETBALL 1v1</b> 🏀

<b>Balance:</b> {balance_str}

<b>How to Play:</b>
Interactive basketball shootout using real Telegram emoji!
• You and the bot both send basketball emojis 🏀
• The animated emoji result determines if you score
• First to win the chosen number of points!
• Win {WIN_MULTIPLIER}x your bet!

<b>Interactive Gameplay:</b>
• 🏀 You send a basketball emoji
• 🤖 Bot sends a basketball emoji 
• Real emoji animations determine results!
• Watch the basketball spin and see if it goes in

<b>Scoring System:</b>
• Miss: Ball doesn't go in (0 points)
• 😬 Near Miss: Close but no score (0 points)
• 🏀 Score: Ball goes in! (+1 point)

<b>1v1 Match Rules:</b>
🟢 You score + Bot misses = +1 point for you
🔴 Bot scores + You miss = +1 point for bot
🟡 Both score or both miss = Tie round (no points)

<b>Min Bet:</b> ${MIN_BET:.2f}
<b>Max Bet:</b> ${MAX_BET:.2f}
<b>Win Multiplier:</b> {WIN_MULTIPLIER}x

<b>Choose target score to win:</b>
"""
 
 keyboard = [
 [
 InlineKeyboardButton("First to 1 Point", callback_data="basketball_target_1"),
 InlineKeyboardButton("First to 2 Points", callback_data="basketball_target_2")
 ],
 [
 InlineKeyboardButton("First to 3 Points", callback_data="basketball_target_3")
 ],
 [
 InlineKeyboardButton("🔙 Back to Games", callback_data="mini_app_centre")
 ]
 ]
 
 await query.edit_message_text(
 text,
 reply_markup=InlineKeyboardMarkup(keyboard),
 parse_mode=ParseMode.HTML
 )


async def basketball_bet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
 """Handle basketball bet amount selection."""
 query = update.callback_query
 await query.answer()
 user_id = query.from_user.id
 
 from main import get_user, format_usd
 
 # Check if target score is set
 if 'basketball_target_score' not in context.user_data:
 await query.answer("❌ Please select target score first", show_alert=True)
 await show_basketball_menu(update, context)
 return
 
 # Get bet amount from callback data
 bet_amount_str = query.data.split('_')[-1]
 
 try:
 bet_amount = float(bet_amount_str)
 except ValueError:
 await query.edit_message_text("❌ Invalid bet amount.")
 return
 
 # Validate bet amount
 if bet_amount < MIN_BET:
 await query.answer(f"❌ Minimum bet is ${MIN_BET:.2f}", show_alert=True)
 return
 
 if bet_amount > MAX_BET:
 await query.answer(f"❌ Maximum bet is ${MAX_BET:.2f}", show_alert=True)
 return
 
 # Check user balance
 user = await get_user(user_id)
 if not user:
 await query.edit_message_text("❌ User not found.")
 return
 
 if user['balance'] < bet_amount:
 balance_str = await format_usd(user['balance'])
 await query.answer(f"❌ Insufficient balance! You have {balance_str}", show_alert=True)
 return
 
 # Store bet amount and get target score
 context.user_data['basketball_bet_amount'] = bet_amount
 target_score = context.user_data['basketball_target_score']
 
 bet_str = await format_usd(bet_amount)
 balance_str = await format_usd(user['balance'])
 win_str = await format_usd(bet_amount * WIN_MULTIPLIER)
 profit_str = await format_usd(bet_amount * (WIN_MULTIPLIER - 1))
 
 text = f"""
🏀 <b>BASKETBALL 1v1 - READY TO PLAY!</b> 🏀

<b>Balance:</b> {balance_str}
<b>Bet Amount:</b> {bet_str}
<b>Target Score:</b> First to {target_score} point{'s' if target_score > 1 else ''}

<b>Potential Winnings:</b>
� Win: {win_str}
Profit: {profit_str}

<b>Game Rules:</b>
• Interactive emoji basketball shootout!
• First to {target_score} point{'s' if target_score > 1 else ''} wins!
• Real Telegram emoji animations determine results

<b>Ready to start?</b>
"""
"""
 
 keyboard = [
 [
 InlineKeyboardButton("🏀 BET SCORE", callback_data="basketball_play_score"),
 InlineKeyboardButton("BET MISS", callback_data="basketball_play_miss")
 ],
 [
 InlineKeyboardButton("🔙 Change Bet", callback_data="game_basketball")
 ]
 ]
 
 await query.edit_message_text(
 text,
 reply_markup=InlineKeyboardMarkup(keyboard),
 parse_mode=ParseMode.HTML
 )


async def basketball_play_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
 """Handle basketball 1v1 game play."""
 query = update.callback_query
 await query.answer()
 user_id = query.from_user.id
 
 from main import get_user, deduct_balance, format_usd
 
 # Get bet amount and target score from context
 bet_amount = context.user_data.get('basketball_bet_amount', 1.0)
 target_score = context.user_data.get('basketball_target_score', DEFAULT_TARGET_SCORE)
 
 # Validate bet amount
 if bet_amount < MIN_BET or bet_amount > MAX_BET:
 await query.edit_message_text(f"❌ Invalid bet amount. Must be between ${MIN_BET:.2f} and ${MAX_BET:.2f}")
 return
 
 # Check and deduct balance
 user = await get_user(user_id)
 if not user:
 await query.edit_message_text("❌ User not found.")
 return
 
 if user['balance'] < bet_amount:
 balance_str = await format_usd(user['balance'])
 await query.edit_message_text(f"❌ Insufficient balance! You have {balance_str}")
 return
 
 # Deduct bet amount
 deducted = await deduct_balance(user_id, bet_amount)
 if not deducted:
 await query.edit_message_text("❌ Failed to place bet. Please try again.")
 return
 
 # Play the interactive 1v1 game with real emoji animations
 result = await play_basketball_1v1_interactive(update, context, user_id, bet_amount, target_score)
 
 # Format final summary (the detailed game was already shown during play)
 bet_str = await format_usd(result['bet_amount'])
 balance_str = await format_usd(result['new_balance'])
 
 if result['player_won']:
 win_str = await format_usd(result['win_amount'])
 profit_str = await format_usd(result['net_result'])
 result_emoji = "🎉"
 result_text = f"<b>YOU WIN!</b>\nWon: {win_str}\nProfit: {profit_str}"
 else:
 loss_str = await format_usd(result['bet_amount'])
 result_emoji = "😞"
 result_text = f"<b>BOT WINS!</b> 🤖\nLost: {loss_str}"
 
 # Send final summary message
 text = f"""
🏀 <b>GAME COMPLETE!</b> 🏀

<b>Final Score:</b>
👤 You: {result['player_score']} points
🤖 Bot: {result['bot_score']} points

<b>Bet Amount:</b> {bet_str}
{result_emoji} {result_text}

<b>New Balance:</b> {balance_str}

<b>Play again?</b>
"""
 
 keyboard = [
 [
 InlineKeyboardButton("Play Again", callback_data="game_basketball"),
 InlineKeyboardButton("All Games", callback_data="mini_app_centre")
 ]
 ]
 
 # Send new message instead of editing (since the interactive game shows progress)
 await update.effective_message.reply_text(
 text,
 reply_markup=InlineKeyboardMarkup(keyboard),
 parse_mode=ParseMode.HTML
 )
 
 # Clear context
 context.user_data.pop('basketball_bet_amount', None)


async def handle_custom_bet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
 """Handle custom bet amount input for basketball."""
 user_id = update.message.from_user.id
 
 from main import get_user, format_usd, deduct_balance
 
 try:
 bet_amount = float(update.message.text.strip().replace('$', ''))
 except ValueError:
 await update.message.reply_text("❌ Invalid amount. Please enter a number.")
 return
 
 if bet_amount < MIN_BET:
 await update.message.reply_text(f"❌ Minimum bet is ${MIN_BET:.2f}")
 return
 
 if bet_amount > MAX_BET:
 await update.message.reply_text(f"❌ Maximum bet is ${MAX_BET:.2f}")
 return
 
 user = await get_user(user_id)
 if not user:
 await update.message.reply_text("❌ User not found.")
 return
 
 if user['balance'] < bet_amount:
 balance_str = await format_usd(user['balance'])
 await update.message.reply_text(f"❌ Insufficient balance! You have {balance_str}")
 return
 
 # Store bet amount
 context.user_data['basketball_bet_amount'] = bet_amount
 context.user_data.pop('awaiting_basketball_custom_bet', None)
 
 # Get target score (must be set before custom bet)
 target_score = context.user_data.get('basketball_target_score', DEFAULT_TARGET_SCORE)
 
 # Deduct bet amount
 deducted = await deduct_balance(user_id, bet_amount)
 if not deducted:
 await update.message.reply_text("❌ Failed to place bet. Please try again.")
 return
 
 # Play the 1v1 game with target score
 result = await play_basketball_1v1(user_id, bet_amount, target_score)
 
 # Format game summary
 bet_str = await format_usd(result['bet_amount'])
 balance_str = await format_usd(result['new_balance'])
 
 # Build game log display (same as in callback handler)
 game_summary = ""
 for round_data in result['game_log']:
 round_result_emoji = ""
 if round_data['round_result'] == "PLAYER":
 round_result_emoji = "🟢"
 elif round_data['round_result'] == "BOT":
 round_result_emoji = "🔴"
 else:
 round_result_emoji = "�"
 
 game_summary += f"\n<b>Round {round_data['round']}:</b> {round_result_emoji}\n"
 game_summary += f"👤 You: {round_data['player_result']}"
 if round_data['player_round_points'] > 0:
 game_summary += f" (+1 point)"
 game_summary += f"\n"
 game_summary += f"🤖 Bot: {round_data['bot_result']}"
 if round_data['bot_round_points'] > 0:
 game_summary += f" (+1 point)"
 game_summary += f"\n"
 game_summary += f"Score: {round_data['player_score']}-{round_data['bot_score']}\n"
 
 if result['player_won']:
 win_str = await format_usd(result['win_amount'])
 profit_str = await format_usd(result['net_result'])
 result_emoji = "🎉"
 result_text = f"<b>YOU WIN!</b>\nWon: {win_str}\nProfit: {profit_str}"
 else:
 loss_str = await format_usd(result['bet_amount'])
 result_emoji = "😞"
 result_text = f"<b>BOT WINS!</b> 🤖\nLost: {loss_str}"
 
 text = f"""
🏀 <b>BASKETBALL 1v1 RESULT</b> 🏀

<b>Final Score:</b>
👤 You: {result['player_score']} points
🤖 Bot: {result['bot_score']} points

{game_summary}

<b>Bet Amount:</b> {bet_str}
{result_emoji} {result_text}

<b>New Balance:</b> {balance_str}

<b>Play again?</b>
"""
 
 keyboard = [
 [
 InlineKeyboardButton("� Play Again", callback_data="game_basketball"),
 InlineKeyboardButton("All Games", callback_data="mini_app_centre")
 ]
 ]
 
 await update.message.reply_text(
 text,
 reply_markup=InlineKeyboardMarkup(keyboard),
 parse_mode=ParseMode.HTML
 )


async def basketball_custom_bet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
 """Handle custom bet amount request."""
 query = update.callback_query
 await query.answer()
 
 # Check if target score is set
 if 'basketball_target_score' not in context.user_data:
 await query.answer("❌ Please select target score first", show_alert=True)
 await show_basketball_menu(update, context)
 return
 
 context.user_data['awaiting_basketball_custom_bet'] = True
 
 target_score = context.user_data['basketball_target_score']
 
 await query.edit_message_text(
 f"<b>Enter your bet amount:</b>\n\n"
 f"Target: First to {target_score} point{'s' if target_score > 1 else ''}\n"
 f"Min: ${MIN_BET:.2f}\n"
 f"Max: ${MAX_BET:.2f}\n\n"
 f"<i>Type the amount and send it.</i>",
 parse_mode=ParseMode.HTML
 )


async def basketball_target_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
 """Handle basketball target score selection."""
 query = update.callback_query
 await query.answer()
 user_id = query.from_user.id
 
 from main import get_user, format_usd
 
 # Get target score from callback data
 target_score_str = query.data.split('_')[-1]
 
 try:
 target_score = int(target_score_str)
 except ValueError:
 await query.edit_message_text("❌ Invalid target score.")
 return
 
 # Validate target score
 if target_score not in [1, 2, 3]:
 await query.answer("❌ Target score must be 1, 2, or 3", show_alert=True)
 return
 
 # Store target score
 context.user_data['basketball_target_score'] = target_score
 
 # Show bet selection
 user = await get_user(user_id)
 if not user:
 await query.edit_message_text("❌ User not found.")
 return
 
 balance_str = await format_usd(user['balance'])
 
 # Calculate game duration estimate
 duration_text = {
 1: "⚡ Quick Match (1-3 rounds)",
 2: "🚀 Fast Match (2-6 rounds)", 
 3: "🏀 Classic Match (3-9 rounds)"
 }
 
 text = f"""
🏀 <b>BASKETBALL 1v1 - TARGET: {target_score} POINT{'S' if target_score > 1 else ''}</b> 🏀

<b>Balance:</b> {balance_str}
<b>Target Score:</b> First to {target_score} point{'s' if target_score > 1 else ''}
⏱️ <b>Duration:</b> {duration_text[target_score]}

<b>Game Format:</b>
• Interactive basketball shootout using real Telegram emoji!
• First to {target_score} point{'s' if target_score > 1 else ''} wins!
• Win {WIN_MULTIPLIER}x your bet!

<b>Min Bet:</b> ${MIN_BET:.2f}
<b>Max Bet:</b> ${MAX_BET:.2f}
<b>Win Multiplier:</b> {WIN_MULTIPLIER}x

<b>Choose your bet amount:</b>
"""
 
 keyboard = [
 [
 InlineKeyboardButton("$1", callback_data="basketball_bet_1"),
 InlineKeyboardButton("$5", callback_data="basketball_bet_5"),
 InlineKeyboardButton("$10", callback_data="basketball_bet_10")
 ],
 [
 InlineKeyboardButton("$25", callback_data="basketball_bet_25"),
 InlineKeyboardButton("$50", callback_data="basketball_bet_50"),
 InlineKeyboardButton("$100", callback_data="basketball_bet_100")
 ],
 [
 InlineKeyboardButton("✏️ Custom Amount", callback_data="basketball_custom_bet")
 ],
 [
 InlineKeyboardButton("Change Target", callback_data="basketball"),
 InlineKeyboardButton("🔙 Back to Games", callback_data="mini_app_centre")
 ]
 ]
 
 await query.edit_message_text(
 text,
 reply_markup=InlineKeyboardMarkup(keyboard),
 parse_mode=ParseMode.HTML
 )


async def handle_basketball_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
 """Main callback handler for basketball game."""
 query = update.callback_query
 data = query.data
 
 if data == "game_basketball" or data == "basketball":
 await show_basketball_menu(update, context)
 elif data.startswith("basketball_target_"):
 await basketball_target_callback(update, context)
 elif data.startswith("basketball_bet_") and data != "basketball_bet_custom":
 await basketball_bet_callback(update, context)
 elif data == "basketball_custom_bet":
 await basketball_custom_bet_callback(update, context)
 elif data.startswith("basketball_play_"):
 await basketball_play_callback(update, context)
 else:
 await query.answer("Unknown action", show_alert=True)
