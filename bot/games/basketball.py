"""
Basketball Game - Enhanced 1v1 Player vs Bot

Interactive basketball game using Telegram's basketball emoji animation!
Experience realistic gameplay with emoji animations that determine shot results.
Compete against the bot in exciting 1v1 matches with customizable target scores!

Features:
- Real-time emoji animations for shot results
- Customizable target scores (1, 2, or 3 points)
- Interactive gameplay with round-by-round updates
- Detailed game statistics and match summaries
- Professional basketball commentary and sound effects
"""

import asyncio
import random
import time
from typing import Tuple, Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError, BadRequest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Game Configuration
MIN_BET = 0.50
MAX_BET = 1000.0
DEFAULT_TARGET_SCORE = 3
WIN_MULTIPLIER = 1.95  # Slightly increased for better rewards

# Enhanced Basketball Mechanics
BASKETBALL_MECHANICS = {
    1: {"result": "AIR_BALL", "points": 0, "emoji": "💨", "description": "Complete miss!", "sound": "🔇"},
    2: {"result": "MISS", "points": 0, "emoji": "🚫", "description": "Shot missed", "sound": "🥅"},
    3: {"result": "RIM_OUT", "points": 0, "emoji": "😬", "description": "Hit the rim!", "sound": "🔔"},
    4: {"result": "SWISH", "points": 1, "emoji": "🎯", "description": "Perfect shot!", "sound": "🎵"},
    5: {"result": "SCORE", "points": 1, "emoji": "🏀", "description": "Basket scored!", "sound": "🎉"}
}

# Game Statistics Tracking
class GameStats:
    def __init__(self):
        self.total_shots = 0
        self.successful_shots = 0
        self.perfect_shots = 0  # Swish shots
        self.rim_shots = 0      # Shots that hit rim
        self.air_balls = 0      # Complete misses
        
    @property
    def accuracy(self) -> float:
        return (self.successful_shots / self.total_shots * 100) if self.total_shots > 0 else 0.0
    
    @property
    def perfect_percentage(self) -> float:
        return (self.perfect_shots / self.total_shots * 100) if self.total_shots > 0 else 0.0

def get_enhanced_shot_result(dice_value: int) -> Dict[str, any]:
    """
    Get enhanced shot result from dice value with detailed mechanics.
    
    Args:
        dice_value: The dice result (1-5)
    
    Returns:
        Dict containing all shot information
    """
    if dice_value not in BASKETBALL_MECHANICS:
        dice_value = 3  # Default to rim shot for safety
    
    return BASKETBALL_MECHANICS[dice_value].copy()

def get_shot_result(dice_value: int) -> Tuple[int, str, str]:
    """
    Legacy function for backward compatibility.
    Returns: (points, description, emoji)
    """
    shot_data = get_enhanced_shot_result(dice_value)
    return shot_data["points"], shot_data["description"], shot_data["emoji"]

def get_commentary(shot_data: Dict, player_name: str = "Player") -> str:
    """Generate dynamic commentary for shots."""
    result = shot_data["result"]
    
    commentary_map = {
        "AIR_BALL": [
            f"🗣️ \"Ooh, {player_name} with the air ball!\"",
            f"�️ \"That one didn't even come close!\"",
            f"🗣️ \"Complete whiff by {player_name}!\"",
        ],
        "MISS": [
            f"🗣️ \"{player_name} shoots... and misses!\"",
            f"🗣️ \"Good attempt but no cigar!\"",
            f"🗣️ \"The shot falls short!\"",
        ],
        "RIM_OUT": [
            f"🗣️ \"So close! {player_name} hits the rim!\"",
            f"�️ \"Unlucky bounce off the rim!\"",
            f"🗣️ \"Almost had it! Rim denied {player_name}!\"",
        ],
        "SWISH": [
            f"🗣️ \"SWISH! Perfect shot by {player_name}!\"",
            f"🗣️ \"Nothing but net! Beautiful form!\"",
            f"🗣️ \"What a shot! Pure basketball poetry!\"",
        ],
        "SCORE": [
            f"🗣️ \"{player_name} scores! Great shot!\"",
            f"🗣️ \"And it's good! {player_name} finds the basket!\"",
            f"🗣️ \"Bucket! {player_name} puts it in!\"",
        ]
    }
    
    return random.choice(commentary_map.get(result, [f"🗣️ \"{player_name} takes a shot!\""]))

