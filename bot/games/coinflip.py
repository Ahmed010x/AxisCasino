# bot/games/coinflip.py
"""
Coin Flip Game Module
Simple 50/50 game - bet on Heads or Tails with custom Telegram emoji
"""

import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Game configuration
MIN_BET = 0.50
MAX_BET = 1000.0
WIN_MULTIPLIER = 1.95  # 95% payout (5% house edge)

# Custom Telegram Emoji IDs for Heads and Tails
HEADS_EMOJI_ID = "5886663771962743061"
TAILS_EMOJI_ID = "5886234567290918532"

async def handle_coinflip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main handler for coin flip game"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "game_coinflip":
        await show_coinflip_menu(update, context)
    elif data == "coinflip_custom_bet":
        await request_custom_bet(update, context)
    elif data.startswith("coinflip_bet_"):
        bet_amount = float(data.split("_")[2])
        await show_coinflip_choice(update, context, bet_amount)
    elif data.startswith("coinflip_play_"):
        await play_coinflip(update, context)

async def show_coinflip_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show coin flip betting interface"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Import here to avoid circular dependency
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
🪙 <b>COIN FLIP</b> 🪙

💰 <b>Your Balance:</b> {balance_str}

🎮 <b>How to Play:</b>
• Choose your bet amount
• Pick Heads or Tails
• Win {WIN_MULTIPLIER}x your bet!

💡 <b>Game Info:</b>
• Fair 50/50 odds
• Instant results with custom emoji
• Win probability: 50%
• Payout: {WIN_MULTIPLIER}x bet

<b>Choose your bet amount:</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("$1", callback_data="coinflip_bet_1"),
            InlineKeyboardButton("$5", callback_data="coinflip_bet_5"),
            InlineKeyboardButton("$10", callback_data="coinflip_bet_10")
        ],
        [
            InlineKeyboardButton("$25", callback_data="coinflip_bet_25"),
            InlineKeyboardButton("$50", callback_data="coinflip_bet_50"),
            InlineKeyboardButton("$100", callback_data="coinflip_bet_100")
        ],
        [
            InlineKeyboardButton(f"💰 Half (${half_balance:.2f})", callback_data=f"coinflip_bet_{half_balance:.2f}"),
            InlineKeyboardButton(f"🎰 All-In (${all_balance:.2f})", callback_data=f"coinflip_bet_{all_balance:.2f}")
        ],
        [InlineKeyboardButton("✏️ Custom Amount", callback_data="coinflip_custom_bet")],
        [InlineKeyboardButton("🔙 Back to Games", callback_data="mini_app_centre")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def show_coinflip_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, bet_amount: float):
    """Show heads/tails choice screen"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Import here to avoid circular dependency
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, format_usd
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found. Please restart with /start")
        return
    
    if user['balance'] < bet_amount:
        balance_str = await format_usd(user['balance'])
        await query.edit_message_text(
            f"❌ Insufficient balance!\n\nYour balance: {balance_str}\nRequired: ${bet_amount:.2f}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_coinflip")]])
        )
        return
    
    # Store bet amount in context
    context.user_data['coinflip_bet'] = bet_amount
    
    potential_win = bet_amount * WIN_MULTIPLIER
    
    text = f"""
🪙 <b>COIN FLIP</b> 🪙

💰 <b>Bet Amount:</b> ${bet_amount:.2f}
💵 <b>Potential Win:</b> ${potential_win:.2f}

<b>Choose your side:</b>
Will it be Heads or Tails?

