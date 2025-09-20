"""
Roulette Game

Implementation of European roulette with various betting options.
"""

import random
from typing import Dict, List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database.user import get_user, add_game_result


# Roulette wheel (European - single zero)
ROULETTE_NUMBERS = list(range(0, 37))  # 0-36

# Number colors
RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK_NUMBERS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

# Bet types and their payouts
BET_TYPES = {
    'straight': {'payout': 35, 'name': 'Single Number'},
    'red': {'payout': 1, 'name': 'Red'},
    'black': {'payout': 1, 'name': 'Black'},
    'even': {'payout': 1, 'name': 'Even'},
    'odd': {'payout': 1, 'name': 'Odd'},
    'low': {'payout': 1, 'name': 'Low (1-18)'},
    'high': {'payout': 1, 'name': 'High (19-36)'},
    'dozen1': {'payout': 2, 'name': '1st Dozen (1-12)'},
    'dozen2': {'payout': 2, 'name': '2nd Dozen (13-24)'},
    'dozen3': {'payout': 2, 'name': '3rd Dozen (25-36)'}
}


def spin_wheel() -> int:
    """Spin the roulette wheel and return winning number."""
    return random.choice(ROULETTE_NUMBERS)


def get_number_color(number: int) -> str:
    """Get the color of a roulette number."""
    if number == 0:
        return 'green'
    elif number in RED_NUMBERS:
        return 'red'
    else:
        return 'black'


def check_bet_win(number: int, bet_type: str, bet_number: int = None) -> bool:
    """Check if a bet wins based on the winning number."""
    if bet_type == 'straight':
        return number == bet_number
    elif bet_type == 'red':
        return number in RED_NUMBERS
    elif bet_type == 'black':
        return number in BLACK_NUMBERS
    elif bet_type == 'even':
        return number != 0 and number % 2 == 0
    elif bet_type == 'odd':
        return number != 0 and number % 2 == 1
    elif bet_type == 'low':
        return 1 <= number <= 18
    elif bet_type == 'high':
        return 19 <= number <= 36
    elif bet_type == 'dozen1':
        return 1 <= number <= 12
    elif bet_type == 'dozen2':
        return 13 <= number <= 24
    elif bet_type == 'dozen3':
        return 25 <= number <= 36
    
    return False


async def play_roulette(user_id: int, bet_type: str, bet_amount: int, bet_number: int = None) -> Tuple[int, bool, int, str]:
    """Play a roulette game."""
    # Spin the wheel
    winning_number = spin_wheel()
    
    # Check if bet wins
    is_win = check_bet_win(winning_number, bet_type, bet_number)
    
    # Calculate winnings
    if is_win:
        payout_multiplier = BET_TYPES[bet_type]['payout']
        win_amount = bet_amount * (payout_multiplier + 1)  # Include original bet
        result_text = f"WIN! {BET_TYPES[bet_type]['name']}"
    else:
        win_amount = 0
        result_text = f"LOSE! {BET_TYPES[bet_type]['name']}"
    
    # Record game result
    await add_game_result(user_id, 'roulette', bet_amount, win_amount, result_text)
    
    # Get updated balance
    user_data = await get_user(user_id)
    new_balance = user_data['balance'] if user_data else 0
    
    return winning_number, is_win, win_amount, new_balance