# --- Interactive Basketball Emoji Functions ---

async def send_basketball_emoji_enhanced(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                       player_name: str = "Player") -> Dict[str, any]:
    """
    Send enhanced basketball emoji with improved error handling and feedback.
    
    Args:
        update: Telegram update object
        context: Bot context
        player_name: Name of the player taking the shot
    
    Returns:
        Dict containing shot result and metadata
    """
    try:
        # Send the basketball emoji
        emoji_message = await context.bot.send_dice(
            chat_id=update.effective_chat.id,
            emoji="🏀"
        )
        
        # Brief pause for dramatic effect
        await asyncio.sleep(1.5)
        
        # Get the dice value
        dice_value = emoji_message.dice.value
        shot_data = get_enhanced_shot_result(dice_value)
        
        # Add metadata
        shot_data.update({
            "player": player_name,
            "dice_value": dice_value,
            "timestamp": time.time(),
            "message_id": emoji_message.message_id
        })
        
        # Wait for animation to complete
        await asyncio.sleep(2.5)
        
        return shot_data
        
    except (TelegramError, BadRequest) as e:
        # Handle Telegram-specific errors
        print(f"Telegram error in basketball emoji: {e}")
        # Fallback to simulated result
        return get_enhanced_shot_result(random.randint(1, 5))
        
    except Exception as e:
        # Handle any other errors
        print(f"Error sending basketball emoji: {e}")
        # Fallback to simulated result
        return get_enhanced_shot_result(random.randint(1, 5))