🟡 <b>HEADS</b> = Custom gold coin emoji
🔵 <b>TAILS</b> = Custom blue coin emoji
"""
    
    # Button text with descriptions since custom emojis might not display in buttons
    heads_button_text = "🟡 HEADS"
    tails_button_text = "🔵 TAILS"
    
    keyboard = [
        [
            InlineKeyboardButton(heads_button_text, callback_data=f"coinflip_play_heads_{bet_amount}"),
            InlineKeyboardButton(tails_button_text, callback_data=f"coinflip_play_tails_{bet_amount}")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="game_coinflip")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def play_coinflip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute the coin flip game"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data_parts = query.data.split("_")
    choice = data_parts[2]  # "heads" or "tails"
    bet_amount = float(data_parts[3])
    
    # Import here to avoid circular dependency
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, deduct_balance, update_balance, log_game_session, update_house_balance_on_game, format_usd
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found. Please restart with /start")
        return
    
    # Validate balance
    if user['balance'] < bet_amount:
        balance_str = await format_usd(user['balance'])
        await query.edit_message_text(
            f"❌ Insufficient balance!\n\nYour balance: {balance_str}\nRequired: ${bet_amount:.2f}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_coinflip")]])
        )
        return
    
    # Deduct bet amount
    if not await deduct_balance(user_id, bet_amount):
        await query.edit_message_text(
            "❌ Error processing bet. Please try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_coinflip")]])
        )
        return
    
    # Flip the coin
    result = random.choice(['heads', 'tails'])
    won = (result == choice)
    
    # Calculate winnings
    win_amount = bet_amount * WIN_MULTIPLIER if won else 0.0
    net_profit = win_amount - bet_amount
    
    # Update balance if won
    if won:
        await update_balance(user_id, win_amount)
    
    # Update house balance
    await update_house_balance_on_game(bet_amount, win_amount)
    
    # Log game session
    await log_game_session(
        user_id=user_id,
        game_type="coinflip",
        bet_amount=bet_amount,
        win_amount=win_amount,
        result=f"{'WIN' if won else 'LOSS'} - {result}"
    )
    
    # Get updated balance
    updated_user = await get_user(user_id)
    new_balance_str = await format_usd(updated_user['balance'])
    
    # Determine which emoji to use
    emoji_id = HEADS_EMOJI_ID if result == "heads" else TAILS_EMOJI_ID
    result_text = "HEADS" if result == "heads" else "TAILS"
    result_color = "�" if result == "heads" else "�"  # Yellow for Heads, Blue for Tails
    
    # Delete the old message first
    try:
        await query.message.delete()
        logger.info(f"Deleted old message for user {user_id}")
    except Exception as e:
        logger.error(f"Could not delete message: {e}")
    
    # Send the custom emoji result
    try:
        # Send custom emoji animation with proper formatting
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🎰 <b>FLIPPING COIN...</b> 🎰",
            parse_mode=ParseMode.HTML
        )
        
        # Add a small delay for dramatic effect
        import asyncio
        await asyncio.sleep(1)
        
        # Try to send as custom emoji sticker first
        try:
            await context.bot.send_sticker(
                chat_id=query.message.chat_id,
                sticker=emoji_id  # Send as custom emoji sticker
            )
            logger.info(f"Sent coin flip custom emoji sticker for {result}")
        except Exception as sticker_error:
            logger.warning(f"Custom emoji sticker failed, trying as emoji: {sticker_error}")
            # Alternative: Send custom emoji in message using custom_emoji_id
            try:
                # This is the correct way to send custom emojis via Bot API
                from telegram import MessageEntity
                
                result_message = f"🎰 COIN FLIP RESULT 🎰\n\n🪙 {result_text}! 🪙\n\nThe coin has landed!"
                
                # Create message entity for custom emoji
                entities = [
                    MessageEntity(
                        type=MessageEntity.CUSTOM_EMOJI,
                        offset=result_message.find("🪙"),
                        length=1,
                        custom_emoji_id=emoji_id
                    ),
                    MessageEntity(
                        type=MessageEntity.CUSTOM_EMOJI,
                        offset=result_message.rfind("🪙"),
                        length=1,
                        custom_emoji_id=emoji_id
                    )
                ]
                
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=result_message,
                    entities=entities
                )
                logger.info(f"Sent coin flip with custom emoji entities for {result}")
            except Exception as entity_error:
                logger.error(f"Custom emoji entities failed: {entity_error}")
                # Final fallback to regular message
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"🎰 <b>COIN FLIP RESULT</b> 🎰\n\n<b>{result_text}!</b>\n\n<i>The coin has landed!</i>",
                    parse_mode=ParseMode.HTML
                )
        
    except Exception as e:
        logger.error(f"Failed to send coin flip result: {e}")
        # Fallback to regular message
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🎰 <b>COIN FLIP RESULT</b> 🎰\n\n<b>{result_text}!</b>\n\n<i>The coin has landed!</i>",
            parse_mode=ParseMode.HTML
        )
    
    # Build result text without custom emoji in text (since we sent it as sticker)
    if won:
        text = f"""
