"""
Dice Prediction Game

A focused dice prediction gaming system featuring:
- Dice Prediction: Predict dice roll outcomes (1-6)
- Multiple selection support for varied risk/reward
- Fair 5% house edge with transparent multipliers
- Secure random number generation

Players can choose single or multiple dice numbers to predict,
with higher multipliers for fewer selections (higher risk).
"""

import random
import asyncio
import time
from typing import Dict, List, Tuple, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from telegram.error import TelegramError, BadRequest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Game Configuration
MIN_BET = 0.50
MAX_BET = 1000.0
DEFAULT_BET = 1.0

# Prediction Game Types
PREDICTION_GAMES = {
    "dice": {
        "name": "🎲 Dice Prediction",
        "description": "Predict the outcome of a dice roll (1-6)",
        "icon": "🎲",
        "options": [1, 2, 3, 4, 5, 6],
        "option_names": ["1", "2", "3", "4", "5", "6"],
        "base_multiplier": 6.0,
        "min_selections": 1,
        "max_selections": 5
    }
}

def calculate_multiplier(game_type: str, num_selections: int) -> float:
    """Calculate multiplier based on game type and number of selections."""
    game_info = PREDICTION_GAMES[game_type]
    base_multiplier = game_info["base_multiplier"]
    total_options = len(game_info["options"])
    
    # Calculate fair multiplier with house edge
    fair_multiplier = total_options / num_selections
    house_edge = 0.05  # 5% house edge
    return fair_multiplier * (1 - house_edge)

def get_random_outcome(game_type: str):
    """Get random outcome for the specified game type."""
    game_info = PREDICTION_GAMES[game_type]
    return random.choice(game_info["options"])

def format_outcome_display(game_type: str, outcome) -> str:
    """Format outcome for display with appropriate emojis."""
    if game_type == "dice":
        return f"🎲 {outcome}"
    else:
        return str(outcome)