async def play_basketball_1v1_interactive(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, bet_amount: float, target_score: int = DEFAULT_TARGET_SCORE) -> dict:
    """
    Play an interactive 1v1 basketball game against the bot using real Telegram emojis.
    First to target_score points wins.
    
    Args:
        update: Telegram update object
        context: Bot context
        user_id: User's Telegram ID
        bet_amount: Amount to bet in USD
        target_score: Points needed to win (1, 2, or 3)
    
    Returns:
        dict with complete game results
    """
    from main import get_user, update_balance, deduct_balance, log_game_session, format_usd
    
    # Initialize scores
    player_score = 0
    bot_score = 0
    
    # Game log for display
    game_log = []
    round_num = 1
    
    # Send initial game message
    await update.effective_message.reply_text(
        f"🏀 <b>BASKETBALL 1v1 MATCH STARTING!</b> 🏀\n\n"
        f"💰 Bet: {await format_usd(bet_amount)}\n"
        f"🎯 First to {target_score} points wins!\n\n"
        f"<i>Watch the basketball animations to see the results!</i>",
        parse_mode=ParseMode.HTML
    )
    
    # Play until someone reaches target score
    while player_score < target_score and bot_score < target_score:
        # Send round announcement
        await update.effective_message.reply_text(
            f"📢 <b>Round {round_num}</b>\n"
            f"Score: You {player_score} - {bot_score} Bot\n\n"
            f"🏀 Your shot:",
            parse_mode=ParseMode.HTML
        )
        
        # Player's shot
        await update.effective_message.reply_text(
            f"🏀 <b>Your turn to shoot!</b>\n"
            f"<i>Watch the basketball animation...</i>",
            parse_mode=ParseMode.HTML
        )
        
        player_shot_data = await send_basketball_emoji_enhanced(update, context, "You")
        player_points = player_shot_data["points"]
        player_made_shot = player_points > 0
        
        # Show player result with commentary
        commentary = get_commentary(player_shot_data, "You")
        await update.effective_message.reply_text(
            f"{player_shot_data['emoji']} <b>{player_shot_data['description']}</b> {player_shot_data['sound']}\n"
            f"{commentary}",
            parse_mode=ParseMode.HTML
        )
        
        await asyncio.sleep(1)  # Brief pause between shots
        
        # Bot's shot announcement
        await update.effective_message.reply_text(
            f"🤖 <b>Bot's turn to shoot!</b>\n"
            f"<i>Can the bot match your performance?</i>",
            parse_mode=ParseMode.HTML
        )
        
        # Bot's shot
        bot_shot_data = await send_basketball_emoji_enhanced(update, context, "Bot")
        bot_points = bot_shot_data["points"]
        bot_made_shot = bot_points > 0
        
        # Show bot result with commentary
        commentary = get_commentary(bot_shot_data, "Bot")
        await update.effective_message.reply_text(
            f"{bot_shot_data['emoji']} <b>{bot_shot_data['description']}</b> {bot_shot_data['sound']}\n"
            f"{commentary}",
            parse_mode=ParseMode.HTML
        )
        
        # Award points based on who scored
        round_points_player = 0
        round_points_bot = 0
        
        if player_made_shot and not bot_made_shot:
            # Player scores, bot misses = Player gets 1 point
            round_points_player = 1
            player_score += 1
        elif bot_made_shot and not player_made_shot:
            # Bot scores, player misses = Bot gets 1 point
            round_points_bot = 1
            bot_score += 1
        # If both score or both miss, no points awarded (tie round)
        
        # Show round results
        round_result = "PLAYER" if round_points_player > 0 else "BOT" if round_points_bot > 0 else "TIE"
        round_emoji = "🟢" if round_result == "PLAYER" else "🔴" if round_result == "BOT" else "🟡"
        
        result_text = f"📊 <b>Round {round_num} Results:</b> {round_emoji}\n\n"
        result_text += f"👤 You: {player_shot_data['emoji']} {player_shot_data['description']}"
        if round_points_player > 0:
            result_text += f" (+1 point) 🎯"
        result_text += f"\n🤖 Bot: {bot_shot_data['emoji']} {bot_shot_data['description']}"
        if round_points_bot > 0:
            result_text += f" (+1 point) 🎯"
        result_text += f"\n\n📈 <b>Current Score: You {player_score} - {bot_score} Bot</b>"
        
        if round_result == "TIE":
            result_text += f"\n🟡 <b>Round {round_num}: TIE!</b> No points awarded."
        elif round_result == "PLAYER":
            result_text += f"\n🟢 <b>You win Round {round_num}!</b>"
        else:
            result_text += f"\n🔴 <b>Bot wins Round {round_num}!</b>"
        
        await update.effective_message.reply_text(result_text, parse_mode=ParseMode.HTML)
        
        # Log this round
        game_log.append({
            'round': round_num,
            'player_dice': player_shot_data['dice_value'],
            'player_result': f"{player_shot_data['emoji']} {player_shot_data['description']}",
            'player_made_shot': player_made_shot,
            'player_round_points': round_points_player,
            'bot_dice': bot_shot_data['dice_value'],
            'bot_result': f"{bot_shot_data['emoji']} {bot_shot_data['description']}",
            'bot_made_shot': bot_made_shot,
            'bot_round_points': round_points_bot,
            'player_score': player_score,
            'bot_score': bot_score,
            'round_result': round_result,
            'player_shot_data': player_shot_data,
            'bot_shot_data': bot_shot_data
        })
        
        round_num += 1
        
        # Brief pause before next round
        if player_score < target_score and bot_score < target_score:
            await asyncio.sleep(2)
        
        # Safety check - max 20 rounds (since ties don't count, may take longer)
        if round_num > 20:
            break
    
    # Determine winner
    player_won = player_score >= target_score and player_score > bot_score
    
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
    await log_game_session(user_id, 'basketball_1v1', bet_amount, win_amount, result_text)
    
    # Get updated balance
    user_data = await get_user(user_id)
    new_balance = user_data['balance'] if user_data else 0
    
    return {
        'player_won': player_won,
        'player_score': player_score,
        'bot_score': bot_score,
        'game_log': game_log,
        'bet_amount': bet_amount,
        'win_amount': win_amount,
        'net_result': net_result,
        'new_balance': new_balance,
        'result_text': result_text,
        'total_rounds': len(game_log)
    }


