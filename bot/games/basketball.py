"""
Basketball Game - 1v1 Player vs Bot

Telegram emoji-based basketball game where player competes against the bot!
Both player and bot take shots using Telegram's basketball dice emoji (🏀).
First to reach the target score wins!
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

# Game settings
TARGET_SCORE = 3  # First to 3 points wins
WIN_MULTIPLIER = 1.9  # 1.9x payout for winning

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
    else:  # 4 or 5
        return 1, "SCORE", "🏀"

async def play_basketball_1v1(user_id: int, bet_amount: float) -> dict:
    """
    Play a 1v1 basketball game against the bot.
    First to TARGET_SCORE points wins.
    
    Args:
        user_id: User's Telegram ID
        bet_amount: Amount to bet in USD
    
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
    while player_score < TARGET_SCORE and bot_score < TARGET_SCORE:
        # Player's turn
        player_dice = random.randint(1, 5)
        player_points, player_desc, player_emoji = get_shot_result(player_dice)
        player_score += player_points
        
        # Bot's turn
        bot_dice = random.randint(1, 5)
        bot_points, bot_desc, bot_emoji = get_shot_result(bot_dice)
        bot_score += bot_points
        
        # Log this round
        game_log.append({
            'round': round_num,
            'player_dice': player_dice,
            'player_result': f"{player_emoji} {player_desc}",
            'player_points': player_points,
            'bot_dice': bot_dice,
            'bot_result': f"{bot_emoji} {bot_desc}",
            'bot_points': bot_points,
            'player_score': player_score,
            'bot_score': bot_score
        })
        
        round_num += 1
        
        # Safety check - max 10 rounds
        if round_num > 10:
            break
    
    # Determine winner
    player_won = player_score >= TARGET_SCORE and player_score > bot_score
    
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

💰 <b>Balance:</b> {balance_str}

🎯 <b>How to Play:</b>
You vs Bot in a basketball shootout!
• First to {TARGET_SCORE} points wins
• Win {WIN_MULTIPLIER}x your bet!

<b>Scoring:</b>
• 🚫 Miss (1-2): 0 points
• 😬 Rim (3): 0 points (close!)
• 🏀 Score (4-5): 1 point

<b>Game Flow:</b>
1. You and bot take turns shooting
2. Each successful shot = 1 point
3. First to {TARGET_SCORE} points wins the game!

💵 <b>Min Bet:</b> ${MIN_BET:.2f}
💰 <b>Max Bet:</b> ${MAX_BET:.2f}
🎯 <b>Win Multiplier:</b> {WIN_MULTIPLIER}x

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
    """Handle basketball 1v1 game play."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    from main import get_user, deduct_balance, format_usd
    
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
    
    # Play the 1v1 game
    result = await play_basketball_1v1(user_id, bet_amount)
    
    # Format game summary
    bet_str = await format_usd(result['bet_amount'])
    balance_str = await format_usd(result['new_balance'])
    
    # Build game log display
    game_summary = ""
    for round_data in result['game_log']:
        game_summary += f"\n<b>Round {round_data['round']}:</b>\n"
        game_summary += f"👤 You: {round_data['player_result']} (+{round_data['player_points']})\n"
        game_summary += f"🤖 Bot: {round_data['bot_result']} (+{round_data['bot_points']})\n"
        game_summary += f"📊 Score: {round_data['player_score']}-{round_data['bot_score']}\n"
    
    if result['player_won']:
        win_str = await format_usd(result['win_amount'])
        profit_str = await format_usd(result['net_result'])
        result_emoji = "🎉"
        result_text = f"<b>YOU WIN!</b> 🏆\n💰 Won: {win_str}\n📈 Profit: {profit_str}"
    else:
        loss_str = await format_usd(result['bet_amount'])
        result_emoji = "😞"
        result_text = f"<b>BOT WINS!</b> 🤖\n📉 Lost: {loss_str}"
    
    text = f"""
🏀 <b>BASKETBALL 1v1 RESULT</b> 🏀

🎯 <b>Final Score:</b>
👤 You: {result['player_score']} points
🤖 Bot: {result['bot_score']} points

{game_summary}

� <b>Bet Amount:</b> {bet_str}
{result_emoji} {result_text}

� <b>New Balance:</b> {balance_str}

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
