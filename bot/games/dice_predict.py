# bot/games/dice_predict.py
"""
Dice Predict Game Module
Players predict the outcome of a dice roll (1-6)
Variable payouts based on number of selections:
- 1 number: 5.76x multiplier
- 2 numbers: 2.88x multiplier
- 3 numbers: 1.92x multiplier
- 4 numbers: 1.44x multiplier
- 5 numbers: 1.15x multiplier
"""

import random
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Game configuration
MIN_BET = 0.50
MAX_BET = 1000.0

# Multipliers based on number of selections
MULTIPLIERS = {
    1: 5.76,  # Select 1 number
    2: 2.88,  # Select 2 numbers
    3: 1.92,  # Select 3 numbers
    4: 1.44,  # Select 4 numbers
    5: 1.15,  # Select 5 numbers
    6: 0.96   # Select all 6 numbers (slight loss - discouraged)
}

async def handle_dice_predict_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main handler for dice prediction game"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "game_dice_predict":
        # Clear any previous selections
        context.user_data.pop('dice_predict_selections', None)
        context.user_data.pop('dice_predict_bet_amount', None)
        await show_dice_predict_menu(update, context)
    elif data == "dice_predict_custom_bet":
        await request_custom_bet(update, context)
    elif data.startswith("dice_predict_bet_"):
        bet_amount = float(data.split("_")[3])
        # Clear previous selections and start fresh
        context.user_data['dice_predict_selections'] = []
        await show_number_selection(update, context, bet_amount)
    elif data.startswith("dice_predict_toggle_"):
        # Toggle number selection
        await toggle_number_selection(update, context)
    elif data == "dice_predict_clear":
        # Clear all selections
        context.user_data['dice_predict_selections'] = []
        bet_amount = context.user_data.get('dice_predict_bet_amount', 0)
        await show_number_selection(update, context, bet_amount)
    elif data.startswith("dice_predict_play_"):
        await play_dice_predict(update, context)

