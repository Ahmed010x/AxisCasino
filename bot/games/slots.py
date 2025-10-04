"""
Slot Machine Game

Implementation of a classic 3-reel slot machine with various symbols
and payout multipliers.
"""

import random
from typing import List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from bot.database.user import get_user, add_game_result


# Slot symbols and their weights (higher weight = more common)
SYMBOLS = {
    '🍒': {'weight': 40, 'payout': 10},
    '🍋': {'weight': 30, 'payout': 20},
    '🍊': {'weight': 20, 'payout': 30},
    '🔔': {'weight': 8, 'payout': 50},
    '💎': {'weight': 2, 'payout': 100}
}

# Bet limits
MIN_BET = 0.50
MAX_BET = 1000.0


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


async def show_slots_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show slots betting interface"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Import to avoid circular dependency
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, format_usd
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found. Please restart with /start")
        return
    
    balance_str = await format_usd(user['balance'])
    
    # Calculate half and all-in amounts
    half_balance = user['balance'] / 2
    all_balance = user['balance']
    
    text = f"""
🎰 <b>SLOT MACHINE</b> 🎰

💰 <b>Your Balance:</b> {balance_str}

🎮 <b>How to Play:</b>
Match 3 symbols to win big!

💎 <b>Payouts:</b>
• 🍒🍒🍒 - 10x
• 🍋🍋🍋 - 20x
• 🍊🍊🍊 - 30x
• 🔔🔔🔔 - 50x
• 💎💎💎 - 100x

<b>Choose your bet amount:</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("$5", callback_data="slots_bet_5"),
            InlineKeyboardButton("$10", callback_data="slots_bet_10"),
            InlineKeyboardButton("$25", callback_data="slots_bet_25")
        ],
        [
            InlineKeyboardButton("$50", callback_data="slots_bet_50"),
            InlineKeyboardButton("$100", callback_data="slots_bet_100"),
            InlineKeyboardButton("$200", callback_data="slots_bet_200")
        ],
        [
            InlineKeyboardButton(f"💰 Half (${half_balance:.2f})", callback_data=f"slots_bet_{half_balance:.2f}"),
            InlineKeyboardButton(f"🎰 All-In (${all_balance:.2f})", callback_data=f"slots_bet_{all_balance:.2f}")
        ],
        [InlineKeyboardButton("✏️ Custom Amount", callback_data="slots_custom_bet")],
        [InlineKeyboardButton("🔙 Back to Games", callback_data="mini_app_centre")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)


async def request_custom_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request custom bet amount from user"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, format_usd
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found. Please restart with /start")
        return
    
    balance_str = await format_usd(user['balance'])
    
    # Set state to await custom bet input
    context.user_data['awaiting_slots_custom_bet'] = True
    
    text = f"""
✏️ <b>CUSTOM BET AMOUNT</b> ✏️

💰 <b>Your Balance:</b> {balance_str}

Please enter your custom bet amount in USD.

<b>Bet Limits:</b>
• Minimum: ${MIN_BET:.2f}
• Maximum: ${MAX_BET:.2f}
• Your Balance: {balance_str}

💡 <i>Type a number (e.g., "15.50" for $15.50)</i>

⌨️ <b>Waiting for your input...</b>
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Slots", callback_data="game_slots")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)