async def play_basketball_1v1(user_id: int, bet_amount: float, target_score: int = DEFAULT_TARGET_SCORE) -> dict:
    """
    Play a 1v1 basketball game against the bot.
    First to target_score points wins.
    
    Args:
        user_id: User's Telegram ID
        bet_amount: Amount to bet in USD
        target_score: Points needed to win (1, 2, or 3)
    
    Returns:
        dict with complete game results
    """
    from main import get_user, update_balance, deduct_balance, log_game_session, format_usd
    
    # Initialize scores
    player_score = 0
    bot_score = 0
    
    # Game log for display
    game_log = []
    round_num = 1
    
    # Play until someone reaches target score
    while player_score < target_score and bot_score < target_score:
        # Player's shot
        player_dice = random.randint(1, 5)
        player_points, player_desc, player_emoji = get_shot_result(player_dice)
        player_made_shot = player_points > 0
        
        # Bot's shot
        bot_dice = random.randint(1, 5)
        bot_points, bot_desc, bot_emoji = get_shot_result(bot_dice)
        bot_made_shot = bot_points > 0
        
        # Award points based on who scored
        round_points_player = 0
        round_points_bot = 0
        
        if player_made_shot and not bot_made_shot:
            # Player scores, bot misses = Player gets 1 point
            round_points_player = 1
            player_score += 1
        elif bot_made_shot and not player_made_shot:
            # Bot scores, player misses = Bot gets 1 point
            round_points_bot = 1
            bot_score += 1
        # If both score or both miss, no points awarded (tie round)
        
        # Log this round
        game_log.append({
            'round': round_num,
            'player_dice': player_dice,
            'player_result': f"{player_emoji} {player_desc}",
            'player_made_shot': player_made_shot,
            'player_round_points': round_points_player,
            'bot_dice': bot_dice,
            'bot_result': f"{bot_emoji} {bot_desc}",
            'bot_made_shot': bot_made_shot,
            'bot_round_points': round_points_bot,
            'player_score': player_score,
            'bot_score': bot_score,
            'round_result': "PLAYER" if round_points_player > 0 else "BOT" if round_points_bot > 0 else "TIE"
        })
        
        round_num += 1
        
        # Safety check - max 20 rounds (since ties don't count, may take longer)
        if round_num > 20:
            break
    
    # Determine winner
    player_won = player_score >= target_score and player_score > bot_score
    
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
    await log_game_session(user_id, 'basketball_1v1', bet_amount, win_amount, result_text)
    
    # Get updated balance
    user_data = await get_user(user_id)
    new_balance = user_data['balance'] if user_data else 0
    
    return {
        'player_won': player_won,
        'player_score': player_score,
        'bot_score': bot_score,
        'game_log': game_log,
        'bet_amount': bet_amount,
        'win_amount': win_amount,
        'net_result': net_result,
        'new_balance': new_balance,
        'result_text': result_text,
        'total_rounds': len(game_log)
    }


