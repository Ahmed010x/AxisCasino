# bot/games/coinflip.py
"""
Coin Flip Game Module
Simple 50/50 game - bet on Heads or Tails
"""

import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Game configuration
MIN_BET = 1.0
MAX_BET = 1000.0
WIN_MULTIPLIER = 1.95  # 95% payout (5% house edge)

async def handle_coinflip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main handler for coin flip game"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "game_coinflip":
        await show_coinflip_menu(update, context)
    elif data.startswith("coinflip_bet_"):
        bet_amount = float(data.split("_")[2])
        await show_coinflip_choice(update, context, bet_amount)
    elif data.startswith("coinflip_play_"):
        await play_coinflip(update, context)

async def show_coinflip_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show coin flip betting interface"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Import here to avoid circular dependency
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, format_usd
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found. Please restart with /start")
        return
    
    balance_str = await format_usd(user['balance'])
    
    text = f"""
🪙 <b>COIN FLIP</b> 🪙

💰 <b>Your Balance:</b> {balance_str}

🎮 <b>How to Play:</b>
• Choose your bet amount
• Pick Heads or Tails
• Win {WIN_MULTIPLIER}x your bet!

💡 <b>Game Info:</b>
• Fair 50/50 odds
• Instant results
• Win probability: 50%
• Payout: {WIN_MULTIPLIER}x bet

<b>Choose your bet amount:</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("$1", callback_data="coinflip_bet_1"),
            InlineKeyboardButton("$5", callback_data="coinflip_bet_5"),
            InlineKeyboardButton("$10", callback_data="coinflip_bet_10")
        ],
        [
            InlineKeyboardButton("$25", callback_data="coinflip_bet_25"),
            InlineKeyboardButton("$50", callback_data="coinflip_bet_50"),
            InlineKeyboardButton("$100", callback_data="coinflip_bet_100")
        ],
        [InlineKeyboardButton("🔙 Back to Games", callback_data="mini_app_centre")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def show_coinflip_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, bet_amount: float):
    """Show heads/tails choice screen"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Import here to avoid circular dependency
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, format_usd
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found. Please restart with /start")
        return
    
    if user['balance'] < bet_amount:
        balance_str = await format_usd(user['balance'])
        await query.edit_message_text(
            f"❌ Insufficient balance!\n\nYour balance: {balance_str}\nRequired: ${bet_amount:.2f}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_coinflip")]])
        )
        return
    
    # Store bet amount in context
    context.user_data['coinflip_bet'] = bet_amount
    
    potential_win = bet_amount * WIN_MULTIPLIER
    
    text = f"""
🪙 <b>COIN FLIP</b> 🪙

💰 <b>Bet Amount:</b> ${bet_amount:.2f}
💵 <b>Potential Win:</b> ${potential_win:.2f}

<b>Choose your side:</b>
Will the coin land on Heads or Tails?
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🔴 HEADS", callback_data=f"coinflip_play_heads_{bet_amount}"),
            InlineKeyboardButton("⚫ TAILS", callback_data=f"coinflip_play_tails_{bet_amount}")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="game_coinflip")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def play_coinflip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute the coin flip game"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data_parts = query.data.split("_")
    choice = data_parts[2]  # "heads" or "tails"
    bet_amount = float(data_parts[3])
    
    # Import here to avoid circular dependency
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, deduct_balance, update_balance, log_game_session, update_house_balance_on_game, format_usd
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found. Please restart with /start")
        return
    
    # Validate balance
    if user['balance'] < bet_amount:
        balance_str = await format_usd(user['balance'])
        await query.edit_message_text(
            f"❌ Insufficient balance!\n\nYour balance: {balance_str}\nRequired: ${bet_amount:.2f}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_coinflip")]])
        )
        return
    
    # Deduct bet amount
    if not await deduct_balance(user_id, bet_amount):
        await query.edit_message_text(
            "❌ Error processing bet. Please try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_coinflip")]])
        )
        return
    
    # Flip the coin
    result = random.choice(['heads', 'tails'])
    won = (result == choice)
    
    # Calculate winnings
    win_amount = bet_amount * WIN_MULTIPLIER if won else 0.0
    net_profit = win_amount - bet_amount
    
    # Update balance if won
    if won:
        await update_balance(user_id, win_amount)
    
    # Update house balance
    await update_house_balance_on_game(bet_amount, win_amount)
    
    # Log game session
    await log_game_session(
        user_id=user_id,
        game_type="coinflip",
        bet_amount=bet_amount,
        win_amount=win_amount,
        result=f"{'WIN' if won else 'LOSS'} - {result}"
    )
    
    # Get updated balance
    updated_user = await get_user(user_id)
    new_balance_str = await format_usd(updated_user['balance'])
    
    # Build result message
    coin_emoji = "🔴" if result == "heads" else "⚫"
    result_text = "HEADS" if result == "heads" else "TAILS"
    
    if won:
        text = f"""
🎉 <b>YOU WIN!</b> 🎉

{coin_emoji} <b>Coin landed on: {result_text}</b>

💰 <b>Bet:</b> ${bet_amount:.2f}
💵 <b>Won:</b> ${win_amount:.2f}
📈 <b>Profit:</b> ${net_profit:.2f}

💳 <b>New Balance:</b> {new_balance_str}

<i>Congratulations! You guessed correctly!</i>
"""
    else:
        text = f"""
😔 <b>YOU LOSE</b> 😔

{coin_emoji} <b>Coin landed on: {result_text}</b>

💰 <b>Bet:</b> ${bet_amount:.2f}
💸 <b>Lost:</b> ${bet_amount:.2f}

💳 <b>New Balance:</b> {new_balance_str}

<i>Better luck next time!</i>
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Play Again", callback_data="game_coinflip")],
        [InlineKeyboardButton("🎮 Other Games", callback_data="mini_app_centre")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# Export the main handler
__all__ = ['handle_coinflip_callback']
