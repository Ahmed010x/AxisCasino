"""
Dice Game

Simple dice betting game where players predict if the sum of two dice
will be high (8-12) or low (3-7), or bet on specific numbers.
"""

import random
from typing import Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database.user import get_user, add_game_result


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


async def play_dice_game(user_id: int, bet_type: str, bet_amount: int, target_sum: int = None) -> Tuple[int, int, int, bool, int, str]:
    """Play a dice game."""
    # Roll the dice
    die1, die2 = roll_dice()
    total = die1 + die2
    
    # Determine if bet wins
    is_win = False
    payout_multiplier = 1
    
    if bet_type == 'high':
        is_win = total >= 8
        payout_multiplier = 1  # 1:1 payout
        result_text = f"HIGH BET ({'WIN' if is_win else 'LOSE'})"
    elif bet_type == 'low':
        is_win = total <= 7
        payout_multiplier = 1  # 1:1 payout  
        result_text = f"LOW BET ({'WIN' if is_win else 'LOSE'})"
    elif bet_type == 'exact':
        is_win = total == target_sum
        # Higher payout for exact number
        if target_sum in [2, 12]:  # Hardest to get
            payout_multiplier = 30
        elif target_sum in [3, 11]:
            payout_multiplier = 15
        elif target_sum in [4, 10]:
            payout_multiplier = 8
        elif target_sum in [5, 9]:
            payout_multiplier = 5
        elif target_sum in [6, 8]:
            payout_multiplier = 3
        else:  # 7 - most common
            payout_multiplier = 2
        result_text = f"EXACT {target_sum} BET ({'WIN' if is_win else 'LOSE'})"
    
    # Calculate winnings
    if is_win:
        win_amount = bet_amount * (payout_multiplier + 1)  # Include original bet
    else:
        win_amount = 0
    
    # Record game result
    await add_game_result(user_id, 'dice', bet_amount, win_amount, result_text)
    
    # Get updated balance
    user_data = await get_user(user_id)
    new_balance = user_data['balance'] if user_data else 0
    
    return die1, die2, total, is_win, win_amount, new_balance


async def show_dice_menu(update: Update, balance: int):
    """Show dice betting menu."""
    dice_text = f"""
🎲 **DICE GAME** 🎲

Current Balance: **{balance} chips**

**Game Rules:**
Roll two dice and bet on the outcome!

**Betting Options:**
🔺 **HIGH (8-12)** - 1:1 payout - 20 chips
🔻 **LOW (3-7)** - 1:1 payout - 20 chips  
🎯 **EXACT NUMBER** - Variable payouts - 10 chips

Choose your bet:
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🔺 HIGH (8-12)", callback_data="dice_bet_high_20"),
            InlineKeyboardButton("🔻 LOW (3-7)", callback_data="dice_bet_low_20")
        ],
        [
            InlineKeyboardButton("🎯 Exact Number", callback_data="dice_exact_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(dice_text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_exact_number_menu(query):
    """Show exact number betting menu."""
    exact_text = """
🎯 **EXACT NUMBER BET**

Bet 10 chips on the exact sum of two dice:

**Payouts:**
• 2 or 12: 30:1 (300 chips)
• 3 or 11: 15:1 (150 chips)  
• 4 or 10: 8:1 (80 chips)
• 5 or 9: 5:1 (50 chips)
• 6 or 8: 3:1 (30 chips)
• 7: 2:1 (20 chips)

Choose your number:
"""
    
    keyboard = [
        [
            InlineKeyboardButton("2 (30:1)", callback_data="dice_bet_exact_10_2"),
            InlineKeyboardButton("3 (15:1)", callback_data="dice_bet_exact_10_3"),
            InlineKeyboardButton("4 (8:1)", callback_data="dice_bet_exact_10_4")
        ],
        [
            InlineKeyboardButton("5 (5:1)", callback_data="dice_bet_exact_10_5"),
            InlineKeyboardButton("6 (3:1)", callback_data="dice_bet_exact_10_6"),
            InlineKeyboardButton("7 (2:1)", callback_data="dice_bet_exact_10_7")
        ],
        [
            InlineKeyboardButton("8 (3:1)", callback_data="dice_bet_exact_10_8"),
            InlineKeyboardButton("9 (5:1)", callback_data="dice_bet_exact_10_9"),
            InlineKeyboardButton("10 (8:1)", callback_data="dice_bet_exact_10_10")
        ],
        [
            InlineKeyboardButton("11 (15:1)", callback_data="dice_bet_exact_10_11"),
            InlineKeyboardButton("12 (30:1)", callback_data="dice_bet_exact_10_12")
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="dice_main_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(exact_text, reply_markup=reply_markup, parse_mode='Markdown')


async def handle_dice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle dice game callbacks."""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    if data == "dice_main_menu":
        user_data = await get_user(user_id)
        await show_dice_menu(update, user_data['balance'])
        return
    
    if data == "dice_exact_menu":
        await show_exact_number_menu(query)
        return
    
    if data.startswith("dice_bet_"):
        parts = data.split('_')
        bet_type = parts[2]
        bet_amount = int(parts[3])
        target_sum = None
        
        if len(parts) > 4:  # Exact number bet
            target_sum = int(parts[4])
        
        # Check balance
        user_data = await get_user(user_id)
        if not user_data or user_data['balance'] < bet_amount:
            await query.answer("❌ Insufficient balance!")
            return
        
        # Play the game
        die1, die2, total, is_win, win_amount, new_balance = await play_dice_game(
            user_id, bet_type, bet_amount, target_sum
        )
        
        # Format result
        die1_emoji = get_dice_emoji(die1)
        die2_emoji = get_dice_emoji(die2)
        
        if is_win:
            result_message = f"""
🎲 **DICE GAME RESULT** 🎲

**Dice Roll:** {die1_emoji} {die2_emoji}
**Total:** {total}

🎉 **YOU WIN!**

**Bet Type:** {bet_type.upper()}{f' (target: {target_sum})' if target_sum else ''}
**Bet Amount:** {bet_amount} chips
🏆 **Won:** {win_amount - bet_amount} chips
📊 **Balance:** {new_balance} chips

Great roll! 🍀
"""
        else:
            result_message = f"""
🎲 **DICE GAME RESULT** 🎲

**Dice Roll:** {die1_emoji} {die2_emoji}
**Total:** {total}

😔 **YOU LOSE**

**Bet Type:** {bet_type.upper()}{f' (target: {target_sum})' if target_sum else ''}
**Bet Amount:** {bet_amount} chips
💸 **Lost:** {bet_amount} chips
📊 **Balance:** {new_balance} chips

Better luck next time! 🍀
"""
        
        # Add play again buttons
        keyboard = [
            [
                InlineKeyboardButton("🎲 Roll Again", callback_data="game_dice"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(result_message, reply_markup=reply_markup, parse_mode='Markdown')
