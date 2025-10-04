"""
Basketball Game

Telegram emoji-based basketball game where players shoot hoops!
Uses Telegram's basketball dice emoji (🏀) which shows values 1-5.
Players can bet on the outcome of the shot.
"""

import random
from typing import Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Bet limits
MIN_BET = 0.50
MAX_BET = 1000.0

# Basketball dice values:
# 1-2: Miss (Ball doesn't go in)
# 3: Near miss (Ball hits rim)
# 4-5: Score! (Ball goes in the hoop)

async def play_basketball_game(user_id: int, bet_type: str, bet_amount: float) -> dict:
    """
    Play a basketball game.
    
    Args:
        user_id: User's Telegram ID
        bet_type: 'score' (bet on making the shot) or 'miss' (bet on missing)
        bet_amount: Amount to bet in USD
    
    Returns:
        dict with game results
    """
    from main import get_user, update_balance, deduct_balance, log_game_session, format_usd
    
    # Basketball emoji dice values (1-5)
    # In Telegram: 1-2 = miss, 3 = rim, 4-5 = score
    dice_value = random.randint(1, 5)
    
    # Determine if shot scored
    scored = dice_value >= 4  # 4 or 5 = score
    
    # Determine if bet wins
    is_win = False
    payout_multiplier = 0
    
    if bet_type == 'score':
        is_win = scored
        payout_multiplier = 1.8  # 1.8x payout (2/5 chance = 40%)
        result_text = f"SCORE BET ({'WIN' if is_win else 'LOSE'})"
    elif bet_type == 'miss':
        is_win = not scored
        payout_multiplier = 1.5  # 1.5x payout (3/5 chance = 60%)
        result_text = f"MISS BET ({'WIN' if is_win else 'LOSE'})"
    
    # Calculate winnings
    if is_win:
        win_amount = bet_amount * payout_multiplier
        net_win = win_amount - bet_amount
    else:
        win_amount = 0
        net_win = -bet_amount
    
    # Update balance
    await update_balance(user_id, net_win)
    
    # Log game session
    await log_game_session(user_id, 'basketball', bet_amount, win_amount, result_text)
    
    # Get updated balance
    user_data = await get_user(user_id)
    new_balance = user_data['balance'] if user_data else 0
    
    # Get shot description
    shot_result = get_shot_description(dice_value)
    
    return {
        'dice_value': dice_value,
        'scored': scored,
        'is_win': is_win,
        'bet_amount': bet_amount,
        'win_amount': win_amount,
        'net_win': net_win,
        'new_balance': new_balance,
        'result_text': result_text,
        'shot_result': shot_result,
        'payout_multiplier': payout_multiplier
    }


def get_shot_description(value: int) -> str:
    """Get description for basketball shot result."""
    descriptions = {
        1: "🚫 **AIR BALL!** - Complete miss!",
        2: "❌ **MISSED!** - Shot bounced off the backboard",
        3: "😬 **SO CLOSE!** - Ball hit the rim!",
        4: "🏀 **SWISH!** - Clean shot!",
        5: "🔥 **PERFECT!** - Nothing but net!"
    }
    return descriptions.get(value, "🏀 Shot taken!")


async def show_basketball_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show basketball game menu."""
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
🏀 <b>BASKETBALL GAME</b> 🏀

💰 <b>Balance:</b> {balance_str}

🎯 <b>How to Play:</b>
Take your shot and bet on the outcome!

<b>Bet Options:</b>
🏀 <b>SCORE</b> - Bet the ball goes in (4-5)
  • 40% chance to win
  • 1.8x payout

🚫 <b>MISS</b> - Bet the ball misses (1-3)
  • 60% chance to win
  • 1.5x payout

<b>Shot Results:</b>
• 1-2: Miss 🚫
• 3: Rim (close!) 😬
• 4-5: Score! 🏀

💵 <b>Min Bet:</b> ${MIN_BET:.2f}
💰 <b>Max Bet:</b> ${MAX_BET:.2f}

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
    
    # Store bet amount and show shot selection
    context.user_data['basketball_bet_amount'] = bet_amount
    
    bet_str = await format_usd(bet_amount)
    balance_str = await format_usd(user['balance'])
    
    text = f"""
🏀 <b>BASKETBALL GAME</b> 🏀

💰 <b>Balance:</b> {balance_str}
💵 <b>Bet Amount:</b> {bet_str}

