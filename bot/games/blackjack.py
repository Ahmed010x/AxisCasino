"""
Blackjack Game

Implementation of classic blackjack with hit, stand, and double down options.
"""

import random
import json
from typing import List, Dict, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database.user import get_user, save_game_session, get_game_session, delete_game_session, add_game_result


# Card values and suits
SUITS = ['♠️', '♥️', '♦️', '♣️']
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']


class BlackjackGame:
    def __init__(self, bet_amount: int):
        self.deck = self.create_deck()
        self.player_hand = []
        self.dealer_hand = []
        self.bet_amount = bet_amount
        self.game_over = False
        self.doubled_down = False
        
        # Deal initial cards
        self.deal_initial_cards()
    
    def create_deck(self) -> List[Dict[str, str]]:
        """Create a shuffled deck of cards."""
        deck = []
        for suit in SUITS:
            for rank in RANKS:
                deck.append({'rank': rank, 'suit': suit})
        random.shuffle(deck)
        return deck
    
    def deal_card(self) -> Dict[str, str]:
        """Deal one card from the deck."""
        return self.deck.pop()
    
    def deal_initial_cards(self):
        """Deal initial two cards to player and dealer."""
        for _ in range(2):
            self.player_hand.append(self.deal_card())
            self.dealer_hand.append(self.deal_card())
    
    def get_hand_value(self, hand: List[Dict[str, str]]) -> int:
        """Calculate the value of a hand."""
        value = 0
        aces = 0
        
        for card in hand:
            rank = card['rank']
            if rank in ['J', 'Q', 'K']:
                value += 10
            elif rank == 'A':
                aces += 1
                value += 11
            else:
                value += int(rank)
        
        # Handle aces
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        
        return value
    
    def is_blackjack(self, hand: List[Dict[str, str]]) -> bool:
        """Check if hand is blackjack (21 with 2 cards)."""
        return len(hand) == 2 and self.get_hand_value(hand) == 21
    
    def hit(self):
        """Player takes another card."""
        if not self.game_over:
            self.player_hand.append(self.deal_card())
            if self.get_hand_value(self.player_hand) > 21:
                self.game_over = True
    
    def double_down(self):
        """Player doubles their bet and takes exactly one more card."""
        if len(self.player_hand) == 2 and not self.doubled_down:
            self.doubled_down = True
            self.bet_amount *= 2
            self.hit()
            self.game_over = True  # Must stand after double down
    
    def dealer_play(self):
        """Dealer plays according to house rules."""
        while self.get_hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deal_card())
    
    def get_result(self) -> Tuple[str, int]:
        """Determine game result and winnings."""
        player_value = self.get_hand_value(self.player_hand)
        dealer_value = self.get_hand_value(self.dealer_hand)
        
        # Player bust
        if player_value > 21:
            return "BUST! You went over 21.", 0
        
        # Player blackjack
        if self.is_blackjack(self.player_hand):
            if self.is_blackjack(self.dealer_hand):
                return "Push! Both have blackjack.", self.bet_amount
            else:
                return "BLACKJACK! 🎉", int(self.bet_amount * 2.5)
        
        # Dealer must play if player didn't bust
        if not self.game_over:
            self.dealer_play()
            dealer_value = self.get_hand_value(self.dealer_hand)
        
        # Dealer blackjack (player doesn't have blackjack)
        if self.is_blackjack(self.dealer_hand):
            return "Dealer has blackjack. You lose.", 0
        
        # Dealer bust
        if dealer_value > 21:
            return "Dealer busts! You win! 🎉", self.bet_amount * 2
        
        # Compare values
        if player_value > dealer_value:
            return "You win! 🎉", self.bet_amount * 2
        elif player_value < dealer_value:
            return "Dealer wins. You lose.", 0
        else:
            return "Push! It's a tie.", self.bet_amount
    
    def format_hand(self, hand: List[Dict[str, str]], hide_first: bool = False) -> str:
        """Format hand for display."""
        if hide_first:
            cards = ["🃏"] + [f"{card['rank']}{card['suit']}" for card in hand[1:]]
        else:
            cards = [f"{card['rank']}{card['suit']}" for card in hand]
        return " ".join(cards)
    
    def to_dict(self) -> Dict:
        """Convert game state to dictionary for storage."""
        return {
            'deck': self.deck,
            'player_hand': self.player_hand,
            'dealer_hand': self.dealer_hand,
            'bet_amount': self.bet_amount,
            'game_over': self.game_over,
            'doubled_down': self.doubled_down
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BlackjackGame':
        """Create game from stored dictionary."""
        game = cls.__new__(cls)
        game.deck = data['deck']
        game.player_hand = data['player_hand']
        game.dealer_hand = data['dealer_hand']
        game.bet_amount = data['bet_amount']
        game.game_over = data['game_over']
        game.doubled_down = data['doubled_down']
        return game


async def start_blackjack(user_id: int, bet_amount: int) -> str:
    """Start a new blackjack game."""
    game = BlackjackGame(bet_amount)
    session_id = f"blackjack_{user_id}_{random.randint(1000, 9999)}"
    
    # Save game session
    await save_game_session(session_id, user_id, 'blackjack', json.dumps(game.to_dict()), bet_amount)
    
    return session_id


async def handle_blackjack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle blackjack game callbacks."""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    if data.startswith("blackjack_bet_"):
        # Starting a new game
        bet_suffix = data.split('_')[-1]
        
        # Check balance
        user_data = await get_user(user_id)
        if not user_data:
            await query.edit_message_text("❌ User not found! Use /start first.")
            return
        
        # Handle different bet types
        if bet_suffix == "half":
            bet_amount = max(20, user_data['balance'] // 2)
        elif bet_suffix == "allin":
            bet_amount = user_data['balance']
        elif bet_suffix == "custom":
            # Request custom amount from user
            context.user_data['awaiting_blackjack_bet'] = True
            await query.edit_message_text(
                f"💰 Current Balance: **{user_data['balance']} chips**\n\n"
                "✏️ Please enter your bet amount (minimum 20 chips):",
                parse_mode='Markdown'
            )
            return
        else:
            # Fixed bet amount
            bet_amount = int(bet_suffix)
        
        # Validate bet amount
        if user_data['balance'] < bet_amount:
            await query.edit_message_text("❌ Insufficient balance! Use /daily for free chips.")
            return
        
        if bet_amount < 20:
            await query.edit_message_text("❌ Minimum bet is 20 chips!")
            return
        
        # Start new game
        session_id = await start_blackjack(user_id, bet_amount)
        session_data = await get_game_session(session_id)
        game = BlackjackGame.from_dict(json.loads(session_data['game_data']))
        
        await show_game_state(query, game, session_id)
    
    elif data.startswith("blackjack_action_"):
        # Game action
        parts = data.split('_')
        action = parts[2]
        session_id = '_'.join(parts[3:])
        
        # Get game session
        session_data = await get_game_session(session_id)
        if not session_data:
            await query.edit_message_text("❌ Game session not found. Please start a new game.")
            return
        
        game = BlackjackGame.from_dict(json.loads(session_data['game_data']))
        
        if action == "hit":
            game.hit()
            if game.get_hand_value(game.player_hand) > 21:
                await end_game(query, game, session_id, user_id)
            else:
                await save_game_session(session_id, user_id, 'blackjack', json.dumps(game.to_dict()), game.bet_amount)
                await show_game_state(query, game, session_id)
        
        elif action == "stand":
            game.game_over = True
            await end_game(query, game, session_id, user_id)
        
        elif action == "double":
            # Check if user has enough balance for double down
            user_data = await get_user(user_id)
            if user_data['balance'] < game.bet_amount:
                await query.answer("❌ Insufficient balance to double down!")
                return
            
            game.double_down()
            await end_game(query, game, session_id, user_id)


async def show_game_state(query, game: BlackjackGame, session_id: str):
    """Display current game state."""
    player_value = game.get_hand_value(game.player_hand)
    
    # Check for immediate blackjack
    if game.is_blackjack(game.player_hand):
        await end_game(query, game, session_id, query.from_user.id)
        return
    
    game_text = f"""
🃏 **BLACKJACK** 🃏

**Dealer's Hand:** {game.format_hand(game.dealer_hand, hide_first=True)}

**Your Hand:** {game.format_hand(game.player_hand)}
**Value:** {player_value}

**Bet:** {game.bet_amount} chips

What would you like to do?
"""
    
    # Create action buttons
    keyboard = []
    
    if not game.game_over:
        action_row = [
            InlineKeyboardButton("👊 Hit", callback_data=f"blackjack_action_hit_{session_id}"),
            InlineKeyboardButton("✋ Stand", callback_data=f"blackjack_action_stand_{session_id}")
        ]
        keyboard.append(action_row)
        
        # Double down option (only with 2 cards and sufficient balance)
        if len(game.player_hand) == 2 and not game.doubled_down:
            keyboard.append([
                InlineKeyboardButton("💰 Double Down", callback_data=f"blackjack_action_double_{session_id}")
            ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(game_text, reply_markup=reply_markup, parse_mode='Markdown')


async def end_game(query, game: BlackjackGame, session_id: str, user_id: int):
    """End the game and show results."""
    result_text, win_amount = game.get_result()
    
    # Record game result
    await add_game_result(user_id, 'blackjack', game.bet_amount, win_amount, result_text)
    
    # Delete game session
    await delete_game_session(session_id)
    
    # Get updated balance
    user_data = await get_user(user_id)
    new_balance = user_data['balance'] if user_data else 0
    
    # Show final hands
    player_value = game.get_hand_value(game.player_hand)
    dealer_value = game.get_hand_value(game.dealer_hand)
    
    final_text = f"""
🃏 **BLACKJACK RESULT** 🃏

**Dealer's Hand:** {game.format_hand(game.dealer_hand)}
**Dealer Value:** {dealer_value}

**Your Hand:** {game.format_hand(game.player_hand)}
**Your Value:** {player_value}

**Result:** {result_text}

💰 **Bet:** {game.bet_amount} chips
{'🏆' if win_amount > game.bet_amount else '💸'} **{'Won' if win_amount > game.bet_amount else 'Lost'}:** {abs(win_amount - game.bet_amount)} chips
📊 **Balance:** {new_balance} chips

{'🎉 Congratulations!' if win_amount > game.bet_amount else 'Better luck next time! 🍀'}
"""
    
    # Add play again button
    keyboard = [
        [
            InlineKeyboardButton("🃏 Play Again", callback_data="game_blackjack"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(final_text, reply_markup=reply_markup, parse_mode='Markdown')


async def handle_custom_bet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom bet amount input from user"""
    if not context.user_data.get('awaiting_blackjack_bet'):
        return
    
    user_id = update.message.from_user.id
    user_data = await get_user(user_id)
    
    try:
        # Parse bet amount
        bet_amount = int(update.message.text.strip())
        
        # Validate bet amount
        if bet_amount < 20:
            await update.message.reply_text(
                f"❌ Bet amount too low!\n\nMinimum bet: 20 chips\nYour input: {bet_amount} chips\n\nPlease try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_blackjack")]])
            )
            return
        
        if not user_data:
            await update.message.reply_text("❌ User not found. Please restart with /start")
            return
        
        if bet_amount > user_data['balance']:
            await update.message.reply_text(
                f"❌ Insufficient balance!\n\nYour balance: {user_data['balance']} chips\nBet amount: {bet_amount} chips\n\nPlease try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_blackjack")]])
            )
            return
        
        # Clear the awaiting state
        context.user_data['awaiting_blackjack_bet'] = False
        
        # Start new game with custom bet
        session_id = await start_blackjack(user_id, bet_amount)
        session_data = await get_game_session(session_id)
        game = BlackjackGame.from_dict(json.loads(session_data['game_data']))
        
        # Send game state as a new message
        player_value = game.get_hand_value(game.player_hand)
        
        # Check for immediate blackjack
        if game.is_blackjack(game.player_hand):
            result_text, win_amount = game.get_result()
            await add_game_result(user_id, 'blackjack', game.bet_amount, win_amount, result_text)
            await delete_game_session(session_id)
            
            user_data = await get_user(user_id)
            new_balance = user_data['balance'] if user_data else 0
            
            dealer_value = game.get_hand_value(game.dealer_hand)
            
            final_text = f"""
🃏 **BLACKJACK RESULT** 🃏

**Dealer's Hand:** {game.format_hand(game.dealer_hand)}
**Dealer Value:** {dealer_value}

**Your Hand:** {game.format_hand(game.player_hand)}
**Your Value:** {player_value}

**Result:** {result_text}

💰 **Bet:** {game.bet_amount} chips
{'🏆' if win_amount > game.bet_amount else '💸'} **{'Won' if win_amount > game.bet_amount else 'Lost'}:** {abs(win_amount - game.bet_amount)} chips
📊 **Balance:** {new_balance} chips

{'🎉 Congratulations!' if win_amount > game.bet_amount else 'Better luck next time! 🍀'}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🃏 Play Again", callback_data="game_blackjack"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="help")
                ]
            ]
            await update.message.reply_text(final_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return
        
        game_text = f"""
🃏 **BLACKJACK** 🃏

**Dealer's Hand:** {game.format_hand(game.dealer_hand, hide_first=True)}

**Your Hand:** {game.format_hand(game.player_hand)}
**Value:** {player_value}

**Bet:** {game.bet_amount} chips

What would you like to do?
"""
        
        keyboard = []
        if not game.game_over:
            action_row = [
                InlineKeyboardButton("👊 Hit", callback_data=f"blackjack_action_hit_{session_id}"),
                InlineKeyboardButton("✋ Stand", callback_data=f"blackjack_action_stand_{session_id}")
            ]
            keyboard.append(action_row)
            
            if len(game.player_hand) == 2 and not game.doubled_down:
                keyboard.append([
                    InlineKeyboardButton("💰 Double Down", callback_data=f"blackjack_action_double_{session_id}")
                ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(game_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text(
            f"❌ Invalid input!\n\nPlease enter a valid number (e.g., 100)\n\nTry again:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_blackjack")]])
        )


# Export handlers
__all__ = ['start_blackjack', 'handle_blackjack_callback', 'handle_custom_bet_input']
