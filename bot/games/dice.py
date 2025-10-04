"""
Dice Game - 1v1 Player vs Bot

Telegram dice-based competitive game where player competes against the bot!
Both player and bot roll dice (two dice each roll).
Best of multiple rounds - highest total each round wins!
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
TARGET_WINS = 3  # First to 3 round wins takes the match
WIN_MULTIPLIER = 1.9  # 1.9x payout for winning

def roll_dice() -> Tuple[int, int]:
    """Roll two dice and return the results."""
    die1 = random.randint(1, 6)
    die2 = random.randint(1, 6)
    return die1, die2


def get_dice_emoji(value: int) -> str:
    """Get dice emoji for a value."""
    dice_emojis = {
        1: '⚀', 2: '⚁', 3: '⚂', 
        4: '⚃', 5: '⚄', 6: '⚅'
    }
    return dice_emojis.get(value, '🎲')


async def play_dice_1v1(user_id: int, bet_amount: float) -> dict:
    """
    Play a 1v1 dice game against the bot.
    Each round, both player and bot roll two dice.
    Highest total wins the round.
    First to TARGET_WINS rounds wins the match.
    
    Args:
        user_id: User's Telegram ID
        bet_amount: Amount to bet in USD
    
    Returns:
        dict with complete game results
    """
    from main import get_user, update_balance, deduct_balance, log_game_session, format_usd
    
    # Initialize wins
    player_wins = 0
    bot_wins = 0
    
    # Game log for display
    game_log = []
    round_num = 1
    
    # Play until someone reaches target wins
    while player_wins < TARGET_WINS and bot_wins < TARGET_WINS:
        # Player's roll
        player_die1, player_die2 = roll_dice()
        player_total = player_die1 + player_die2
        
        # Bot's roll
        bot_die1, bot_die2 = roll_dice()
        bot_total = bot_die1 + bot_die2
        
        # Determine round winner
        if player_total > bot_total:
            round_winner = "PLAYER"
            player_wins += 1
        elif bot_total > player_total:
            round_winner = "BOT"
            bot_wins += 1
        else:
            round_winner = "TIE"
            # On tie, roll again (no win for either)
        
        # Log this round
        game_log.append({
            'round': round_num,
            'player_dice': [player_die1, player_die2],
            'player_total': player_total,
            'bot_dice': [bot_die1, bot_die2],
            'bot_total': bot_total,
            'round_winner': round_winner,
            'player_wins': player_wins,
            'bot_wins': bot_wins
        })
        
        round_num += 1
        
        # Safety check - max 15 rounds
        if round_num > 15:
            break
    
    # Determine match winner
    player_won = player_wins >= TARGET_WINS and player_wins > bot_wins
    
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
    await log_game_session(user_id, 'dice_1v1', bet_amount, win_amount, result_text)
    
    # Get updated balance
    user_data = await get_user(user_id)
    new_balance = user_data['balance'] if user_data else 0
    
    return {
        'player_won': player_won,
        'player_wins': player_wins,
        'bot_wins': bot_wins,
        'game_log': game_log,
        'bet_amount': bet_amount,
        'win_amount': win_amount,
        'net_result': net_result,
        'new_balance': new_balance,
        'result_text': result_text,
        'total_rounds': len(game_log)
    }


async def show_dice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show dice 1v1 game menu."""
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
🎲 <b>DICE 1v1</b> 🎲

💰 <b>Balance:</b> {balance_str}

� <b>How to Play:</b>
You vs Bot in a dice battle!
• Both roll two dice each round
• Highest total wins the round
• First to {TARGET_WINS} round wins takes the match!
• Win {WIN_MULTIPLIER}x your bet!

<b>Round Rules:</b>
• Each player rolls two dice (⚀⚁⚂⚃⚄⚅)
• Highest total (2-12) wins the round
• Ties don't count - roll again!

<b>Match Flow:</b>
1. Both players roll simultaneously
2. Compare totals - higher wins
3. First to {TARGET_WINS} round wins takes the match!

💵 <b>Min Bet:</b> ${MIN_BET:.2f}
💰 <b>Max Bet:</b> ${MAX_BET:.2f}
🎯 <b>Win Multiplier:</b> {WIN_MULTIPLIER}x

