"""
Game handlers for casino games
"""

import random
import logging
from typing import List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..services.database import db_service

logger = logging.getLogger(__name__)

class GameHandlers:
    """Handlers for casino games"""
    
    async def slots_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show slots game betting interface"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user = await db_service.get_user(user_id)
        
        if not user:
            await query.edit_message_text("❌ User not found. Please restart with /start")
            return
        
        balance_str = f"${user['balance']:.2f}"
        
        text = f"""
🎰 <b>SLOTS</b>

💰 Balance: {balance_str}

<b>Payouts:</b>
🍒🍒🍒 10x • 🍋🍋🍋 20x • 🍊🍊🍊 30x
🔔🔔🔔 50x • 💎💎💎 100x

Choose bet:
"""
        
        keyboard = [
            [
                InlineKeyboardButton("$1", callback_data="slots_bet_1"),
                InlineKeyboardButton("$5", callback_data="slots_bet_5"),
                InlineKeyboardButton("$10", callback_data="slots_bet_10")
            ],
            [
                InlineKeyboardButton("$25", callback_data="slots_bet_25"),
                InlineKeyboardButton("$50", callback_data="slots_bet_50"),
                InlineKeyboardButton("$100", callback_data="slots_bet_100")
            ],
            [InlineKeyboardButton("🔙 Back to Games", callback_data="mini_app_centre")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def blackjack_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show blackjack game betting interface"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user = await db_service.get_user(user_id)
        
        if not user:
            await query.edit_message_text("❌ User not found. Please restart with /start")
            return
        
        balance_str = f"${user['balance']:.2f}"
        
        text = f"""
🃏 <b>BLACKJACK</b>

💰 Balance: {balance_str}

<b>Rules:</b>
Get to 21 • Beat dealer • Blackjack pays 3:2

<b>Card Values:</b>
Numbers = face • Face cards = 10 • Ace = 1 or 11

Choose bet:
"""
        
        keyboard = [
            [
                InlineKeyboardButton("$1", callback_data="blackjack_bet_1"),
                InlineKeyboardButton("$5", callback_data="blackjack_bet_5"),
                InlineKeyboardButton("$10", callback_data="blackjack_bet_10")
            ],
            [
                InlineKeyboardButton("$25", callback_data="blackjack_bet_25"),
                InlineKeyboardButton("$50", callback_data="blackjack_bet_50"),
                InlineKeyboardButton("$100", callback_data="blackjack_bet_100")
            ],
            [InlineKeyboardButton("🔙 Back to Games", callback_data="mini_app_centre")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def dice_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show dice game betting interface"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user = await db_service.get_user(user_id)
        
        if not user:
            await query.edit_message_text("❌ User not found. Please restart with /start")
            return
        
        balance_str = f"${user['balance']:.2f}"
        
        text = f"""
🎲 <b>DICE</b>

💰 Balance: {balance_str}

<b>Options:</b>
HIGH (8-12) = 2x • LOW (2-7) = 2x • Lucky 7 = 5x

Choose bet:
"""
        
        keyboard = [
            [
                InlineKeyboardButton("$1", callback_data="dice_bet_1"),
                InlineKeyboardButton("$5", callback_data="dice_bet_5"),
                InlineKeyboardButton("$10", callback_data="dice_bet_10")
            ],
            [
                InlineKeyboardButton("$25", callback_data="dice_bet_25"),
                InlineKeyboardButton("$50", callback_data="dice_bet_50"),
                InlineKeyboardButton("$100", callback_data="dice_bet_100")
            ],
            [InlineKeyboardButton("🔙 Back to Games", callback_data="mini_app_centre")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def coinflip_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show coin flip game"""
        query = update.callback_query
        await query.answer()
        
        text = """
🪙 <b>COIN FLIP</b>

<b>Coming Soon!</b>

Classic heads or tails with 2x payout!
"""
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Games", callback_data="mini_app_centre")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    # Game logic methods
    def _generate_slot_reels(self) -> List[str]:
        """Generate three random symbols for slots"""
        symbols = ['🍒', '🍋', '🍊', '🔔', '💎']
        weights = [40, 30, 20, 8, 2]  # Higher weight = more common
        
        # Create weighted symbol list
        weighted_symbols = []
        for symbol, weight in zip(symbols, weights):
            weighted_symbols.extend([symbol] * weight)
        
        return [random.choice(weighted_symbols) for _ in range(3)]
    
    def _calculate_slots_win(self, reels: List[str], bet_amount: float) -> Tuple[float, str]:
        """Calculate slots winnings"""
        payouts = {'🍒': 10, '🍋': 20, '🍊': 30, '🔔': 50, '💎': 100}
        
        # Check for three matching symbols
        if reels[0] == reels[1] == reels[2]:
            symbol = reels[0]
            multiplier = payouts[symbol]
            win_amount = bet_amount * multiplier
            return win_amount, f"JACKPOT! {symbol}{symbol}{symbol} - {multiplier}x multiplier!"
        
        # Check for two matching symbols (small consolation)
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            win_amount = bet_amount * 0.5
            return win_amount, "Two matching symbols - small win!"
        
        return 0.0, "No match - try again!"
    
    def _generate_blackjack_hand(self) -> List[str]:
        """Generate a blackjack hand"""
        cards = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        return [random.choice(cards) for _ in range(2)]
    
    def _calculate_hand_value(self, hand: List[str]) -> int:
        """Calculate blackjack hand value"""
        value = 0
        aces = 0
        
        for card in hand:
            if card in ['J', 'Q', 'K']:
                value += 10
            elif card == 'A':
                aces += 1
                value += 11
            else:
                value += int(card)
        
        # Adjust for aces
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        
        return value
    
    def _roll_dice(self) -> Tuple[int, int]:
        """Roll two dice"""
        return random.randint(1, 6), random.randint(1, 6)
    
    # Game betting handlers
    async def handle_slots_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle slots betting"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        bet_amount = float(query.data.split("_")[-1])
        
        # Check user balance
        user = await db_service.get_user(user_id)
        if not user or user['balance'] < bet_amount:
            await query.edit_message_text(
                "❌ Insufficient balance! Please deposit more funds.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Deposit", callback_data="deposit")]])
            )
            return
        
        # Deduct bet amount
        success = await db_service.update_balance(user_id, -bet_amount, "game_bet")
        if not success:
            await query.edit_message_text("❌ Error processing bet. Please try again.")
            return
        
        # Play the game
        reels = self._generate_slot_reels()
        win_amount, result_text = self._calculate_slots_win(reels, bet_amount)
        
        # Update balance if won
        if win_amount > 0:
            await db_service.update_balance(user_id, win_amount, "game_win")
        
        # Get updated balance
        user = await db_service.get_user(user_id)
        balance_str = f"${user['balance']:.2f}"
        
        # Create result message
        slots_display = f"{reels[0]} | {reels[1]} | {reels[2]}"
        
        if win_amount > 0:
            result_message = f"""
🎰 <b>SLOT RESULT</b>

{slots_display}

{result_text}

💰 Bet: ${bet_amount:.2f}
🏆 Won: ${win_amount:.2f}
📊 Balance: {balance_str}
"""
        else:
            result_message = f"""
🎰 <b>SLOT RESULT</b>

{slots_display}

{result_text}

💰 Bet: ${bet_amount:.2f}
💸 Lost: ${bet_amount:.2f}
📊 Balance: {balance_str}
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🎰 Play Again", callback_data="game_slots"),
                InlineKeyboardButton("🎮 Other Games", callback_data="mini_app_centre")
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        
        await query.edit_message_text(result_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def handle_blackjack_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle blackjack betting"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        bet_amount = float(query.data.split("_")[-1])
        
        # Check user balance
        user = await db_service.get_user(user_id)
        if not user or user['balance'] < bet_amount:
            await query.edit_message_text(
                "❌ Insufficient balance! Please deposit more funds.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Deposit", callback_data="deposit")]])
            )
            return
        
        # Deduct bet amount
        success = await db_service.update_balance(user_id, -bet_amount, "game_bet")
        if not success:
            await query.edit_message_text("❌ Error processing bet. Please try again.")
            return
        
        # Play the game
        player_hand = self._generate_blackjack_hand()
        dealer_hand = self._generate_blackjack_hand()
        
        player_value = self._calculate_hand_value(player_hand)
        dealer_value = self._calculate_hand_value(dealer_hand)
        
        # Simple blackjack logic (auto-play)
        win_amount = 0.0
        result_text = ""
        
        if player_value == 21:
            # Player blackjack
            win_amount = bet_amount * 2.5  # 3:2 payout
            result_text = "BLACKJACK! You got 21!"
        elif player_value > 21:
            # Player bust
            result_text = f"BUST! You went over 21 with {player_value}"
        elif dealer_value > 21:
            # Dealer bust
            win_amount = bet_amount * 2
            result_text = f"DEALER BUST! Dealer went over 21 with {dealer_value}"
        elif player_value > dealer_value:
            # Player wins
            win_amount = bet_amount * 2
            result_text = f"YOU WIN! {player_value} beats {dealer_value}"
        elif player_value == dealer_value:
            # Push (tie)
            win_amount = bet_amount  # Return bet
            result_text = f"PUSH! Both got {player_value}"
        else:
            # Dealer wins
            result_text = f"DEALER WINS! {dealer_value} beats {player_value}"
        
        # Update balance if won
        if win_amount > 0:
            await db_service.update_balance(user_id, win_amount, "game_win")
        
        # Get updated balance
        user = await db_service.get_user(user_id)
        balance_str = f"${user['balance']:.2f}"
        
        # Create result message
        player_cards = " ".join(player_hand)
        dealer_cards = " ".join(dealer_hand)
        
        result_message = f"""
🃏 <b>BLACKJACK</b>

👤 Your: {player_cards} ({player_value})
🤖 Dealer: {dealer_cards} ({dealer_value})

{result_text}

💰 Bet: ${bet_amount:.2f}
🏆 Won: ${win_amount:.2f}
📊 Balance: {balance_str}
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🃏 Play Again", callback_data="game_blackjack"),
                InlineKeyboardButton("🎮 Other Games", callback_data="mini_app_centre")
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        
        await query.edit_message_text(result_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def handle_dice_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle dice betting - show betting options"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        bet_amount = float(query.data.split("_")[-1])
        
        # Check user balance
        user = await db_service.get_user(user_id)
        if not user or user['balance'] < bet_amount:
            await query.edit_message_text(
                "❌ Insufficient balance! Please deposit more funds.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Deposit", callback_data="deposit")]])
            )
            return
        
        balance_str = f"${user['balance']:.2f}"
        
        text = f"""
🎲 <b>DICE</b>

💰 Balance: {balance_str}
💵 Bet: ${bet_amount:.2f}

Choose your prediction:
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🔺 HIGH (8-12) - 2x", callback_data=f"dice_play_high_{bet_amount}"),
                InlineKeyboardButton("🔻 LOW (2-7) - 2x", callback_data=f"dice_play_low_{bet_amount}")
            ],
            [InlineKeyboardButton("🎯 LUCKY 7 - 5x", callback_data=f"dice_play_seven_{bet_amount}")],
            [InlineKeyboardButton("🔙 Back to Games", callback_data="mini_app_centre")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def handle_dice_play(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle dice game play"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        parts = query.data.split("_")
        prediction = parts[2]  # high, low, seven
        bet_amount = float(parts[3])
        
        # Deduct bet amount
        success = await db_service.update_balance(user_id, -bet_amount, "game_bet")
        if not success:
            await query.edit_message_text("❌ Error processing bet. Please try again.")
            return
        
        # Roll dice
        die1, die2 = self._roll_dice()
        total = die1 + die2
        
        # Get dice emojis
        dice_emojis = {1: '⚀', 2: '⚁', 3: '⚂', 4: '⚃', 5: '⚄', 6: '⚅'}
        die1_emoji = dice_emojis[die1]
        die2_emoji = dice_emojis[die2]
        
        # Calculate result
        win_amount = 0.0
        result_text = ""
        
        if prediction == "high" and total >= 8:
            win_amount = bet_amount * 2
            result_text = f"YOU WIN! {total} is HIGH!"
        elif prediction == "low" and total <= 7:
            win_amount = bet_amount * 2
            result_text = f"YOU WIN! {total} is LOW!"
        elif prediction == "seven" and total == 7:
            win_amount = bet_amount * 5
            result_text = f"LUCKY 7! Perfect prediction!"
        else:
            if prediction == "high":
                result_text = f"You predicted HIGH but got {total}"
            elif prediction == "low":
                result_text = f"You predicted LOW but got {total}"
            elif prediction == "seven":
                result_text = f"You predicted 7 but got {total}"
        
        # Update balance if won
        if win_amount > 0:
            await db_service.update_balance(user_id, win_amount, "game_win")
        
        # Get updated balance
        user = await db_service.get_user(user_id)
        balance_str = f"${user['balance']:.2f}"
        
        # Create result message
        result_message = f"""
🎲 <b>DICE</b>

Roll: {die1_emoji} {die2_emoji} = {total}

{result_text}

💰 Bet: ${bet_amount:.2f}
🏆 Won: ${win_amount:.2f}
📊 Balance: {balance_str}
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🎲 Play Again", callback_data="game_dice"),
                InlineKeyboardButton("🎮 Other Games", callback_data="mini_app_centre")
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        
        await query.edit_message_text(result_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
