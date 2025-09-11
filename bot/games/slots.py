"""
Slot Machine Game

Implementation of a classic 3-reel slot machine with various symbols
and payout multipliers.
"""

import random
from typing import List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database.user import get_user, add_game_result


# Slot symbols and their weights (higher weight = more common)
SYMBOLS = {
    '🍒': {'weight': 40, 'payout': 10},
    '🍋': {'weight': 30, 'payout': 20},
    '🍊': {'weight': 20, 'payout': 30},
    '🔔': {'weight': 8, 'payout': 50},
    '💎': {'weight': 2, 'payout': 100}
}


def generate_reels() -> List[str]:
    """Generate three random symbols for the slot machine."""
    # Create weighted symbol list
    weighted_symbols = []
    for symbol, data in SYMBOLS.items():
        weighted_symbols.extend([symbol] * data['weight'])
    
    # Generate three random symbols
    return [random.choice(weighted_symbols) for _ in range(3)]


def calculate_win(reels: List[str], bet_amount: int) -> Tuple[int, str]:
    """Calculate winnings based on slot results."""
    # Check for three matching symbols
    if reels[0] == reels[1] == reels[2]:
        symbol = reels[0]
        multiplier = SYMBOLS[symbol]['payout']
        win_amount = bet_amount * multiplier
        return win_amount, f"JACKPOT! {symbol}{symbol}{symbol} - {multiplier}x multiplier!"
    
    # Check for two matching symbols
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        # Small consolation prize for two matching
        win_amount = bet_amount // 2
        return win_amount, "Two matching symbols - small win!"
    
    # No win
    return 0, "No match - try again!"


async def play_slots(user_id: int, bet_amount: int) -> Tuple[List[str], int, str, int]:
    """Play a slot machine game."""
    # Generate slot results
    reels = generate_reels()
    win_amount, result_text = calculate_win(reels, bet_amount)
    
    # Record game result
    await add_game_result(user_id, 'slots', bet_amount, win_amount, result_text)
    
    # Get updated balance
    user_data = await get_user(user_id)
    new_balance = user_data['balance'] if user_data else 0
    
    return reels, win_amount, result_text, new_balance


async def handle_slots_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle slot machine betting callbacks."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Extract bet amount from callback data
    bet_amount = int(query.data.split('_')[-1])
    
    # Check if user has enough balance
    user_data = await get_user(user_id)
    if not user_data or user_data['balance'] < bet_amount:
        await query.edit_message_text("❌ Insufficient balance! Use /daily for free chips.")
        return
    
    # Play the game
    reels, win_amount, result_text, new_balance = await play_slots(user_id, bet_amount)
    
    # Create result message
    slots_display = f"{reels[0]} | {reels[1]} | {reels[2]}"
    
    if win_amount > 0:
        result_message = f"""
🎰 **SLOT MACHINE RESULT** 🎰

{slots_display}

🎉 **{result_text}**

💰 **Bet:** {bet_amount} chips
🏆 **Won:** {win_amount} chips
📊 **Balance:** {new_balance} chips

Keep spinning! 🍀
"""
    else:
        result_message = f"""
🎰 **SLOT MACHINE RESULT** 🎰

{slots_display}

😔 **{result_text}**

💰 **Bet:** {bet_amount} chips
💸 **Lost:** {bet_amount} chips
📊 **Balance:** {new_balance} chips

Better luck next time! 🍀
"""
    
    # Add play again button
    keyboard = [
        [
            InlineKeyboardButton("🎰 Play Again", callback_data="game_slots"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        result_message, 
        reply_markup=reply_markup, 
        parse_mode='Markdown'
    )