<b>Choose your bet amount:</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("$1", callback_data="dice_bet_1"),
            InlineKeyboardButton("$5", callback_data="dice_bet_5"),
            InlineKeyboardButton("$10", callback_data="dice_bet_10")
        ],
        [
            InlineKeyboardButton("$25", callback_data="dice_bet_25"),
            InlineKeyboardButton("$50", callback_data="dice_bet_50"),
            InlineKeyboardButton("$100", callback_data="dice_bet_100")
        ],
        [
            InlineKeyboardButton("✏️ Custom Amount", callback_data="dice_custom_bet")
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


async def handle_dice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle dice game callbacks."""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    from main import get_user, format_usd, deduct_balance
    
    if data == "dice_custom_bet":
        user_data = await get_user(user_id)
        context.user_data['awaiting_dice_custom_bet'] = True
        await query.edit_message_text(
            f"💰 <b>Current Balance:</b> {await format_usd(user_data['balance'])}\n\n"
            "✏️ Please enter your bet amount (e.g., 15.50):",
            parse_mode=ParseMode.HTML
        )
        return
    
    if data.startswith("dice_bet_"):
        bet_amount_str = data.split('_')[2]
        
        try:
            bet_amount = float(bet_amount_str)
        except ValueError:
            await query.answer("❌ Invalid bet amount!")
            return
        
        # Validate bet amount
        if bet_amount < MIN_BET or bet_amount > MAX_BET:
            await query.answer(f"❌ Bet must be between ${MIN_BET:.2f} and ${MAX_BET:.2f}!")
            return
        
        # Check balance and deduct bet
        user_data = await get_user(user_id)
        if not user_data or user_data['balance'] < bet_amount:
            await query.answer("❌ Insufficient balance!")
            return
        
        # Deduct bet amount
        await deduct_balance(user_id, bet_amount)
        
        # Play the 1v1 game
        game_result = await play_dice_1v1(user_id, bet_amount)
        
        # Format detailed result message
        result_message = f"🎲 <b>DICE 1v1 MATCH RESULTS</b> 🎲\n\n"
        
        # Show round-by-round results
        for round_data in game_result['game_log']:
            player_dice = round_data['player_dice']
            bot_dice = round_data['bot_dice']
            
            player_emojis = f"{get_dice_emoji(player_dice[0])}{get_dice_emoji(player_dice[1])}"
            bot_emojis = f"{get_dice_emoji(bot_dice[0])}{get_dice_emoji(bot_dice[1])}"
            
            round_winner_emoji = ""
            if round_data['round_winner'] == "PLAYER":
                round_winner_emoji = "🟢"
            elif round_data['round_winner'] == "BOT":
                round_winner_emoji = "🔴"
            else:
                round_winner_emoji = "🟡"
            
            result_message += f"<b>Round {round_data['round']}:</b> {round_winner_emoji}\n"
            result_message += f"You: {player_emojis} = {round_data['player_total']}\n"
            result_message += f"Bot: {bot_emojis} = {round_data['bot_total']}\n"
            result_message += f"Score: {round_data['player_wins']}-{round_data['bot_wins']}\n\n"
        
        # Final result
        if game_result['player_won']:
            result_message += f"� <b>YOU WIN THE MATCH!</b>\n\n"
            result_message += f"💰 <b>Bet:</b> {await format_usd(game_result['bet_amount'])}\n"
            result_message += f"🎉 <b>Won:</b> {await format_usd(game_result['win_amount'])}\n"
            result_message += f"📈 <b>Profit:</b> +{await format_usd(game_result['net_result'])}\n"
        else:
            result_message += f"😔 <b>BOT WINS THE MATCH</b>\n\n"
            result_message += f"💸 <b>Lost:</b> {await format_usd(game_result['bet_amount'])}\n"
        
        result_message += f"📊 <b>New Balance:</b> {await format_usd(game_result['new_balance'])}\n"
        
        # Add play again buttons
        keyboard = [
            [
                InlineKeyboardButton("🎲 Play Again", callback_data="game_dice"),
                InlineKeyboardButton("🎮 Games Menu", callback_data="mini_app_centre")
            ],
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data="start_panel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(result_message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def handle_custom_bet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom bet amount input from user"""
    if not context.user_data.get('awaiting_dice_custom_bet'):
        return
    
    from main import get_user, format_usd, deduct_balance
    
    user_id = update.message.from_user.id
    user_data = await get_user(user_id)
    
    try:
        # Parse bet amount
        bet_amount = float(update.message.text.strip().replace('$', '').replace(',', ''))
        
        # Validate bet amount
        if bet_amount < MIN_BET:
            await update.message.reply_text(
                f"❌ Bet amount too low!\n\nMinimum bet: ${MIN_BET:.2f}\nYour input: ${bet_amount:.2f}\n\nPlease try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_dice")]])
            )
            return
        
        if bet_amount > MAX_BET:
            await update.message.reply_text(
                f"❌ Bet amount too high!\n\nMaximum bet: ${MAX_BET:.2f}\nYour input: ${bet_amount:.2f}\n\nPlease try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_dice")]])
            )
            return
        
        if not user_data:
            await update.message.reply_text("❌ User not found. Please restart with /start")
            return
        
        if bet_amount > user_data['balance']:
            await update.message.reply_text(
                f"❌ Insufficient balance!\n\nYour balance: {await format_usd(user_data['balance'])}\nBet amount: ${bet_amount:.2f}\n\nPlease try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_dice")]])
            )
            return
        
        # Clear the awaiting state
        context.user_data['awaiting_dice_custom_bet'] = False
        
        # Deduct bet amount
        await deduct_balance(user_id, bet_amount)
        
        # Play the 1v1 game
        game_result = await play_dice_1v1(user_id, bet_amount)
        
        # Format detailed result message (same as in callback handler)
        result_message = f"🎲 <b>DICE 1v1 MATCH RESULTS</b> 🎲\n\n"
        
        # Show round-by-round results
        for round_data in game_result['game_log']:
            player_dice = round_data['player_dice']
            bot_dice = round_data['bot_dice']
            
            player_emojis = f"{get_dice_emoji(player_dice[0])}{get_dice_emoji(player_dice[1])}"
            bot_emojis = f"{get_dice_emoji(bot_dice[0])}{get_dice_emoji(bot_dice[1])}"
            
            round_winner_emoji = ""
            if round_data['round_winner'] == "PLAYER":
                round_winner_emoji = "�"
            elif round_data['round_winner'] == "BOT":
                round_winner_emoji = "�"
            else:
                round_winner_emoji = "🟡"
            
            result_message += f"<b>Round {round_data['round']}:</b> {round_winner_emoji}\n"
            result_message += f"You: {player_emojis} = {round_data['player_total']}\n"
            result_message += f"Bot: {bot_emojis} = {round_data['bot_total']}\n"
            result_message += f"Score: {round_data['player_wins']}-{round_data['bot_wins']}\n\n"
        
        # Final result
        if game_result['player_won']:
            result_message += f"🏆 <b>YOU WIN THE MATCH!</b>\n\n"
            result_message += f"💰 <b>Bet:</b> {await format_usd(game_result['bet_amount'])}\n"
            result_message += f"🎉 <b>Won:</b> {await format_usd(game_result['win_amount'])}\n"
            result_message += f"📈 <b>Profit:</b> +{await format_usd(game_result['net_result'])}\n"
        else:
            result_message += f"😔 <b>BOT WINS THE MATCH</b>\n\n"
            result_message += f"💸 <b>Lost:</b> {await format_usd(game_result['bet_amount'])}\n"
        
        result_message += f"� <b>New Balance:</b> {await format_usd(game_result['new_balance'])}\n"
        
        # Add play again buttons
        keyboard = [
            [
                InlineKeyboardButton("� Play Again", callback_data="game_dice"),
                InlineKeyboardButton("🎮 Games Menu", callback_data="mini_app_centre")
            ],
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data="start_panel")
            ]
        ]
        
        await update.message.reply_text(result_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        
    except ValueError:
        await update.message.reply_text(
            f"❌ Invalid input!\n\nPlease enter a valid number (e.g., 15.50)\n\nTry again:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_dice")]])
        )


# Export handlers
__all__ = ['handle_dice_callback', 'handle_custom_bet_input', 'show_dice_menu', 'play_dice_1v1']
