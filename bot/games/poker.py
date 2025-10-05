"""
Texas Hold'em Poker Game

Implementation of simplified Texas Hold'em poker for the casino bot.
Players compete against the house with a simplified betting structure.
"""

import random
import json
from typing import List, Dict, Tuple, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database.user import get_user, save_game_session, get_game_session, delete_game_session, add_game_result


# Game constants
MIN_BET = 0.50
MAX_BET = 1000.0

# Card definitions
SUITS = ['♠️', '♥️', '♦️', '♣️']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUES = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 
    '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
}

# Hand rankings
HAND_RANKINGS = {
    'high_card': 1,
    'pair': 2,
    'two_pair': 3,
    'three_kind': 4,
    'straight': 5,
    'flush': 6,
    'full_house': 7,
    'four_kind': 8,
    'straight_flush': 9,
    'royal_flush': 10
}


class PokerGame:
    def __init__(self, ante: int):
        self.deck = self.create_deck()
        self.player_hand = []
        self.dealer_hand = []
        self.community_cards = []
        self.ante = ante
        self.current_bet = ante
        self.game_stage = 'preflop'  # preflop, flop, turn, river, showdown
        self.player_folded = False
        
        # Deal initial hands
        self.deal_initial_hands()
    
    def create_deck(self) -> List[Dict[str, str]]:
        """Create and shuffle a deck of cards."""
        deck = []
        for suit in SUITS:
            for rank in RANKS:
                deck.append({'rank': rank, 'suit': suit})
        random.shuffle(deck)
        return deck
    
    def deal_card(self) -> Dict[str, str]:
        """Deal one card from the deck."""
        return self.deck.pop()
    
    def deal_initial_hands(self):
        """Deal 2 cards to player and dealer."""
        for _ in range(2):
            self.player_hand.append(self.deal_card())
            self.dealer_hand.append(self.deal_card())
    
    def deal_flop(self):
        """Deal the flop (3 community cards)."""
        if self.game_stage == 'preflop':
            self.deck.pop()  # Burn card
            for _ in range(3):
                self.community_cards.append(self.deal_card())
            self.game_stage = 'flop'
    
    def deal_turn(self):
        """Deal the turn (4th community card)."""
        if self.game_stage == 'flop':
            self.deck.pop()  # Burn card
            self.community_cards.append(self.deal_card())
            self.game_stage = 'turn'
    
    def deal_river(self):
        """Deal the river (5th community card)."""
        if self.game_stage == 'turn':
            self.deck.pop()  # Burn card
            self.community_cards.append(self.deal_card())
            self.game_stage = 'river'
    
    def evaluate_hand(self, hole_cards: List[Dict[str, str]]) -> Tuple[int, str, List[int]]:
        """Evaluate the best 5-card hand from hole cards and community cards."""
        all_cards = hole_cards + self.community_cards
        best_hand = None
        best_rank = 0
        best_name = "High Card"
        best_values = []
        
        # Generate all possible 5-card combinations
        from itertools import combinations
        for combo in combinations(all_cards, 5):
            rank, name, values = self._evaluate_5_cards(list(combo))
            if rank > best_rank or (rank == best_rank and values > best_values):
                best_rank = rank
                best_name = name
                best_values = values
                best_hand = combo
        
        return best_rank, best_name, best_values
    
    def _evaluate_5_cards(self, cards: List[Dict[str, str]]) -> Tuple[int, str, List[int]]:
        """Evaluate a specific 5-card hand."""
        ranks = [RANK_VALUES[card['rank']] for card in cards]
        suits = [card['suit'] for card in cards]
        ranks.sort(reverse=True)
        
        # Count ranks
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        # Check for flush
        is_flush = len(set(suits)) == 1
        
        # Check for straight
        is_straight = False
        if ranks == [14, 5, 4, 3, 2]:  # A-2-3-4-5 straight
            is_straight = True
            ranks = [5, 4, 3, 2, 1]  # Treat ace as 1
        elif ranks == list(range(ranks[0], ranks[0] - 5, -1)):
            is_straight = True
        
        # Determine hand type
        counts = sorted(rank_counts.values(), reverse=True)
        
        if is_straight and is_flush:
            if ranks[0] == 14:  # Royal flush
                return HAND_RANKINGS['royal_flush'], "Royal Flush", ranks
            else:
                return HAND_RANKINGS['straight_flush'], "Straight Flush", ranks
        elif counts == [4, 1]:
            return HAND_RANKINGS['four_kind'], "Four of a Kind", ranks
        elif counts == [3, 2]:
            return HAND_RANKINGS['full_house'], "Full House", ranks
        elif is_flush:
            return HAND_RANKINGS['flush'], "Flush", ranks
        elif is_straight:
            return HAND_RANKINGS['straight'], "Straight", ranks
        elif counts == [3, 1, 1]:
            return HAND_RANKINGS['three_kind'], "Three of a Kind", ranks
        elif counts == [2, 2, 1]:
            return HAND_RANKINGS['two_pair'], "Two Pair", ranks
        elif counts == [2, 1, 1, 1]:
            return HAND_RANKINGS['pair'], "Pair", ranks
        else:
            return HAND_RANKINGS['high_card'], "High Card", ranks
    
    def get_winner(self) -> Tuple[str, str]:
        """Determine the winner and return result."""
        if self.player_folded:
            return "dealer", "Player folded"
        
        player_rank, player_name, player_values = self.evaluate_hand(self.player_hand)
        dealer_rank, dealer_name, dealer_values = self.evaluate_hand(self.dealer_hand)
        
        if player_rank > dealer_rank:
            return "player", f"Player wins with {player_name}"
        elif dealer_rank > player_rank:
            return "dealer", f"Dealer wins with {dealer_name}"
        else:
            # Same hand type, compare values
            if player_values > dealer_values:
                return "player", f"Player wins with {player_name}"
            elif dealer_values > player_values:
                return "dealer", f"Dealer wins with {dealer_name}"
            else:
                return "tie", f"Tie with {player_name}"
    
    def format_cards(self, cards: List[Dict[str, str]]) -> str:
        """Format cards for display."""
        return " ".join([f"{card['rank']}{card['suit']}" for card in cards])
    
    def format_hidden_cards(self, num_cards: int) -> str:
        """Format hidden cards for display."""
        return " ".join(["🃏"] * num_cards)
    
    def to_dict(self) -> Dict:
        """Convert game state to dictionary."""
        return {
            'deck': self.deck,
            'player_hand': self.player_hand,
            'dealer_hand': self.dealer_hand,
            'community_cards': self.community_cards,
            'ante': self.ante,
            'current_bet': self.current_bet,
            'game_stage': self.game_stage,
            'player_folded': self.player_folded
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PokerGame':
        """Create game from dictionary."""
        game = cls.__new__(cls)
        game.deck = data['deck']
        game.player_hand = data['player_hand']
        game.dealer_hand = data['dealer_hand']
        game.community_cards = data['community_cards']
        game.ante = data['ante']
        game.current_bet = data['current_bet']
        game.game_stage = data['game_stage']
        game.player_folded = data['player_folded']
        return game


async def start_poker_game(user_id: int, ante: int) -> str:
    """Start a new poker game."""
    game = PokerGame(ante)
    session_id = f"poker_{user_id}_{random.randint(1000, 9999)}"
    
    # Save game session
    await save_game_session(session_id, user_id, 'poker', json.dumps(game.to_dict()), ante)
    
    return session_id


async def show_poker_menu(update: Update, balance: int):
    """Show poker game menu."""
    poker_text = f"""
🃏 **TEXAS HOLD'EM POKER** 🃏

Current Balance: **{balance} chips**

**How to Play:**
• Get 2 hole cards, 5 community cards dealt
• Make the best 5-card hand possible
• Beat the dealer to win!

**Betting:**
• Ante: Your initial bet
• You can call, raise, or fold each round

Choose your ante:
"""
    
    keyboard = [
        [
            InlineKeyboardButton("25 chips", callback_data="poker_ante_25"),
            InlineKeyboardButton("50 chips", callback_data="poker_ante_50")
        ],
        [
            InlineKeyboardButton("100 chips", callback_data="poker_ante_100"),
            InlineKeyboardButton("200 chips", callback_data="poker_ante_200")
        ],
        [
            InlineKeyboardButton("� Half", callback_data="poker_ante_half"),
            InlineKeyboardButton("🎯 All-In", callback_data="poker_ante_allin")
        ],
        [
            InlineKeyboardButton("✏️ Custom Amount", callback_data="poker_ante_custom")
        ],
        [
            InlineKeyboardButton("�📖 Hand Rankings", callback_data="poker_rankings")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(poker_text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_hand_rankings(query):
    """Show poker hand rankings."""
    rankings_text = """
🃏 **POKER HAND RANKINGS** 🃏
*(From Highest to Lowest)*

🏆 **Royal Flush** - A♠️ K♠️ Q♠️ J♠️ 10♠️
🔥 **Straight Flush** - 5 cards in sequence, same suit
🎯 **Four of a Kind** - Four cards of same rank
🏠 **Full House** - Three of a kind + pair
💎 **Flush** - 5 cards of same suit
📈 **Straight** - 5 cards in sequence
🎲 **Three of a Kind** - Three cards of same rank
👥 **Two Pair** - Two different pairs
👫 **Pair** - Two cards of same rank
🃏 **High Card** - Highest single card

**Tips:**
• Position matters - play tight early
• Observe betting patterns
• Don't chase bad hands!
"""
    
    keyboard = [[InlineKeyboardButton("⬅️ Back to Game", callback_data="poker_main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(rankings_text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_game_state(query, game: PokerGame, session_id: str):
    """Display current poker game state."""
    # Format community cards
    if game.community_cards:
        community_display = game.format_cards(game.community_cards)
    else:
        community_display = "No community cards yet"
    
    # Show different information based on game stage
    if game.game_stage == 'preflop':
        stage_text = "**Pre-Flop** - You have your hole cards"
    elif game.game_stage == 'flop':
        stage_text = "**The Flop** - 3 community cards revealed"
    elif game.game_stage == 'turn':
        stage_text = "**The Turn** - 4th community card revealed"
    elif game.game_stage == 'river':
        stage_text = "**The River** - All 5 community cards revealed"
    else:
        stage_text = "**Showdown** - Time to reveal hands"
    
    game_text = f"""
🃏 **TEXAS HOLD'EM POKER** 🃏

{stage_text}

**Your Hole Cards:** {game.format_cards(game.player_hand)}
**Community Cards:** {community_display}

**Dealer's Cards:** {game.format_hidden_cards(2)}

**Current Bet:** {game.current_bet} chips
**Pot:** {game.current_bet * 2} chips

What's your move?
"""
    
    # Create action buttons based on game stage
    keyboard = []
    
    if game.game_stage in ['preflop', 'flop', 'turn']:
        if game.game_stage == 'preflop':
            keyboard.append([
                InlineKeyboardButton("📞 Call", callback_data=f"poker_action_call_{session_id}"),
                InlineKeyboardButton("📈 Raise", callback_data=f"poker_action_raise_{session_id}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("✅ Check", callback_data=f"poker_action_check_{session_id}"),
                InlineKeyboardButton("📈 Bet", callback_data=f"poker_action_bet_{session_id}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("❌ Fold", callback_data=f"poker_action_fold_{session_id}")
        ])
    elif game.game_stage == 'river':
        keyboard.append([
            InlineKeyboardButton("👁️ Showdown", callback_data=f"poker_action_showdown_{session_id}")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(game_text, reply_markup=reply_markup, parse_mode='Markdown')


async def end_poker_game(query, game: PokerGame, session_id: str, user_id: int):
    """End the poker game and show results."""
    winner, result_text = game.get_winner()
    
    # Calculate winnings
    if winner == "player":
        win_amount = game.current_bet * 3  # Win ante + bet + bonus
    elif winner == "tie":
        win_amount = game.current_bet  # Return ante
    else:
        win_amount = 0  # Lose ante
    
    # Record game result
    await add_game_result(user_id, 'poker', game.current_bet, win_amount, result_text)
    
    # Delete game session
    await delete_game_session(session_id)
    
    # Get updated balance
    user_data = await get_user(user_id)
    new_balance = user_data['balance'] if user_data else 0
    
    # Evaluate hands for display
    player_rank, player_name, _ = game.evaluate_hand(game.player_hand)
    dealer_rank, dealer_name, _ = game.evaluate_hand(game.dealer_hand)
    
    final_text = f"""
🃏 **POKER SHOWDOWN** 🃏

**Community Cards:** {game.format_cards(game.community_cards)}

**Your Hand:** {game.format_cards(game.player_hand)}
**Your Best:** {player_name}

**Dealer's Hand:** {game.format_cards(game.dealer_hand)}
**Dealer's Best:** {dealer_name}

**Result:** {result_text}

💰 **Ante:** {game.ante} chips
{'🏆' if win_amount > game.ante else '💸'} **{'Won' if win_amount > game.ante else 'Lost'}:** {abs(win_amount - game.ante)} chips
📊 **Balance:** {new_balance} chips

{'Great hand!' if winner == 'player' else 'Better luck next time!'}
"""
    
    # Add play again buttons
    keyboard = [
        [
            InlineKeyboardButton("🃏 Play Again", callback_data="game_poker"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(final_text, reply_markup=reply_markup, parse_mode='Markdown')


async def handle_poker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle poker game callbacks."""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    if data == "poker_main_menu":
        user_data = await get_user(user_id)
        await show_poker_menu(update, user_data['balance'])
        return
    
    if data == "poker_rankings":
        await show_hand_rankings(query)
        return
    
    if data.startswith("poker_ante_"):
        # Starting a new game
        ante_suffix = data.split('_')[2]
        
        # Check balance
        user_data = await get_user(user_id)
        if not user_data:
            await query.edit_message_text("❌ User not found. Please use /start first.")
            return
        
        # Handle different ante types
        if ante_suffix == "half":
            ante = max(MIN_BET, user_data['balance'] // 2)
        elif ante_suffix == "allin":
            ante = user_data['balance']
        elif ante_suffix == "custom":
            # Request custom amount from user
            context.user_data['awaiting_poker_ante'] = True
            await query.edit_message_text(
                f"💰 Current Balance: **{user_data['balance']} chips**\n\n"
                f"✏️ Please enter your ante amount (minimum ${MIN_BET:.2f}):",
                parse_mode='Markdown'
            )
            return
        else:
            # Fixed ante amount
            ante = int(ante_suffix)
        
        # Validate ante
        if user_data['balance'] < ante:
            await query.edit_message_text("❌ Insufficient balance! Use /daily for free chips.")
            return
        
        if ante < MIN_BET:
            await query.edit_message_text(f"❌ Minimum ante is ${MIN_BET:.2f}!")
            return
        
        # Start new game
        session_id = await start_poker_game(user_id, ante)
        session_data = await get_game_session(session_id)
        game = PokerGame.from_dict(json.loads(session_data['game_data']))
        
        await show_game_state(query, game, session_id)
    
    elif data.startswith("poker_action_"):
        # Game action
        parts = data.split('_')
        action = parts[2]
        session_id = '_'.join(parts[3:])
        
        # Get game session
        session_data = await get_game_session(session_id)
        if not session_data:
            await query.edit_message_text("❌ Game session not found. Please start a new game.")
            return
        
        game = PokerGame.from_dict(json.loads(session_data['game_data']))
        
        if action == "call" or action == "check":
            # Progress to next stage
            if game.game_stage == 'preflop':
                game.deal_flop()
            elif game.game_stage == 'flop':
                game.deal_turn()
            elif game.game_stage == 'turn':
                game.deal_river()
            elif game.game_stage == 'river':
                await end_poker_game(query, game, session_id, user_id)
                return
            
            await save_game_session(session_id, user_id, 'poker', json.dumps(game.to_dict()), game.ante)
            await show_game_state(query, game, session_id)
        
        elif action == "raise" or action == "bet":
            # Double the bet and progress
            game.current_bet *= 2
            
            if game.game_stage == 'preflop':
                game.deal_flop()
            elif game.game_stage == 'flop':
                game.deal_turn()
            elif game.game_stage == 'turn':
                game.deal_river()
            elif game.game_stage == 'river':
                await end_poker_game(query, game, session_id, user_id)
                return
            
            await save_game_session(session_id, user_id, 'poker', json.dumps(game.to_dict()), game.ante)
            await show_game_state(query, game, session_id)
        
        elif action == "fold":
            game.player_folded = True
            await end_poker_game(query, game, session_id, user_id)
        
        elif action == "showdown":
            await end_poker_game(query, game, session_id, user_id)

async def handle_custom_bet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom ante amount input from user"""
    if not context.user_data.get('awaiting_poker_ante'):
        return
    
    user_id = update.message.from_user.id
    user_data = await get_user(user_id)
    
    try:
        # Parse ante amount
        ante = int(update.message.text.strip())
        
        # Validate ante amount
        if ante < MIN_BET:
            await update.message.reply_text(
                f"❌ Ante amount too low!\n\nMinimum ante: ${MIN_BET:.2f}\nYour input: ${ante:.2f}\n\nPlease try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_poker")]])
            )
            return
        
        if not user_data:
            await update.message.reply_text("❌ User not found. Please restart with /start")
            return
        
        if ante > user_data['balance']:
            await update.message.reply_text(
                f"❌ Insufficient balance!\n\nYour balance: {user_data['balance']} chips\nAnte amount: {ante} chips\n\nPlease try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_poker")]])
            )
            return
        
        # Clear the awaiting state
        context.user_data['awaiting_poker_ante'] = False
        
        # Start new game with custom ante
        session_id = await start_poker_game(user_id, ante)
        session_data = await get_game_session(session_id)
        game = PokerGame.from_dict(json.loads(session_data['game_data']))
        
        # Send game state as a new message
        game_text = f"""
🃏 **TEXAS HOLD'EM POKER** 🃏

**Your Hand:** {game.format_cards(game.player_hand)}

**Community Cards:** {game.format_cards(game.community_cards) if game.community_cards else 'None yet'}

**Stage:** {game.game_stage.upper()}
**Ante:** {game.ante} chips
**Current Bet:** {game.current_bet} chips

What would you like to do?
"""
        
        keyboard = []
        if game.game_stage != 'river':
            keyboard.append([
                InlineKeyboardButton("✅ Call", callback_data=f"poker_action_call_{session_id}"),
                InlineKeyboardButton("⬆️ Raise", callback_data=f"poker_action_raise_{session_id}")
            ])
        keyboard.append([
            InlineKeyboardButton("❌ Fold", callback_data=f"poker_action_fold_{session_id}")
        ])
        
        if game.game_stage == 'river':
            keyboard.append([
                InlineKeyboardButton("🎲 Showdown", callback_data=f"poker_action_showdown_{session_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(game_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text(
            f"❌ Invalid input!\n\nPlease enter a valid number (e.g., 100)\n\nTry again:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="game_poker")]])
        )


# Export handlers
__all__ = ['start_poker_game', 'handle_poker_callback', 'handle_custom_bet_input', 'show_poker_menu']