async def show_dice_predict_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show dice prediction betting interface"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Import here to avoid circular dependency
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, format_usd
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found. Please use /start")
        return
    
    balance = user['balance']
    balance_str = await format_usd(balance)
    
    text = f"""
🎲 <b>DICE PREDICT</b> 🎲

💰 <b>Balance:</b> {balance_str}

🎯 <b>Game Rules:</b>
• Select 1-5 numbers from the dice (1-6)
• If dice lands on any of your numbers, you win!
• More numbers = better odds, lower multiplier

📊 <b>Payouts:</b>
1️⃣ number: 5.76x (17% chance)
2️⃣ numbers: 2.88x (33% chance)
3️⃣ numbers: 1.92x (50% chance)
4️⃣ numbers: 1.44x (67% chance)
5️⃣ numbers: 1.15x (83% chance)

<b>Select your bet amount:</b>
"""
    
    # Create betting keyboard
    keyboard = []
    
    # Quick bet amounts
    quick_bets = [5.0, 10.0, 25.0, 50.0, 100.0]
    row = []
    for bet in quick_bets:
        if bet <= balance:
            row.append(InlineKeyboardButton(f"${bet:.0f}", callback_data=f"dice_predict_bet_{bet}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
    if row:
        keyboard.append(row)
    
    # Custom bet options
    custom_row = []
    if balance >= 1.0:
        custom_row.append(InlineKeyboardButton("💰 Half", callback_data=f"dice_predict_bet_{balance/2}"))
    if balance >= 2.0:
        custom_row.append(InlineKeyboardButton("🎰 All-In", callback_data=f"dice_predict_bet_{balance}"))
    custom_row.append(InlineKeyboardButton("✏️ Custom", callback_data="dice_predict_custom_bet"))
    keyboard.append(custom_row)
    
    # Back button
    keyboard.append([InlineKeyboardButton("🔙 Back to Games", callback_data="games")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error showing dice predict menu: {e}")
        await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def request_custom_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request custom bet amount from user"""
    query = update.callback_query
    
    text = f"""
✏️ <b>CUSTOM BET AMOUNT</b>

Please enter your bet amount:

💵 <b>Minimum:</b> ${MIN_BET}
💰 <b>Maximum:</b> ${MAX_BET}

<i>Type the amount and send it as a message.</i>
"""
    
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="game_dice_predict")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Set state for custom bet input
    context.user_data['awaiting_dice_predict_custom_bet'] = True
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def handle_custom_bet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom bet amount input"""
    if not context.user_data.get('awaiting_dice_predict_custom_bet'):
        return
    
    user_id = update.message.from_user.id
    
    # Import here to avoid circular dependency
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user
    
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("❌ User not found. Please use /start")
        return
    
    try:
        bet_amount = float(update.message.text.strip().replace('$', ''))
        
        # Validate bet amount
        if bet_amount < MIN_BET:
            await update.message.reply_text(f"❌ Minimum bet is ${MIN_BET}")
            return
        
        if bet_amount > MAX_BET:
            await update.message.reply_text(f"❌ Maximum bet is ${MAX_BET}")
            return
        
        if bet_amount > user['balance']:
            await update.message.reply_text(f"❌ Insufficient balance. You have ${user['balance']:.2f}")
            return
        
        # Clear the state
        context.user_data.pop('awaiting_dice_predict_custom_bet', None)
        
        # Show number selection
        await show_number_selection_message(update, context, bet_amount)
        
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number")

async def show_number_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, bet_amount: float):
    """Show dice number selection interface with multi-select support"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Import here to avoid circular dependency
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, format_usd
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found. Please use /start")
        return
    
    # Validate balance
    if bet_amount > user['balance']:
        await query.edit_message_text(
            f"❌ Insufficient balance!\n\nYou need ${bet_amount:.2f} but only have ${user['balance']:.2f}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="game_dice_predict")
            ]])
        )
        return
    
    # Store bet amount in context
    context.user_data['dice_predict_bet_amount'] = bet_amount
    
    # Get current selections (empty list if none)
    selected = context.user_data.get('dice_predict_selections', [])
    num_selected = len(selected)
    
    # Calculate potential win based on selections
    if num_selected > 0 and num_selected <= 5:
        multiplier = MULTIPLIERS.get(num_selected, 1.0)
        potential_win = bet_amount * multiplier
        win_chance = (num_selected / 6) * 100
    else:
        multiplier = 0
        potential_win = 0
        win_chance = 0
    
    # Build selection display
    selected_str = ", ".join([f"{n}" for n in sorted(selected)]) if selected else "None"
    
    text = f"""
🎲 <b>DICE PREDICT</b> 🎲

💰 <b>Bet Amount:</b> ${bet_amount:.2f}
🎯 <b>Selected:</b> {selected_str}
� <b>Count:</b> {num_selected}/5

"""
    
    if num_selected > 0:
        text += f"""�💵 <b>Multiplier:</b> {multiplier:.2f}x
📈 <b>Win Chance:</b> {win_chance:.1f}%
🏆 <b>Potential Win:</b> ${potential_win:.2f}
� <b>Profit:</b> ${potential_win - bet_amount:.2f}

"""
    
    text += "<b>🎯 Select your numbers (1-5 numbers):</b>"
    
    # Create number selection keyboard with toggle buttons
    number_emojis = {
        1: "1️⃣", 2: "2️⃣", 3: "3️⃣",
        4: "4️⃣", 5: "5️⃣", 6: "6️⃣"
    }
    
    keyboard = []
    row = []
    for num in range(1, 7):
        # Show checkmark if selected
        if num in selected:
            button_text = f"✅ {number_emojis[num]}"
        else:
            button_text = number_emojis[num]
        
        row.append(InlineKeyboardButton(
            button_text,
            callback_data=f"dice_predict_toggle_{num}"
        ))
        
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Add play button (only if at least 1 number selected)
    if num_selected > 0 and num_selected <= 5:
        keyboard.append([
            InlineKeyboardButton(
                f"🎲 ROLL DICE ({multiplier:.2f}x)",
                callback_data=f"dice_predict_play_{bet_amount}"
            )
        ])
    
    # Add utility buttons
    utility_row = []
    if num_selected > 0:
        utility_row.append(InlineKeyboardButton("🔄 Clear All", callback_data="dice_predict_clear"))
    utility_row.append(InlineKeyboardButton("🔙 Change Bet", callback_data="game_dice_predict"))
    keyboard.append(utility_row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def toggle_number_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle a number in the selection list"""
    query = update.callback_query
    
    # Parse the number from callback data
    # Format: dice_predict_toggle_{number}
    parts = query.data.split("_")
    number = int(parts[3])
    
    # Get current selections
    selected = context.user_data.get('dice_predict_selections', [])
    bet_amount = context.user_data.get('dice_predict_bet_amount', 0)
    
    # Toggle the number
    if number in selected:
        selected.remove(number)
    else:
        # Only allow up to 5 selections
        if len(selected) < 5:
            selected.append(number)
        else:
            await query.answer("❌ Maximum 5 numbers allowed!", show_alert=True)
            return
    
    # Update the selections
    context.user_data['dice_predict_selections'] = selected
    
    # Refresh the display
    await show_number_selection(update, context, bet_amount)
    await query.answer()

async def show_number_selection_message(update: Update, context: ContextTypes.DEFAULT_TYPE, bet_amount: float):
    """Show number selection as a new message (for custom bet)"""
    user_id = update.message.from_user.id
    
    # Import here to avoid circular dependency
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user
    
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("❌ User not found. Please use /start")
        return
    
    # Initialize selections
    context.user_data['dice_predict_selections'] = []
    context.user_data['dice_predict_bet_amount'] = bet_amount
    
    # Get current selections (empty list)
    selected = []
    
    # Build selection display
    text = f"""
🎲 <b>DICE PREDICT</b> 🎲

💰 <b>Bet Amount:</b> ${bet_amount:.2f}
🎯 <b>Selected:</b> None
📊 <b>Count:</b> 0/5

<b>🎯 Select your numbers (1-5 numbers):</b>

📊 <b>Payouts:</b>
• 1 number: 5.76x
• 2 numbers: 2.88x
• 3 numbers: 1.92x
• 4 numbers: 1.44x
• 5 numbers: 1.15x
"""
    
    # Create number selection keyboard with toggle buttons
    number_emojis = {
        1: "1️⃣", 2: "2️⃣", 3: "3️⃣",
        4: "4️⃣", 5: "5️⃣", 6: "6️⃣"
    }
    
    keyboard = []
    row = []
    for num in range(1, 7):
        button_text = number_emojis[num]
        row.append(InlineKeyboardButton(
            button_text,
            callback_data=f"dice_predict_toggle_{num}"
        ))
        
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Change Bet", callback_data="game_dice_predict")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def play_dice_predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Play the dice prediction game with multiple number selection"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Get bet amount and selected numbers from context
    bet_amount = context.user_data.get('dice_predict_bet_amount', 0)
    selected_numbers = context.user_data.get('dice_predict_selections', [])
    
    # Validate selections
    if not selected_numbers or len(selected_numbers) > 5:
        await query.answer("❌ Please select 1-5 numbers!", show_alert=True)
        return
    
    # Import here to avoid circular dependency
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import (
        get_user, deduct_balance, update_balance, 
        log_game_session, format_usd,
        update_house_balance_on_game
    )
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found. Please use /start")
        return
    
    # Check balance
    if bet_amount > user['balance']:
        await query.answer("❌ Insufficient balance!", show_alert=True)
        return
    
    # Deduct bet amount
    if not await deduct_balance(user_id, bet_amount):
        await query.answer("❌ Failed to place bet!", show_alert=True)
        return
    
    # Delete the old message first
    try:
        await query.message.delete()
    except Exception as e:
        logger.error(f"Could not delete message: {e}")
    
    # Send dice animation using Telegram's native dice
    # The dice value will be our actual result for fairness and sync
    dice_msg = None
    actual_number = None
    
    try:
        dice_msg = await context.bot.send_dice(
            chat_id=query.message.chat_id,
            emoji="🎲"
        )
        # Get the actual dice value from Telegram's animation
        actual_number = dice_msg.dice.value
        logger.info(f"Dice animation sent, result: {actual_number}")
    except Exception as e:
        logger.error(f"Failed to send dice animation: {e}")
        # Fallback: generate random number if dice fails
        actual_number = random.randint(1, 6)
        logger.warning(f"Using fallback random number: {actual_number}")
    
    # Check win condition - did the dice land on any of the selected numbers?
    won = actual_number in selected_numbers
    
    # Get multiplier based on number of selections
    num_selected = len(selected_numbers)
    multiplier = MULTIPLIERS.get(num_selected, 1.0)
    
    # Calculate winnings
    if won:
        win_amount = bet_amount * multiplier
        net_profit = win_amount - bet_amount
        await update_balance(user_id, win_amount)
    else:
        win_amount = 0.0
        net_profit = -bet_amount
    
    # Update house balance
    await update_house_balance_on_game(bet_amount, win_amount)
    
    # Format selected numbers for logging
    selected_str = ", ".join([str(n) for n in sorted(selected_numbers)])
    
    # Log game session
    await log_game_session(
        user_id=user_id,
        game_type="dice_predict",
        bet_amount=bet_amount,
        win_amount=win_amount,
        result=f"{'WIN' if won else 'LOSS'} - Selected: [{selected_str}], Rolled: {actual_number}, Multiplier: {multiplier}x"
    )
    
    # Get updated balance
    updated_user = await get_user(user_id)
    new_balance_str = await format_usd(updated_user['balance'])
    
    # Wait for dice animation to complete (animation takes ~4 seconds)
    await asyncio.sleep(4)
    
    # Number emojis
    number_emojis = {
        1: "1️⃣",
        2: "2️⃣",
        3: "3️⃣",
        4: "4️⃣",
        5: "5️⃣",
        6: "6️⃣"
    }
    
    # Build selected numbers display
    selected_display = " ".join([number_emojis[n] for n in sorted(selected_numbers)])
    
    # Build result message
    if won:
        text = f"""
🎉 <b>YOU WIN!</b> 🎉

� <b>Your Numbers:</b> {selected_display}
🎲 <b>Dice Result:</b> {number_emojis[actual_number]}

✅ <b>MATCH! ({num_selected} number{'s' if num_selected > 1 else ''})</b>

💰 <b>Bet:</b> ${bet_amount:.2f}
📊 <b>Multiplier:</b> {multiplier:.2f}x
💵 <b>Won:</b> ${win_amount:.2f}
📈 <b>Profit:</b> ${net_profit:.2f}

💳 <b>New Balance:</b> {new_balance_str}
"""
    else:
        text = f"""
😔 <b>NO MATCH</b>

� <b>Your Numbers:</b> {selected_display}
🎲 <b>Dice Result:</b> {number_emojis[actual_number]}

❌ <b>Not in your selection</b>

💰 <b>Bet:</b> ${bet_amount:.2f}
💸 <b>Lost:</b> ${bet_amount:.2f}

💳 <b>New Balance:</b> {new_balance_str}

<i>Better luck next time!</i>
"""
    
    # Play again buttons
    keyboard = [
        [
            InlineKeyboardButton("🔄 Same Bet", callback_data=f"dice_predict_bet_{bet_amount}"),
            InlineKeyboardButton("💰 Double Bet", callback_data=f"dice_predict_bet_{bet_amount * 2}")
        ],
        [
            InlineKeyboardButton("🎲 New Bet", callback_data="game_dice_predict"),
            InlineKeyboardButton("🎮 Other Games", callback_data="games")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send result message
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