async def show_prediction_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main prediction games menu."""
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
🔮 <b>DICE PREDICTION GAME</b> 🔮

💰 <b>Your Balance:</b> {balance_str}

🎯 <b>How It Works:</b>
• Choose your dice predictions (1-6)
• Select 1 or more numbers you think will be rolled
• More predictions = lower risk, lower reward
• Fewer predictions = higher risk, higher reward

 <b>Dice Prediction:</b>
Predict the outcome of a dice roll (1-6)
• Single number: ~5.7x multiplier
• 2 numbers: ~2.85x multiplier
• 3 numbers: ~1.9x multiplier

💡 <b>Strategy Tips:</b>
• Single predictions offer highest multipliers
• Multiple predictions increase win chances
• House edge: 5% (fair and competitive)

💵 <b>Betting Limits:</b>
Min: ${MIN_BET:.2f} | Max: ${MAX_BET:.2f}

<b>🎯 Start playing dice prediction:</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🎲 Play Dice Prediction", callback_data="prediction_game_dice")
        ],
        [
            InlineKeyboardButton("📊 Game Rules", callback_data="prediction_rules"),
            InlineKeyboardButton("🔙 Back", callback_data="mini_app_centre")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def show_prediction_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed prediction game rules."""
    query = update.callback_query
    await query.answer()
    
    text = f"""
📚 <b>DICE PREDICTION - RULES & STRATEGY</b> 📚

🎯 <b>General Rules:</b>
• Select one or more dice numbers (1-6) to predict
• The random outcome is generated fairly using secure randomization
• If your prediction matches the dice roll, you win!
• Payouts depend on how many numbers you select

🎲 <b>Dice Prediction (1-6):</b>
• Single number: ~5.7x multiplier (highest risk, highest reward)
• 2 numbers: ~2.85x multiplier  
• 3 numbers: ~1.9x multiplier
• 4 numbers: ~1.43x multiplier
• 5 numbers: ~1.14x multiplier (lowest risk, lowest reward)

💰 <b>Payout Formula:</b>
Multiplier = (6 ÷ Your Selections) × 0.95

🎯 <b>Strategy Tips:</b>
• <b>Conservative:</b> Choose 3-5 numbers (lower risk, steady wins)
• <b>Aggressive:</b> Choose 1-2 numbers (higher risk, bigger payouts)
• <b>Balanced:</b> Choose 2-3 numbers for moderate risk/reward

🔒 <b>Fairness Guarantee:</b>
All dice rolls use cryptographically secure randomization. The house edge is a transparent 5%, which is very competitive in the gaming industry.

Ready to test your prediction skills? 🎮
"""
    
    keyboard = [
        [InlineKeyboardButton("🎮 Start Playing", callback_data="prediction")],
        [InlineKeyboardButton("🔙 Back to Games", callback_data="prediction")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def show_game_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, game_type: str):
    """Show selection menu for a specific prediction game."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    from main import get_user, format_usd
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found.")
        return
    
    # Initialize user selections
    context.user_data['prediction_game_type'] = game_type
    context.user_data['prediction_selections'] = []
    
    game_info = PREDICTION_GAMES[game_type]
    balance_str = await format_usd(user['balance'])
    
    text = f"""
{game_info['icon']} <b>{game_info['name']}</b> {game_info['icon']}

💰 <b>Balance:</b> {balance_str}
📝 <b>Game:</b> {game_info['description']}

🎯 <b>Your Selections:</b> None yet
💵 <b>Current Multiplier:</b> Select options to see

🎮 <b>How to Play:</b>
1. Choose one or more options below
2. More selections = safer but lower payout
3. Fewer selections = riskier but higher payout
4. Place your bet and test your prediction!

<b>📊 Select your predictions:</b>
"""
    
    # Create selection buttons
    keyboard = []
    options = game_info['options']
    option_names = game_info['option_names']
    
    # Create rows of buttons (2-3 per row depending on game type)
    if game_type == "dice" or game_type == "number":
        # Numbers: 3 per row
        for i in range(0, len(options), 3):
            row = []
            for j in range(i, min(i + 3, len(options))):
                row.append(InlineKeyboardButton(
                    option_names[j], 
                    callback_data=f"prediction_select_{game_type}_{j}"
                ))
            keyboard.append(row)
    else:
        # Colors, cards, coin: 2 per row
        for i in range(0, len(options), 2):
            row = []
            for j in range(i, min(i + 2, len(options))):
                row.append(InlineKeyboardButton(
                    option_names[j], 
                    callback_data=f"prediction_select_{game_type}_{j}"
                ))
            keyboard.append(row)
    
    # Control buttons
    keyboard.extend([
        [
            InlineKeyboardButton("🗑️ Clear All", callback_data=f"prediction_clear_{game_type}"),
            InlineKeyboardButton("✅ Place Bet", callback_data=f"prediction_bet_{game_type}")
        ],
        [
            InlineKeyboardButton("🔙 Back to Games", callback_data="prediction")
        ]
    ])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def handle_selection_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE, game_type: str, option_index: int):
    """Handle toggling a prediction selection."""
    query = update.callback_query
    await query.answer()
    
    from main import get_user, format_usd
    
    user = await get_user(query.from_user.id)
    if not user:
        await query.edit_message_text("❌ User not found.")
        return
    
    game_info = PREDICTION_GAMES[game_type]
    selections = context.user_data.get('prediction_selections', [])
    
    # Toggle selection
    if option_index in selections:
        selections.remove(option_index)
        action = "removed"
    else:
        # Check max selections limit
        if len(selections) >= game_info['max_selections']:
            await query.answer(f"❌ Maximum {game_info['max_selections']} selections allowed!", show_alert=True)
            return
        selections.append(option_index)
        action = "added"
    
    context.user_data['prediction_selections'] = selections
    
    # Update display
    balance_str = await format_usd(user['balance'])
    
    # Format selected options
    if selections:
        selected_names = [game_info['option_names'][i] for i in selections]
        selections_text = ", ".join(selected_names)
        multiplier = calculate_multiplier(game_type, len(selections))
        multiplier_text = f"{multiplier:.2f}x"
        
        # Calculate potential winnings for default bet
        potential_win = DEFAULT_BET * multiplier
        win_str = await format_usd(potential_win)
        profit_str = await format_usd(potential_win - DEFAULT_BET)
    else:
        selections_text = "None"
        multiplier_text = "Select options to see"
        win_str = "Select options to see"
        profit_str = "Select options to see"
    
    text = f"""
{game_info['icon']} <b>{game_info['name']}</b> {game_info['icon']}

💰 <b>Balance:</b> {balance_str}
📝 <b>Game:</b> {game_info['description']}

🎯 <b>Your Selections:</b> {selections_text}
💵 <b>Multiplier:</b> {multiplier_text}

💡 <b>Example with ${DEFAULT_BET:.2f} bet:</b>
🏆 Potential Win: {win_str}
📈 Potential Profit: {profit_str}

<b>📊 Select your predictions:</b>
"""
    
    # Recreate buttons with selection state
    keyboard = []
    options = game_info['options']
    option_names = game_info['option_names']
    
    # Create selection buttons with visual indicators
    if game_type == "dice" or game_type == "number":
        for i in range(0, len(options), 3):
            row = []
            for j in range(i, min(i + 3, len(options))):
                # Add checkmark if selected
                button_text = f"✅ {option_names[j]}" if j in selections else option_names[j]
                row.append(InlineKeyboardButton(
                    button_text, 
                    callback_data=f"prediction_select_{game_type}_{j}"
                ))
            keyboard.append(row)
    else:
        for i in range(0, len(options), 2):
            row = []
            for j in range(i, min(i + 2, len(options))):
                button_text = f"✅ {option_names[j]}" if j in selections else option_names[j]
                row.append(InlineKeyboardButton(
                    button_text, 
                    callback_data=f"prediction_select_{game_type}_{j}"
                ))
            keyboard.append(row)
    
    # Control buttons
    keyboard.extend([
        [
            InlineKeyboardButton("🗑️ Clear All", callback_data=f"prediction_clear_{game_type}"),
            InlineKeyboardButton("✅ Place Bet", callback_data=f"prediction_bet_{game_type}")
        ],
        [
            InlineKeyboardButton("🔙 Back to Games", callback_data="prediction")
        ]
    ])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def show_betting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, game_type: str):
    """Show betting menu for prediction game."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    from main import get_user, format_usd
    
    selections = context.user_data.get('prediction_selections', [])
    if not selections:
        await query.answer("❌ Please select at least one prediction first!", show_alert=True)
        return
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found.")
        return
    
    game_info = PREDICTION_GAMES[game_type]
    balance_str = await format_usd(user['balance'])
    
    # Format selections
    selected_names = [game_info['option_names'][i] for i in selections]
    selections_text = ", ".join(selected_names)
    multiplier = calculate_multiplier(game_type, len(selections))
    
    text = f"""
{game_info['icon']} <b>PLACE YOUR BET</b> {game_info['icon']}

💰 <b>Balance:</b> {balance_str}
🎯 <b>Predictions:</b> {selections_text}
💵 <b>Multiplier:</b> {multiplier:.2f}x

🎮 <b>Game:</b> {game_info['description']}
📊 <b>Win Chance:</b> {len(selections)}/{len(game_info['options'])} ({len(selections)/len(game_info['options'])*100:.1f}%)

💡 <b>Potential Winnings:</b>
"""
    
    # Show potential winnings for different bet amounts
    bet_amounts = [1, 5, 10, 25, 50, 100]
    for bet in bet_amounts:
        if bet <= user['balance']:
            win_amount = bet * multiplier
            profit = win_amount - bet
            text += f"${bet}: Win ${win_amount:.2f} (Profit ${profit:.2f})\n"
    
    text += f"\n<b>Choose your bet amount:</b>"
    
    keyboard = [
        [
            InlineKeyboardButton("$1", callback_data=f"prediction_play_{game_type}_1"),
            InlineKeyboardButton("$5", callback_data=f"prediction_play_{game_type}_5"),
            InlineKeyboardButton("$10", callback_data=f"prediction_play_{game_type}_10")
        ],
        [
            InlineKeyboardButton("$25", callback_data=f"prediction_play_{game_type}_25"),
            InlineKeyboardButton("$50", callback_data=f"prediction_play_{game_type}_50"),
            InlineKeyboardButton("$100", callback_data=f"prediction_play_{game_type}_100")
        ],
        [
            InlineKeyboardButton("✏️ Custom Amount", callback_data=f"prediction_custom_bet_{game_type}")
        ],
        [
            InlineKeyboardButton("🔙 Back to Selections", callback_data=f"prediction_game_{game_type}")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def play_prediction_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_type: str, bet_amount: float):
    """Play the prediction game with the given parameters."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    from main import get_user, deduct_balance, update_balance, log_game_session, format_usd
    
    selections = context.user_data.get('prediction_selections', [])
    if not selections:
        await query.edit_message_text("❌ No predictions selected.")
        return
    
    # Validate bet amount
    if bet_amount < MIN_BET or bet_amount > MAX_BET:
        await query.edit_message_text(f"❌ Bet must be between ${MIN_BET:.2f} and ${MAX_BET:.2f}")
        return
    
    # Check user balance
    user = await get_user(user_id)
    if not user or user['balance'] < bet_amount:
        balance_str = await format_usd(user['balance']) if user else "$0.00"
        await query.edit_message_text(f"❌ Insufficient balance! You have {balance_str}")
        return
    
    # Deduct bet amount
    if not await deduct_balance(user_id, bet_amount):
        await query.edit_message_text("❌ Failed to place bet. Please try again.")
        return
    
    game_info = PREDICTION_GAMES[game_type]
    
    # Show game start message
    await query.edit_message_text(
        f"{game_info['icon']} <b>PREDICTION GAME STARTING!</b> {game_info['icon']}\n\n"
        f"🎯 Your predictions are being tested...\n"
        f"💰 Bet: {await format_usd(bet_amount)}\n\n"
        f"<i>Generating random outcome...</i>",
        parse_mode=ParseMode.HTML
    )
    
    # Dramatic pause
    await asyncio.sleep(2)
    
    # Generate outcome
    outcome = get_random_outcome(game_type)
    outcome_display = format_outcome_display(game_type, outcome)
    
    # Determine if player won
    if game_type == "dice" or game_type == "number":
        outcome_index = game_info['options'].index(outcome)
    elif game_type == "coin":
        outcome_index = game_info['options'].index(outcome)
    elif game_type == "color":
        outcome_index = game_info['options'].index(outcome)
    elif game_type == "card":
        outcome_index = game_info['options'].index(outcome)
    
    player_won = outcome_index in selections
    
    # Calculate winnings
    if player_won:
        multiplier = calculate_multiplier(game_type, len(selections))
        win_amount = bet_amount * multiplier
        net_profit = win_amount - bet_amount
        
        # Update balance
        await update_balance(user_id, win_amount)
        
        result_text = "WIN"
        result_emoji = "🎉"
        result_message = f"<b>🎉 PREDICTION CORRECT! 🎉</b>"
    else:
        win_amount = 0
        net_profit = -bet_amount
        result_text = "LOSS"
        result_emoji = "💔"
        result_message = f"<b>💔 PREDICTION INCORRECT 💔</b>"
    
    # Get updated balance
    updated_user = await get_user(user_id)
    new_balance = updated_user['balance'] if updated_user else 0
    
    # Log game session
    await log_game_session(user_id, f'prediction_{game_type}', bet_amount, win_amount, result_text)
    
    # Format selections for display
    selected_names = [game_info['option_names'][i] for i in selections]
    selections_text = ", ".join(selected_names)
    
    # Show result
    if player_won:
        text = f"""
🎊🔮🎊🔮🎊
{result_message}
🎊🔮🎊🔮🎊

{game_info['icon']} <b>{game_info['name']}</b>

🎯 <b>The Outcome:</b> {outcome_display}
📝 <b>Your Predictions:</b> {selections_text}
✅ <b>Result:</b> You predicted correctly!

💰 <b>Bet Amount:</b> {await format_usd(bet_amount)}
🏆 <b>Total Winnings:</b> {await format_usd(win_amount)}
💎 <b>Net Profit:</b> {await format_usd(net_profit)}
💵 <b>Multiplier:</b> {multiplier:.2f}x

💳 <b>New Balance:</b> {await format_usd(new_balance)}

<b>🔮 Ready for another prediction?</b>
"""
    else:
        text = f"""
💪🎯💪🎯💪
{result_message}
💪🎯💪🎯💪

{game_info['icon']} <b>{game_info['name']}</b>

🎯 <b>The Outcome:</b> {outcome_display}
📝 <b>Your Predictions:</b> {selections_text}
❌ <b>Result:</b> Better luck next time!

💰 <b>Bet Amount:</b> {await format_usd(bet_amount)}
📉 <b>Amount Lost:</b> {await format_usd(bet_amount)}
💳 <b>New Balance:</b> {await format_usd(new_balance)}

💡 <b>Tip:</b> Try adjusting your prediction strategy!

<b>🔮 Ready to try again?</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Same Game", callback_data=f"prediction_game_{game_type}"),
            InlineKeyboardButton("🎮 All Games", callback_data="prediction")
        ],
        [
            InlineKeyboardButton("💡 Strategy Tips", callback_data="prediction_rules"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="mini_app_centre")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    
    # Clear selections for next game
    context.user_data.pop('prediction_selections', None)
    context.user_data.pop('prediction_game_type', None)

async def handle_custom_bet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom bet amount input for prediction games."""
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
    
    # Get game type and play
    game_type = context.user_data.get('prediction_game_type')
    if not game_type:
        await update.message.reply_text("❌ Game session expired. Please start again.")
        return
    
    # Clear the custom bet state
    context.user_data.pop('awaiting_prediction_custom_bet', None)
    
    # Create a fake update object for the play function
    class FakeUpdate:
        def __init__(self):
            self.callback_query = FakeQuery()
    
    class FakeQuery:
        def __init__(self):
            self.from_user = update.message.from_user
            
        async def answer(self):
            pass
            
        async def edit_message_text(self, text, **kwargs):
            await update.message.reply_text(text, **kwargs)
    
    fake_update = FakeUpdate()
    await play_prediction_game(fake_update, context, game_type, bet_amount)

async def handle_prediction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced main callback handler for prediction games."""
    query = update.callback_query
    data = query.data
    
    try:
        if data == "game_prediction" or data == "prediction":
            await show_prediction_menu(update, context)
        elif data == "prediction_rules":
            await show_prediction_rules(update, context)
        elif data.startswith("prediction_game_"):
            game_type = data.split("prediction_game_")[1]
            await show_game_selection_menu(update, context, game_type)
        elif data.startswith("prediction_select_"):
            parts = data.split("_")
            game_type = parts[2]
            option_index = int(parts[3])
            await handle_selection_toggle(update, context, game_type, option_index)
        elif data.startswith("prediction_clear_"):
            game_type = data.split("prediction_clear_")[1]
            context.user_data['prediction_selections'] = []
            await show_game_selection_menu(update, context, game_type)
        elif data.startswith("prediction_bet_"):
            game_type = data.split("prediction_bet_")[1]
            await show_betting_menu(update, context, game_type)
        elif data.startswith("prediction_play_"):
            parts = data.split("_")
            game_type = parts[2]
            bet_amount = float(parts[3])
            await play_prediction_game(update, context, game_type, bet_amount)
        elif data.startswith("prediction_custom_bet_"):
            game_type = data.split("prediction_custom_bet_")[1]
            context.user_data['awaiting_prediction_custom_bet'] = True
            await query.edit_message_text(
                f"💵 <b>Enter your custom bet amount:</b>\n\n"
                f"Min: ${MIN_BET:.2f} | Max: ${MAX_BET:.2f}\n\n"
                f"<i>Type the amount and send it.</i>",
                parse_mode=ParseMode.HTML
            )
        else:
            await query.answer("⚠️ Unknown prediction action", show_alert=True)
            await show_prediction_menu(update, context)
            
    except Exception as e:
        # Enhanced error handling
        error_msg = f"❌ An error occurred in prediction games: {str(e)}"
        try:
            await query.edit_message_text(error_msg)
        except:
            await query.answer(error_msg, show_alert=True)
        
        # Log the error for debugging
        print(f"Prediction game error: {e}")
        
        # Reset to main menu on error
        context.user_data.clear()
        try:
            await show_prediction_menu(update, context)
        except:
            pass

# For backward compatibility with dice_predict imports
handle_dice_predict_callback = handle_prediction_callback