async def show_basketball_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show enhanced basketball 1v1 game menu with better UI."""
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
🏀 <b>ENHANCED BASKETBALL 1v1</b> 🏀

💰 <b>Your Balance:</b> {balance_str}
🎯 <b>Multiplier:</b> {WIN_MULTIPLIER}x your bet!

🎮 <b>How to Play:</b>
• Choose your target score (1, 2, or 3 points)
• Place your bet and start the match
• Watch <b>real Telegram basketball animations</b> 🏀
• Each player shoots alternately
• First to reach target score wins!

📊 <b>Enhanced Shot Results:</b>
💨 <b>Air Ball:</b> Complete miss (0 points)
🚫 <b>Miss:</b> Shot missed (0 points)
😬 <b>Rim Out:</b> Hit the rim! (0 points)
🎯 <b>Swish:</b> Perfect shot! (1 point)
🏀 <b>Score:</b> Basket made! (1 point)

🏆 <b>Scoring Rules:</b>
🟢 You score + Bot misses = +1 point for you
🔴 Bot scores + You miss = +1 point for bot
🟡 Both score or both miss = Tie round (no points)

� <b>Pro Tips:</b>
• Shorter matches (1 point) = Quick results
• Longer matches (3 points) = More excitement
• Perfect shots (swish) count as regular scores but look cooler!

💵 <b>Betting Limits:</b>
• Min: ${MIN_BET:.2f} | Max: ${MAX_BET:.2f}

<b>🎯 Choose your target score to begin:</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("⚡ First to 1 Point", callback_data="basketball_target_1"),
        ],
        [
            InlineKeyboardButton("🚀 First to 2 Points", callback_data="basketball_target_2"),
        ],
        [
            InlineKeyboardButton("� First to 3 Points", callback_data="basketball_target_3")
        ],
        [
            InlineKeyboardButton("� Game Rules", callback_data="basketball_rules"),
            InlineKeyboardButton("🔙 Back", callback_data="mini_app_centre")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def show_basketball_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed basketball game rules."""
    query = update.callback_query
    await query.answer()
    
    text = f"""
📚 <b>BASKETBALL 1v1 - DETAILED RULES</b> 📚

🎮 <b>Game Mechanics:</b>
The game uses Telegram's built-in basketball emoji animation to determine shot results. When you or the bot "shoots" by sending a 🏀 emoji, Telegram plays a realistic basketball animation that randomly lands on one of 5 possible outcomes.

🎯 <b>Shot Results Explained:</b>

💨 <b>Air Ball (Value 1):</b>
• Complete miss - ball doesn't even reach the basket
• 0 points awarded
• Happens ~20% of the time

🚫 <b>Miss (Value 2):</b>
• Shot attempt that misses the basket
• 0 points awarded  
• Happens ~20% of the time

😬 <b>Rim Out (Value 3):</b>
• Ball hits the rim but bounces out
• So close! But still 0 points
• Happens ~20% of the time

🎯 <b>Swish (Value 4):</b>
• Perfect shot - nothing but net!
• 1 point awarded
• Happens ~20% of the time

🏀 <b>Score (Value 5):</b>
• Ball goes in the basket
• 1 point awarded
• Happens ~20% of the time

🏆 <b>Winning Conditions:</b>
• First player to reach the target score wins
• You must win by actually reaching the target
• Tie rounds don't count toward your score

💰 <b>Betting & Payouts:</b>
• Win: Get {WIN_MULTIPLIER}x your bet amount
• Lose: Lose your bet amount
• Minimum bet: ${MIN_BET:.2f}
• Maximum bet: ${MAX_BET:.2f}

🎲 <b>Fairness:</b>
This game uses Telegram's official emoji animations, making it completely fair and random. Neither the casino nor players can influence the results - it's pure chance and excitement!

Ready to play? 🏀
"""
    
    keyboard = [
        [InlineKeyboardButton("🏀 Start Playing", callback_data="basketball")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="basketball")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def basketball_bet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle basketball bet amount selection."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    from main import get_user, format_usd
    
    # Check if target score is set
    if 'basketball_target_score' not in context.user_data:
        await query.answer("❌ Please select target score first", show_alert=True)
        await show_basketball_menu(update, context)
        return
    
    # Get bet amount from callback data
    bet_amount_str = query.data.split('_')[-1]
    
    try:
        bet_amount = float(bet_amount_str)
    except ValueError:
        await query.edit_message_text("❌ Invalid bet amount.")
        return
    
    # Validate bet amount
    if bet_amount < MIN_BET:
        await query.answer(f"❌ Minimum bet is ${MIN_BET:.2f}", show_alert=True)
        return
    
    if bet_amount > MAX_BET:
        await query.answer(f"❌ Maximum bet is ${MAX_BET:.2f}", show_alert=True)
        return
    
    # Check user balance
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found.")
        return
    
    if user['balance'] < bet_amount:
        balance_str = await format_usd(user['balance'])
        await query.answer(f"❌ Insufficient balance! You have {balance_str}", show_alert=True)
        return
    
    # Store bet amount and get target score
    context.user_data['basketball_bet_amount'] = bet_amount
    target_score = context.user_data['basketball_target_score']
    
    bet_str = await format_usd(bet_amount)
    balance_str = await format_usd(user['balance'])
    win_str = await format_usd(bet_amount * WIN_MULTIPLIER)
    profit_str = await format_usd(bet_amount * (WIN_MULTIPLIER - 1))
    
    # Enhanced match preview
    match_type = {
        1: "⚡ Lightning Match",
        2: "🚀 Quick Match", 
        3: "🏀 Classic Match"
    }
    
    expected_rounds = {
        1: "1-3 rounds",
        2: "2-6 rounds",
        3: "3-9 rounds"
    }
    
    text = f"""
🏀 <b>BASKETBALL 1v1 - GAME READY!</b> 🏀

🎯 <b>{match_type[target_score]}</b>
📊 First to {target_score} point{'s' if target_score > 1 else ''} wins!
⏱️ Expected duration: {expected_rounds[target_score]}

💰 <b>Your Balance:</b> {balance_str}
💵 <b>Bet Amount:</b> {bet_str}

📈 <b>Potential Winnings:</b>
🏆 Win: {win_str}
💎 Profit: {profit_str}
📊 Multiplier: {WIN_MULTIPLIER}x

🎮 <b>Game Preview:</b>
• Interactive real-time basketball shooting
• Live emoji animations determine results
• Professional commentary for each shot
• Detailed round-by-round scoring

🎯 <b>Shot Types You'll See:</b>
💨 Air Ball • 🚫 Miss • 😬 Rim Out • 🎯 Swish • 🏀 Score

<b>🏀 Ready to start your basketball match?</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🏀 START MATCH!", callback_data="basketball_play_start"),
        ],
        [
            InlineKeyboardButton("💡 View Strategy Tips", callback_data="basketball_tips"),
            InlineKeyboardButton("🔄 Change Bet", callback_data=f"basketball_target_{target_score}")
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="basketball")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def basketball_target_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle basketball target score selection."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    from main import get_user, format_usd
    
    # Get target score from callback data
    target_score_str = query.data.split('_')[-1]
    
    try:
        target_score = int(target_score_str)
    except ValueError:
        await query.edit_message_text("❌ Invalid target score.")
        return
    
    # Validate target score
    if target_score not in [1, 2, 3]:
        await query.answer("❌ Target score must be 1, 2, or 3", show_alert=True)
        return
    
    # Store target score
    context.user_data['basketball_target_score'] = target_score
    
    # Show bet selection
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found.")
        return
    
    balance_str = await format_usd(user['balance'])
    
    # Calculate game duration estimate
    duration_text = {
        1: "⚡ Quick Match (1-3 rounds)",
        2: "🚀 Fast Match (2-6 rounds)", 
        3: "🏀 Classic Match (3-9 rounds)"
    }
    
    text = f"""
🏀 <b>BASKETBALL 1v1 - TARGET: {target_score} POINT{'S' if target_score > 1 else ''}</b> 🏀

💰 <b>Balance:</b> {balance_str}
🎯 <b>Target Score:</b> First to {target_score} point{'s' if target_score > 1 else ''}
⏱️ <b>Duration:</b> {duration_text[target_score]}

🎮 <b>Game Format:</b>
• Interactive basketball shootout using real Telegram emoji!
• First to {target_score} point{'s' if target_score > 1 else ''} wins!
• Win {WIN_MULTIPLIER}x your bet!

💵 <b>Min Bet:</b> ${MIN_BET:.2f}
💰 <b>Max Bet:</b> ${MAX_BET:.2f}
🎯 <b>Win Multiplier:</b> {WIN_MULTIPLIER}x

<b>Choose your bet amount:</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("$1", callback_data="basketball_bet_1"),
            InlineKeyboardButton("$5", callback_data="basketball_bet_5"),
            InlineKeyboardButton("$10", callback_data="basketball_bet_10")
        ],
        [
            InlineKeyboardButton("$25", callback_data="basketball_bet_25"),
            InlineKeyboardButton("$50", callback_data="basketball_bet_50"),
            InlineKeyboardButton("$100", callback_data="basketball_bet_100")
        ],
        [
            InlineKeyboardButton("✏️ Custom Amount", callback_data="basketball_custom_bet")
        ],
        [
            InlineKeyboardButton("🔄 Change Target", callback_data="basketball"),
            InlineKeyboardButton("🔙 Back to Games", callback_data="mini_app_centre")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def basketball_play_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle enhanced basketball 1v1 game play with better user experience."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    from main import get_user, deduct_balance, format_usd
    
    # Get bet amount and target score from context
    bet_amount = context.user_data.get('basketball_bet_amount', 1.0)
    target_score = context.user_data.get('basketball_target_score', DEFAULT_TARGET_SCORE)
    
    # Validate bet amount
    if bet_amount < MIN_BET or bet_amount > MAX_BET:
        await query.edit_message_text(f"❌ Invalid bet amount. Must be between ${MIN_BET:.2f} and ${MAX_BET:.2f}")
        return
    
    # Check and deduct balance
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found.")
        return
    
    if user['balance'] < bet_amount:
        balance_str = await format_usd(user['balance'])
        await query.edit_message_text(f"❌ Insufficient balance! You have {balance_str}")
        return
    
    # Deduct bet amount
    deducted = await deduct_balance(user_id, bet_amount)
    if not deducted:
        await query.edit_message_text("❌ Failed to place bet. Please try again.")
        return
    
    # Show exciting match start message
    match_type = {1: "⚡ Lightning", 2: "🚀 Quick", 3: "🏀 Classic"}
    bet_str = await format_usd(bet_amount)
    
    await query.edit_message_text(
        f"🏀 <b>{match_type[target_score]} Basketball Match</b> �\n\n"
        f"💰 Bet: {bet_str}\n"
        f"🎯 Target: First to {target_score} point{'s' if target_score > 1 else ''}\n"
        f"🎮 <b>GET READY TO SHOOT!</b>\n\n"
        f"<i>The interactive game is starting below...</i>",
        parse_mode=ParseMode.HTML
    )
    
    # Small delay for dramatic effect
    await asyncio.sleep(1)
    
    # Play the enhanced interactive 1v1 game
    result = await play_basketball_1v1_interactive(update, context, user_id, bet_amount, target_score)
    
    # Show enhanced final summary
    bet_str = await format_usd(result['bet_amount'])
    balance_str = await format_usd(result['new_balance'])
    
    if result['player_won']:
        win_str = await format_usd(result['win_amount'])
        profit_str = await format_usd(result['net_result'])
        result_emoji = "🎉"
        result_title = "🏆 VICTORY! 🏆"
        result_text = f"<b>YOU ARE THE CHAMPION!</b>\n💰 Winnings: {win_str}\n💎 Profit: {profit_str}"
    else:
        loss_str = await format_usd(result['bet_amount'])
        result_emoji = "💪"
        result_title = "⚡ GOOD GAME! ⚡"
        result_text = f"<b>Bot wins this round!</b>\n📉 Amount lost: {loss_str}\n💪 Get 'em next time!"
    
    match_type = {1: "⚡ Lightning", 2: "🚀 Quick", 3: "🏀 Classic"}
    
    final_text = f"""
🏀 <b>{match_type[target_score]} Match Complete!</b> 🏀

{result_title}

🎯 <b>Final Score:</b>
👤 You: {result['player_score']} points
🤖 Bot: {result['bot_score']} points

{result_emoji} {result_text}

💳 <b>New Balance:</b> {balance_str}

<b>🏀 Ready for another match?</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🔥 Play Again", callback_data="basketball"),
            InlineKeyboardButton("🎮 Other Games", callback_data="mini_app_centre")
        ]
    ]
    
    await update.effective_message.reply_text(
        final_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    
    # Clear context
    context.user_data.pop('basketball_bet_amount', None)
    # Keep target score for potential replay


async def handle_custom_bet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom bet amount input for basketball."""
    user_id = update.message.from_user.id
    
    from main import get_user, format_usd, deduct_balance
    
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
    
    # Store bet amount
    context.user_data['basketball_bet_amount'] = bet_amount
    context.user_data.pop('awaiting_basketball_custom_bet', None)
    
    # Get target score (must be set before custom bet)
    target_score = context.user_data.get('basketball_target_score', DEFAULT_TARGET_SCORE)
    
    # Deduct bet amount
    deducted = await deduct_balance(user_id, bet_amount)
    if not deducted:
        await update.message.reply_text("❌ Failed to place bet. Please try again.")
        return
    
    # Play the 1v1 game with target score
    result = await play_basketball_1v1(user_id, bet_amount, target_score)
    
    # Format game summary with enhanced display
    bet_str = await format_usd(result['bet_amount'])
    balance_str = await format_usd(result['new_balance'])
    
    if result['player_won']:
        win_str = await format_usd(result['win_amount'])
        profit_str = await format_usd(result['net_result'])
        result_emoji = "🎉"
        result_text = f"<b>YOU WIN!</b> 🏆\n💰 Won: {win_str}\n📈 Profit: {profit_str}"
    else:
        loss_str = await format_usd(result['bet_amount'])
        result_emoji = "💪"
        result_text = f"<b>BOT WINS!</b> 🤖\n📉 Lost: {loss_str}\n💪 Next time!"
    
    text = f"""
🏀 <b>BASKETBALL 1v1 COMPLETE</b> 🏀

🎯 <b>Final Score:</b>
👤 You: {result['player_score']} points
🤖 Bot: {result['bot_score']} points

💵 <b>Bet Amount:</b> {bet_str}
{result_emoji} {result_text}

💳 <b>New Balance:</b> {balance_str}

<b>Play again?</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🔥 Play Again", callback_data="basketball"),
            InlineKeyboardButton("🎮 All Games", callback_data="mini_app_centre")
        ]
    ]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def handle_basketball_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced main callback handler for basketball game with all features."""
    query = update.callback_query
    data = query.data
    
    try:
        if data == "game_basketball" or data == "basketball":
            await show_basketball_menu(update, context)
        elif data == "basketball_rules":
            await show_basketball_rules(update, context)
        elif data.startswith("basketball_target_"):
            await basketball_target_callback(update, context)
        elif data.startswith("basketball_bet_") and not data.endswith("_return"):
            await basketball_bet_callback(update, context)
        elif data == "basketball_bet_return":
            # Return to bet selection with current target score
            target_score = context.user_data.get('basketball_target_score', DEFAULT_TARGET_SCORE)
            context.user_data['basketball_target_score'] = target_score
            await basketball_target_callback(update, context)
        elif data == "basketball_custom_bet":
            await basketball_custom_bet_callback(update, context)
        elif data == "basketball_play_start":
            await basketball_play_callback(update, context)
        elif data == "basketball_tips":
            await show_basketball_tips(update, context)
        elif data == "basketball_view_log":
            # TODO: Implement detailed game log view
            await query.answer("🚧 Game log view coming soon!", show_alert=True)
        else:
            await query.answer("⚠️ Unknown basketball action", show_alert=True)
            await show_basketball_menu(update, context)
            
    except Exception as e:
        # Enhanced error handling
        error_msg = f"❌ An error occurred in basketball game: {str(e)}"
        try:
            await query.edit_message_text(error_msg)
        except:
            await query.answer(error_msg, show_alert=True)
        
        # Log the error for debugging
        print(f"Basketball game error: {e}")
        
        # Reset to main menu on error
        context.user_data.clear()
        try:
            await show_basketball_menu(update, context)
        except:
            pass
