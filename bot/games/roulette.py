"""
Roulette Game

Implementation of European roulette with various betting options.
"""

import random
from typing import Dict, List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database.user import get_user, add_game_result


# Game constants
MIN_BET = 0.50
MAX_BET = 1000.0

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

**Step 1:** Choose your bet type below
**Step 2:** Select bet amount

**Betting Options:**
• Single Number (35:1) - High risk, high reward
• Red/Black (1:1) - Classic even-money bet
• Even/Odd (1:1) - Classic even-money bet
• Low/High (1:1) - Half the board
• Dozens (2:1) - One third of the board

Choose your bet type:
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🔴 Red (1:1)", callback_data="roulette_select_red"),
            InlineKeyboardButton("⚫ Black (1:1)", callback_data="roulette_select_black")
        ],
        [
            InlineKeyboardButton("📈 Even (1:1)", callback_data="roulette_select_even"),
            InlineKeyboardButton("📉 Odd (1:1)", callback_data="roulette_select_odd")
        ],
        [
            InlineKeyboardButton("⬇️ Low 1-18 (1:1)", callback_data="roulette_select_low"),
            InlineKeyboardButton("⬆️ High 19-36 (1:1)", callback_data="roulette_select_high")
        ],
        [
            InlineKeyboardButton("1️⃣ 1st Dozen (2:1)", callback_data="roulette_select_dozen1"),
            InlineKeyboardButton("2️⃣ 2nd Dozen (2:1)", callback_data="roulette_select_dozen2"),
            InlineKeyboardButton("3️⃣ 3rd Dozen (2:1)", callback_data="roulette_select_dozen3")
        ],
        [
            InlineKeyboardButton("🎯 Single Number (35:1)", callback_data="roulette_select_straight")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(roulette_text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_bet_amount_menu(query, bet_type: str, balance: int):
    """Show bet amount selection for chosen bet type."""
    bet_info = BET_TYPES[bet_type]
    
    # Suggest default amounts based on bet type
    if bet_type == 'straight':
        default_amounts = [50, 100, 200, 500]
    elif bet_type in ['dozen1', 'dozen2', 'dozen3']:
        default_amounts = [20, 50, 100, 200]
    else:  # Even money bets
        default_amounts = [10, 25, 50, 100]
    
    bet_text = f"""
🎲 **ROULETTE - {bet_info['name']}**

💰 **Current Balance:** {balance} chips
📊 **Payout:** {bet_info['payout']}:1

Choose your bet amount:
"""
    
    keyboard = []
    # Add default bet amounts
    row1 = []
    row2 = []
    for i, amount in enumerate(default_amounts):
        button = InlineKeyboardButton(
            f"{amount} chips",
            callback_data=f"roulette_bet_{bet_type}_{amount}"
        )
        if i < 2:
            row1.append(button)
        else:
            row2.append(button)
    
    keyboard.append(row1)
    keyboard.append(row2)
    
    # Add custom bet options
    keyboard.append([
        InlineKeyboardButton("💰 Half", callback_data=f"roulette_bet_{bet_type}_half"),
        InlineKeyboardButton("🎯 All-In", callback_data=f"roulette_bet_{bet_type}_allin")
    ])
    keyboard.append([
        InlineKeyboardButton("✏️ Custom Amount", callback_data=f"roulette_bet_{bet_type}_custom")
    ])
    keyboard.append([
        InlineKeyboardButton("⬅️ Back", callback_data="roulette_main_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(bet_text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_number_menu(query, balance: int):
    """Show single number betting menu with bet amount selection."""
    number_text = f"""
🎯 **SINGLE NUMBER BET**

💰 **Current Balance:** {balance} chips
📊 **Payout:** 35:1

First, choose your bet amount, then select a number:
"""
    
    keyboard = []
    
    # Bet amount selection
    keyboard.append([
        InlineKeyboardButton("50 chips", callback_data="roulette_number_amount_50"),
        InlineKeyboardButton("100 chips", callback_data="roulette_number_amount_100")
    ])
    keyboard.append([
        InlineKeyboardButton("200 chips", callback_data="roulette_number_amount_200"),
        InlineKeyboardButton("500 chips", callback_data="roulette_number_amount_500")
    ])
    keyboard.append([
        InlineKeyboardButton("💰 Half", callback_data="roulette_number_amount_half"),
        InlineKeyboardButton("🎯 All-In", callback_data="roulette_number_amount_allin")
    ])
    keyboard.append([
        InlineKeyboardButton("✏️ Custom Amount", callback_data="roulette_number_amount_custom")
    ])
    keyboard.append([
        InlineKeyboardButton("⬅️ Back", callback_data="roulette_main_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(number_text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_number_selection(query, bet_amount: int):
    """Show number grid for straight bet."""
    number_text = f"""
🎯 **SINGLE NUMBER BET**

💰 **Bet Amount:** {bet_amount} chips
📊 **Payout:** 35:1
🏆 **Potential Win:** {bet_amount * 36} chips

Choose a number (0-36):
"""
    
    # Create number grid (6 rows of 6 numbers each, plus 0)
    keyboard = []
    
    # Add 0 separately
    keyboard.append([InlineKeyboardButton("0️⃣ 0", callback_data=f"roulette_bet_straight_{bet_amount}_0")])
    
    # Add numbers 1-36 in rows of 6
    for row in range(6):
        number_row = []
        for col in range(6):
            number = row * 6 + col + 1
            if number <= 36:
                number_row.append(
                    InlineKeyboardButton(f"{number}", callback_data=f"roulette_bet_straight_{bet_amount}_{number}")
                )
        keyboard.append(number_row)
    
    # Back button
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="roulette_select_straight")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(number_text, reply_markup=reply_markup, parse_mode='Markdown')


async def handle_roulette_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle roulette betting callbacks."""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    user_data = await get_user(user_id)
    
    if not user_data:
        await query.edit_message_text("❌ User not found. Please use /start first.")
        return
    
    # Main menu
    if data == "roulette_main_menu":
        await show_roulette_menu(update, user_data['balance'])
        return
    
    # Bet type selection (shows bet amount menu)
    if data.startswith("roulette_select_"):
        bet_type = data.split('_')[-1]
        if bet_type == "straight":
            await show_number_menu(query, user_data['balance'])
        else:
            await show_bet_amount_menu(query, bet_type, user_data['balance'])
        return
    
    # Number bet amount selection
    if data.startswith("roulette_number_amount_"):
        amount_type = data.split('_')[-1]
        
        if amount_type == "half":
            bet_amount = max(10, user_data['balance'] // 2)
        elif amount_type == "allin":
            bet_amount = user_data['balance']
        elif amount_type == "custom":
            context.user_data['awaiting_roulette_number_bet'] = True
            await query.edit_message_text(
                f"💰 Current Balance: **{user_data['balance']} chips**\n\n"
                "✏️ Please enter your bet amount for single number (minimum 10 chips):",
                parse_mode='Markdown'
            )
            return
        else:
            bet_amount = int(amount_type)
        
        # Validate bet amount
        if bet_amount > user_data['balance']:
            await query.answer("❌ Insufficient balance!")
            return
        if bet_amount < MIN_BET:
            await query.answer(f"❌ Minimum bet is ${MIN_BET:.2f}!")
            return
        
        # Show number selection grid
        await show_number_selection(query, bet_amount)
        return
    
    # Place bet
    if data.startswith("roulette_bet_"):
        parts = data.split('_')
        bet_type = parts[2]
        bet_suffix = parts[3]
        bet_number = None
        
        # Handle different bet amount types
        if bet_suffix == "half":
            bet_amount = max(10, user_data['balance'] // 2)
        elif bet_suffix == "allin":
            bet_amount = user_data['balance']
        elif bet_suffix == "custom":
            # Request custom amount
            context.user_data['awaiting_roulette_bet'] = bet_type
            await query.edit_message_text(
                f"💰 Current Balance: **{user_data['balance']} chips**\n\n"
                f"✏️ Please enter your bet amount for {BET_TYPES[bet_type]['name']} (minimum 10 chips):",
                parse_mode='Markdown'
            )
            return
        else:
            bet_amount = int(bet_suffix)
            if len(parts) > 4:  # Single number bet
                bet_number = int(parts[4])
        
        # Validate bet amount
        if bet_amount > user_data['balance']:
            await query.answer("❌ Insufficient balance!")
            return
        if bet_amount < MIN_BET:
            await query.answer(f"❌ Minimum bet is ${MIN_BET:.2f}!")
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

**YOU WIN!**

**Your Bet:** {BET_TYPES[bet_type]['name']} - {bet_amount} chips
**Payout:** {BET_TYPES[bet_type]['payout']}:1
🏆 **Won:** {win_amount - bet_amount} chips
📊 **Balance:** {new_balance} chips

Congratulations!
"""
        else:
            result_message = f"""
🎲 **ROULETTE RESULT** 🎲

**Winning Number:** {color_emoji} **{winning_number}**

**YOU LOSE**

**Your Bet:** {BET_TYPES[bet_type]['name']} - {bet_amount} chips
💸 **Lost:** {bet_amount} chips
📊 **Balance:** {new_balance} chips

Better luck next time!
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


async def handle_custom_bet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom bet amount input from user"""
    # Handle regular bet type custom input
    if context.user_data.get('awaiting_roulette_bet'):
        bet_type = context.user_data['awaiting_roulette_bet']
        user_id = update.message.from_user.id
        user_data = await get_user(user_id)
        
        try:
            bet_amount = float(update.message.text.strip())
            
            if bet_amount < MIN_BET:
                await update.message.reply_text(
                    f"❌ Bet amount too low!\n\nMinimum bet: ${MIN_BET:.2f}\nYour input: ${bet_amount:.2f}\n\nPlease try again.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_roulette")]])
                )
                return
            
            if not user_data:
                await update.message.reply_text("❌ User not found. Please restart with /start")
                return
            
            if bet_amount > user_data['balance']:
                await update.message.reply_text(
                    f"❌ Insufficient balance!\n\nYour balance: {user_data['balance']} chips\nBet amount: {bet_amount} chips\n\nPlease try again.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_roulette")]])
                )
                return
            
            # Clear the awaiting state
            context.user_data.pop('awaiting_roulette_bet', None)
            
            # Play the game
            winning_number, is_win, win_amount, new_balance = await play_roulette(
                user_id, bet_type, bet_amount, None
            )
            
            # Format result
            color = get_number_color(winning_number)
            color_emoji = {'red': '🔴', 'black': '⚫', 'green': '🟢'}[color]
            
            if is_win:
                result_message = f"""
🎲 **ROULETTE RESULT** 🎲

**Winning Number:** {color_emoji} **{winning_number}**

**YOU WIN!**

**Your Bet:** {BET_TYPES[bet_type]['name']} - {bet_amount} chips
**Payout:** {BET_TYPES[bet_type]['payout']}:1
🏆 **Won:** {win_amount - bet_amount} chips
📊 **Balance:** {new_balance} chips

Congratulations!
"""
            else:
                result_message = f"""
🎲 **ROULETTE RESULT** 🎲

**Winning Number:** {color_emoji} **{winning_number}**

**YOU LOSE**

**Your Bet:** {BET_TYPES[bet_type]['name']} - {bet_amount} chips
💸 **Lost:** {bet_amount} chips
📊 **Balance:** {new_balance} chips

Better luck next time! 🍀
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🎲 Play Again", callback_data="game_roulette"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="help")
                ]
            ]
            await update.message.reply_text(result_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
        except ValueError:
            await update.message.reply_text(
                f"❌ Invalid input!\n\nPlease enter a valid number (e.g., 100)\n\nTry again:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_roulette")]])
            )
        return
    
    # Handle number bet custom input
    if context.user_data.get('awaiting_roulette_number_bet'):
        user_id = update.message.from_user.id
        user_data = await get_user(user_id)
        
        try:
            bet_amount = float(update.message.text.strip())
            
            if bet_amount < MIN_BET:
                await update.message.reply_text(
                    f"❌ Bet amount too low!\n\nMinimum bet: ${MIN_BET:.2f}\nYour input: ${bet_amount:.2f}\n\nPlease try again.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_roulette")]])
                )
                return
            
            if not user_data:
                await update.message.reply_text("❌ User not found. Please restart with /start")
                return
            
            if bet_amount > user_data['balance']:
                await update.message.reply_text(
                    f"❌ Insufficient balance!\n\nYour balance: {user_data['balance']} chips\nBet amount: {bet_amount} chips\n\nPlease try again.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_roulette")]])
                )
                return
            
            # Clear the awaiting state
            context.user_data.pop('awaiting_roulette_number_bet', None)
            
            # Show number selection grid
            number_text = f"""
🎯 **SINGLE NUMBER BET**

💰 **Bet Amount:** {bet_amount} chips
📊 **Payout:** 35:1
🏆 **Potential Win:** {bet_amount * 36} chips

Choose a number (0-36):
"""
            
            keyboard = []
            keyboard.append([InlineKeyboardButton("0️⃣ 0", callback_data=f"roulette_bet_straight_{bet_amount}_0")])
            
            for row in range(6):
                number_row = []
                for col in range(6):
                    number = row * 6 + col + 1
                    if number <= 36:
                        number_row.append(
                            InlineKeyboardButton(f"{number}", callback_data=f"roulette_bet_straight_{bet_amount}_{number}")
                        )
                keyboard.append(number_row)
            
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="roulette_select_straight")])
            
            await update.message.reply_text(number_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
        except ValueError:
            await update.message.reply_text(
                f"❌ Invalid input!\n\nPlease enter a valid number (e.g., 100)\n\nTry again:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_roulette")]])
            )


# Export handlers
__all__ = ['handle_roulette_callback', 'handle_custom_bet_input', 'show_roulette_menu']