async def handle_custom_bet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom bet amount input from user"""
    if not context.user_data.get('awaiting_slots_custom_bet'):
        return False
    
    user_id = update.message.from_user.id
    
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, format_usd
    
    try:
        # Parse bet amount
        bet_amount = float(update.message.text.strip().replace('$', '').replace(',', ''))
        
        # Validate bet amount
        if bet_amount < MIN_BET:
            await update.message.reply_text(
                f"❌ Bet amount too low!\n\nMinimum bet: ${MIN_BET:.2f}\nYour input: ${bet_amount:.2f}\n\nPlease try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_slots")]])
            )
            return True
        
        if bet_amount > MAX_BET:
            await update.message.reply_text(
                f"❌ Bet amount too high!\n\nMaximum bet: ${MAX_BET:.2f}\nYour input: ${bet_amount:.2f}\n\nPlease try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_slots")]])
            )
            return True
        
        user = await get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found. Please restart with /start")
            return True
        
        if bet_amount > user['balance']:
            balance_str = await format_usd(user['balance'])
            await update.message.reply_text(
                f"❌ Insufficient balance!\n\nYour balance: {balance_str}\nBet amount: ${bet_amount:.2f}\n\nPlease try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_slots")]])
            )
            return True
        
        # Clear the awaiting state
        context.user_data['awaiting_slots_custom_bet'] = False
        
        # Play the game with custom bet
        await play_slots_game(update.message, context, bet_amount, is_custom=True)
        return True
        
    except ValueError:
        await update.message.reply_text(
            f"❌ Invalid input!\n\nPlease enter a valid number (e.g., 15.50)\n\nTry again:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_slots")]])
        )
        return True


async def play_slots_game(message_or_query, context: ContextTypes.DEFAULT_TYPE, bet_amount: float, is_custom: bool = False):
    """Execute the slots game"""
    if is_custom:
        user_id = message_or_query.from_user.id
        message = message_or_query
    else:
        query = message_or_query
        user_id = query.from_user.id
    
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, deduct_balance, update_balance, log_game_session, update_house_balance_on_game, format_usd
    
    user = await get_user(user_id)
    if not user:
        text = "❌ User not found. Please restart with /start"
        if is_custom:
            await message.reply_text(text)
        else:
            await query.edit_message_text(text)
        return
    
    # Validate balance
    if user['balance'] < bet_amount:
        balance_str = await format_usd(user['balance'])
        text = f"❌ Insufficient balance!\n\nYour balance: {balance_str}\nRequired: ${bet_amount:.2f}"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="game_slots")]]
        if is_custom:
            await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Deduct bet amount
    if not await deduct_balance(user_id, bet_amount):
        text = "❌ Error processing bet. Please try again."
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="game_slots")]]
        if is_custom:
            await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Play the game
    reels, win_amount, result_text, new_balance = await play_slots(user_id, bet_amount)
    
    # Update house balance
    await update_house_balance_on_game(bet_amount, win_amount)
    
    # Log game session
    await log_game_session(
        user_id=user_id,
        game_type="slots",
        bet_amount=bet_amount,
        win_amount=win_amount,
        result=result_text
    )
    
    # Get updated balance
    updated_user = await get_user(user_id)
    new_balance_str = await format_usd(updated_user['balance'])
    
    # Create result message
    slots_display = f"{reels[0]} | {reels[1]} | {reels[2]}"
    
    if win_amount > 0:
        net_profit = win_amount - bet_amount
        result_message = f"""
🎰 <b>SLOT MACHINE RESULT</b> 🎰

{slots_display}

🎉 <b>{result_text}</b>

💰 <b>Bet:</b> ${bet_amount:.2f}
🏆 <b>Won:</b> ${win_amount:.2f}
📈 <b>Profit:</b> ${net_profit:.2f}
📊 <b>Balance:</b> {new_balance_str}

<i>Keep spinning! 🍀</i>
"""
    else:
        result_message = f"""
🎰 <b>SLOT MACHINE RESULT</b> 🎰

{slots_display}

😔 <b>{result_text}</b>

💰 <b>Bet:</b> ${bet_amount:.2f}
💸 <b>Lost:</b> ${bet_amount:.2f}
📊 <b>Balance:</b> {new_balance_str}

<i>Better luck next time! 🍀</i>
"""
    
    # Add play again button
    keyboard = [
        [
            InlineKeyboardButton("🎰 Play Again", callback_data="game_slots"),
            InlineKeyboardButton("🎮 Other Games", callback_data="mini_app_centre")
        ],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_custom:
        await message.reply_text(result_message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text(result_message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def handle_slots_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle slot machine betting callbacks."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data
    
    if data == "game_slots":
        await show_slots_menu(update, context)
        return
    
    if data == "slots_custom_bet":
        await request_custom_bet(update, context)
        return
    
    if data.startswith("slots_bet_"):
        # Extract bet amount from callback data
        bet_amount = float(data.split('_')[-1])
        
        # Check if user has enough balance
        user_data = await get_user(user_id)
        if not user_data or user_data['balance'] < bet_amount:
            await query.edit_message_text("❌ Insufficient balance! Use /daily for free chips.")
            return
        
        # Play the game
        await play_slots_game(query, context, bet_amount)