🎉 <b>YOU WIN!</b> 🎉

<b>Result: {result_text}</b>

💰 <b>Bet:</b> ${bet_amount:.2f}
💵 <b>Won:</b> ${win_amount:.2f}
📈 <b>Profit:</b> ${net_profit:.2f}

💳 <b>New Balance:</b> {new_balance_str}

<i>🎯 Congratulations! You predicted correctly!</i>
"""
    else:
        text = f"""
💔 <b>YOU LOSE</b> 💔

<b>Result: {result_text}</b>

💰 <b>Bet:</b> ${bet_amount:.2f}
💸 <b>Lost:</b> ${bet_amount:.2f}

💳 <b>New Balance:</b> {new_balance_str}

<i>🍀 Better luck next time!</i>
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Play Again", callback_data="game_coinflip")],
        [InlineKeyboardButton("🎮 Other Games", callback_data="mini_app_centre")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    # Send new message with results
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def request_custom_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request custom bet amount from user"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Import here to avoid circular dependency
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
    context.user_data['awaiting_coinflip_custom_bet'] = True
    
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
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Coin Flip", callback_data="game_coinflip")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def handle_custom_bet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom bet amount input from user"""
    if not context.user_data.get('awaiting_coinflip_custom_bet'):
        return
    
    user_id = update.message.from_user.id
    
    # Import here to avoid circular dependency
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
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_coinflip")]])
            )
            return
        
        if bet_amount > MAX_BET:
            await update.message.reply_text(
                f"❌ Bet amount too high!\n\nMaximum bet: ${MAX_BET:.2f}\nYour input: ${bet_amount:.2f}\n\nPlease try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_coinflip")]])
            )
            return
        
        user = await get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found. Please restart with /start")
            return
        
        if bet_amount > user['balance']:
            balance_str = await format_usd(user['balance'])
            await update.message.reply_text(
                f"❌ Insufficient balance!\n\nYour balance: {balance_str}\nBet amount: ${bet_amount:.2f}\n\nPlease try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_coinflip")]])
            )
            return
        
        # Clear the awaiting state
        context.user_data['awaiting_coinflip_custom_bet'] = False
        
        # Show the choice screen with custom bet amount
        potential_win = bet_amount * WIN_MULTIPLIER
        
        text = f"""
🪙 <b>COIN FLIP</b> 🪙

💰 <b>Bet Amount:</b> ${bet_amount:.2f}
💵 <b>Potential Win:</b> ${potential_win:.2f}

<b>Choose your side:</b>
Will it be Heads or Tails?

🟡 <b>HEADS</b> = Gold coin side
🔵 <b>TAILS</b> = Blue coin side
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🟡 HEADS", callback_data=f"coinflip_play_heads_{bet_amount}"),
                InlineKeyboardButton("🔵 TAILS", callback_data=f"coinflip_play_tails_{bet_amount}")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="game_coinflip")]
        ]
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        
    except ValueError:
        await update.message.reply_text(
            f"❌ Invalid input!\n\nPlease enter a valid number (e.g., 15.50)\n\nTry again:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_coinflip")]])
        )

# Export handlers
__all__ = ['handle_coinflip_callback', 'handle_custom_bet_input']