async def show_roulette_menu(update: Update, balance: int):
    """Show roulette betting menu."""
    roulette_text = f"""
🎲 **EUROPEAN ROULETTE** 🎲

Current Balance: **{balance} chips**

**Betting Options:**
• Single Number (35:1) - 100 chips
• Red/Black (1:1) - 15 chips  
• Even/Odd (1:1) - 15 chips
• Low/High (1:1) - 15 chips
• Dozens (2:1) - 30 chips

Choose your bet type:
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🔴 Red (1:1)", callback_data="roulette_bet_red_15"),
            InlineKeyboardButton("⚫ Black (1:1)", callback_data="roulette_bet_black_15")
        ],
        [
            InlineKeyboardButton("📈 Even (1:1)", callback_data="roulette_bet_even_15"),
            InlineKeyboardButton("📉 Odd (1:1)", callback_data="roulette_bet_odd_15")
        ],
        [
            InlineKeyboardButton("⬇️ Low 1-18 (1:1)", callback_data="roulette_bet_low_15"),
            InlineKeyboardButton("⬆️ High 19-36 (1:1)", callback_data="roulette_bet_high_15")
        ],
        [
            InlineKeyboardButton("1️⃣ 1st Dozen (2:1)", callback_data="roulette_bet_dozen1_30"),
            InlineKeyboardButton("2️⃣ 2nd Dozen (2:1)", callback_data="roulette_bet_dozen2_30"),
            InlineKeyboardButton("3️⃣ 3rd Dozen (2:1)", callback_data="roulette_bet_dozen3_30")
        ],
        [
            InlineKeyboardButton("🎯 Single Number (35:1)", callback_data="roulette_number_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(roulette_text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_number_menu(query):
    """Show single number betting menu."""
    number_text = """
🎯 **SINGLE NUMBER BET**

Choose a number (0-36):
Bet: 100 chips
Payout: 35:1 (3500 chips if you win!)
"""
    
    # Create number grid (6 rows of 6 numbers each, plus 0)
    keyboard = []
    
    # Add 0 separately
    keyboard.append([InlineKeyboardButton("0️⃣ 0", callback_data="roulette_bet_straight_100_0")])
    
    # Add numbers 1-36 in rows of 6
    for row in range(6):
        number_row = []
        for col in range(6):
            number = row * 6 + col + 1
            if number <= 36:
                number_row.append(
                    InlineKeyboardButton(f"{number}", callback_data=f"roulette_bet_straight_100_{number}")
                )
        keyboard.append(number_row)
    
    # Back button
    keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="roulette_main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(number_text, reply_markup=reply_markup, parse_mode='Markdown')


async def handle_roulette_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle roulette betting callbacks."""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    if data == "roulette_main_menu":
        user_data = await get_user(user_id)
        await show_roulette_menu(update, user_data['balance'])
        return
    
    if data == "roulette_number_menu":
        await show_number_menu(query)
        return
    
    if data.startswith("roulette_bet_"):
        parts = data.split('_')
        bet_type = parts[2]
        bet_amount = int(parts[3])
        bet_number = None
        
        if len(parts) > 4:  # Single number bet
            bet_number = int(parts[4])
        
        # Check balance
        user_data = await get_user(user_id)
        if not user_data or user_data['balance'] < bet_amount:
            await query.answer("❌ Insufficient balance!")
            return
        
        # Play the game
        winning_number, is_win, win_amount, new_balance = await play_roulette(
            user_id, bet_type, bet_amount, bet_number
        )
        
        # Format result
        color = get_number_color(winning_number)
        color_emoji = {'red': '🔴', 'black': '⚫', 'green': '🟢'}[color]
        
        if is_win:
            result_message = f"""
🎲 **ROULETTE RESULT** 🎲

**Winning Number:** {color_emoji} **{winning_number}**

🎉 **YOU WIN!**

**Your Bet:** {BET_TYPES[bet_type]['name']} - {bet_amount} chips
**Payout:** {BET_TYPES[bet_type]['payout']}:1
🏆 **Won:** {win_amount - bet_amount} chips
📊 **Balance:** {new_balance} chips

Congratulations! 🍀
"""
        else:
            result_message = f"""
🎲 **ROULETTE RESULT** 🎲

**Winning Number:** {color_emoji} **{winning_number}**

😔 **YOU LOSE**

**Your Bet:** {BET_TYPES[bet_type]['name']} - {bet_amount} chips
💸 **Lost:** {bet_amount} chips
📊 **Balance:** {new_balance} chips

Better luck next time! 🍀
"""
        
        # Add play again buttons
        keyboard = [
            [
                InlineKeyboardButton("🎲 Play Again", callback_data="game_roulette"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(result_message, reply_markup=reply_markup, parse_mode='Markdown')
