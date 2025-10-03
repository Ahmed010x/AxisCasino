# bot/games/dice_predict.py
"""
Dice Predict Game Module
Players predict the outcome of a dice roll (1-6)
Correct prediction = 5x payout
"""

import random
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Game configuration
MIN_BET = 1.0
MAX_BET = 1000.0
WIN_MULTIPLIER = 5.0  # 5x payout for correct prediction
HOUSE_EDGE = 0.17  # ~17% house edge (fair for 1/6 odds, normal would be 6x)

async def handle_dice_predict_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main handler for dice prediction game"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "game_dice_predict":
        await show_dice_predict_menu(update, context)
    elif data == "dice_predict_custom_bet":
        await request_custom_bet(update, context)
    elif data.startswith("dice_predict_bet_"):
        bet_amount = float(data.split("_")[3])
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
• Predict the dice number (1-6)
• Correct prediction = <b>5x</b> your bet!
• Wrong prediction = lose your bet

📊 <b>Win Chance:</b> 16.67% (1 in 6)
💵 <b>Payout:</b> 5.00x

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
    """Show dice number selection interface"""
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
    
    potential_win = bet_amount * WIN_MULTIPLIER
    
    text = f"""
🎲 <b>DICE PREDICT</b> 🎲

💰 <b>Bet Amount:</b> ${bet_amount:.2f}
💵 <b>Potential Win:</b> ${potential_win:.2f}
📈 <b>Profit:</b> ${potential_win - bet_amount:.2f}

🎯 <b>Select your predicted number (1-6):</b>
"""
    
    # Create number selection keyboard
    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data=f"dice_predict_play_{bet_amount}_1"),
            InlineKeyboardButton("2️⃣", callback_data=f"dice_predict_play_{bet_amount}_2"),
            InlineKeyboardButton("3️⃣", callback_data=f"dice_predict_play_{bet_amount}_3")
        ],
        [
            InlineKeyboardButton("4️⃣", callback_data=f"dice_predict_play_{bet_amount}_4"),
            InlineKeyboardButton("5️⃣", callback_data=f"dice_predict_play_{bet_amount}_5"),
            InlineKeyboardButton("6️⃣", callback_data=f"dice_predict_play_{bet_amount}_6")
        ],
        [InlineKeyboardButton("🔙 Change Bet", callback_data="game_dice_predict")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

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
    
    potential_win = bet_amount * WIN_MULTIPLIER
    
    text = f"""
🎲 <b>DICE PREDICT</b> 🎲

💰 <b>Bet Amount:</b> ${bet_amount:.2f}
💵 <b>Potential Win:</b> ${potential_win:.2f}
📈 <b>Profit:</b> ${potential_win - bet_amount:.2f}

🎯 <b>Select your predicted number (1-6):</b>
"""
    
    # Create number selection keyboard
    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data=f"dice_predict_play_{bet_amount}_1"),
            InlineKeyboardButton("2️⃣", callback_data=f"dice_predict_play_{bet_amount}_2"),
            InlineKeyboardButton("3️⃣", callback_data=f"dice_predict_play_{bet_amount}_3")
        ],
        [
            InlineKeyboardButton("4️⃣", callback_data=f"dice_predict_play_{bet_amount}_4"),
            InlineKeyboardButton("5️⃣", callback_data=f"dice_predict_play_{bet_amount}_5"),
            InlineKeyboardButton("6️⃣", callback_data=f"dice_predict_play_{bet_amount}_6")
        ],
        [InlineKeyboardButton("🔙 Change Bet", callback_data="game_dice_predict")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def play_dice_predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Play the dice prediction game"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Parse bet amount and predicted number from callback data
    # Format: dice_predict_play_{bet_amount}_{predicted_number}
    parts = query.data.split("_")
    bet_amount = float(parts[3])
    predicted_number = int(parts[4])
    
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
    
    # Check win condition
    won = actual_number == predicted_number
    
    # Calculate winnings
    if won:
        win_amount = bet_amount * WIN_MULTIPLIER
        net_profit = win_amount - bet_amount
        await update_balance(user_id, win_amount)
    else:
        win_amount = 0.0
        net_profit = -bet_amount
    
    # Update house balance
    await update_house_balance_on_game(bet_amount, win_amount)
    
    # Log game session
    await log_game_session(
        user_id=user_id,
        game_type="dice_predict",
        bet_amount=bet_amount,
        win_amount=win_amount,
        result=f"{'WIN' if won else 'LOSS'} - Predicted: {predicted_number}, Rolled: {actual_number}"
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
    
    # Build result message
    if won:
        text = f"""
🎉 <b>CORRECT PREDICTION!</b> 🎉

🎲 <b>Your Prediction:</b> {number_emojis[predicted_number]}
🎲 <b>Dice Result:</b> {number_emojis[actual_number]}

✅ <b>MATCH! YOU WIN!</b>

💰 <b>Bet:</b> ${bet_amount:.2f}
💵 <b>Won:</b> ${win_amount:.2f}
📈 <b>Profit:</b> ${net_profit:.2f}

💳 <b>New Balance:</b> {new_balance_str}
"""
    else:
        text = f"""
😔 <b>WRONG PREDICTION</b>

🎲 <b>Your Prediction:</b> {number_emojis[predicted_number]}
🎲 <b>Dice Result:</b> {number_emojis[actual_number]}

❌ <b>NO MATCH</b>

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