🎯 <b>Choose your bet:</b>

🏀 <b>SCORE</b> (4-5 to win)
  • 40% win chance
  • Win: {await format_usd(bet_amount * 1.8)}
  • Profit: +{await format_usd(bet_amount * 0.8)}

🚫 <b>MISS</b> (1-3 to win)
  • 60% win chance
  • Win: {await format_usd(bet_amount * 1.5)}
  • Profit: +{await format_usd(bet_amount * 0.5)}

<b>What's your prediction?</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🏀 BET SCORE", callback_data="basketball_play_score"),
            InlineKeyboardButton("🚫 BET MISS", callback_data="basketball_play_miss")
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
    """Handle basketball game play."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    from main import get_user, deduct_balance, format_usd
    
    # Get bet type from callback data
    bet_type = query.data.split('_')[-1]  # 'score' or 'miss'
    
    # Get bet amount from context
    bet_amount = context.user_data.get('basketball_bet_amount', 1.0)
    
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
    
    # Play the game
    result = await play_basketball_game(user_id, bet_type, bet_amount)
    
    # Format result message
    bet_str = await format_usd(result['bet_amount'])
    balance_str = await format_usd(result['new_balance'])
    
    if result['is_win']:
        win_str = await format_usd(result['win_amount'])
        profit_str = await format_usd(result['net_win'])
        result_emoji = "🎉"
        result_text = f"<b>YOU WIN!</b> 🏆\n💰 Won: {win_str}\n📈 Profit: {profit_str}"
    else:
        loss_str = await format_usd(result['bet_amount'])
        result_emoji = "😞"
        result_text = f"<b>YOU LOSE</b>\n📉 Lost: {loss_str}"
    
    # Get shot animation
    shot_emoji = "🏀"
    
    text = f"""
🏀 <b>BASKETBALL GAME</b> 🏀

{shot_emoji} <b>SHOT RESULT:</b>
{result['shot_result']}

🎯 <b>Your Bet:</b> {bet_type.upper()} - {bet_str}
{'🏀 Ball scored!' if result['scored'] else '🚫 Ball missed!'}

{result_emoji} {result_text}

💰 <b>New Balance:</b> {balance_str}

<b>Play again?</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Play Again", callback_data="game_basketball"),
            InlineKeyboardButton("🎮 All Games", callback_data="mini_app_centre")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    
    # Clear context
    context.user_data.pop('basketball_bet_amount', None)


async def handle_custom_bet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom bet amount input for basketball."""
    user_id = update.message.from_user.id
    
    from main import get_user, format_usd
    
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
    
    # Show shot selection
    bet_str = await format_usd(bet_amount)
    balance_str = await format_usd(user['balance'])
    
    text = f"""
🏀 <b>BASKETBALL GAME</b> 🏀

💰 <b>Balance:</b> {balance_str}
💵 <b>Bet Amount:</b> {bet_str}

🎯 <b>Choose your bet:</b>

🏀 <b>SCORE</b> (4-5 to win)
  • 40% win chance
  • Win: {await format_usd(bet_amount * 1.8)}

🚫 <b>MISS</b> (1-3 to win)
  • 60% win chance
  • Win: {await format_usd(bet_amount * 1.5)}
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🏀 BET SCORE", callback_data="basketball_play_score"),
            InlineKeyboardButton("🚫 BET MISS", callback_data="basketball_play_miss")
        ],
        [
            InlineKeyboardButton("🔙 Change Bet", callback_data="game_basketball")
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
    
    context.user_data['awaiting_basketball_custom_bet'] = True
    
    await query.edit_message_text(
        f"💵 <b>Enter your bet amount:</b>\n\n"
        f"Min: ${MIN_BET:.2f}\n"
        f"Max: ${MAX_BET:.2f}\n\n"
        f"<i>Type the amount and send it.</i>",
        parse_mode=ParseMode.HTML
    )


async def handle_basketball_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main callback handler for basketball game."""
    query = update.callback_query
    data = query.data
    
    if data == "game_basketball":
        await show_basketball_menu(update, context)
    elif data.startswith("basketball_bet_") and data != "basketball_bet_custom":
        await basketball_bet_callback(update, context)
    elif data == "basketball_custom_bet":
        await basketball_custom_bet_callback(update, context)
    elif data.startswith("basketball_play_"):
        await basketball_play_callback(update, context)
    else:
        await query.answer("Unknown action", show_alert=True)
