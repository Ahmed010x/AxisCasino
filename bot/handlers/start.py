"""
Start and Help Command Handlers

Handles the basic bot commands like /start and /help.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database.user import create_user, get_user
from bot.utils.achievements import check_achievements, show_achievement_notification


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Create user in database if doesn't exist
    await create_user(user.id, user.username or user.first_name)
    user_data = await get_user(user.id)
    
    # Check for achievements
    newly_earned = await check_achievements(user.id)
    if newly_earned:
        await show_achievement_notification(update, newly_earned)
    
    welcome_text = f"""
🎰 **Welcome to Casino Bot!** 🎰

Hello {user.first_name}! Welcome to the ultimate Telegram casino experience!

💰 **Your Current Balance:** {user_data['balance']} chips
🎁 **Daily Bonus:** Get free chips every day!

🎮 **Available Games:**
🎰 Slots - Classic slot machine fun
🃏 Blackjack - Beat the dealer  
🎲 Roulette - Spin the wheel of fortune
🎯 Dice - Multiple dice betting games
🃏 Poker - Texas Hold'em against the house

📊 **Features:**
🏆 Achievement system with rewards
📈 Detailed statistics tracking
🎁 Daily bonuses and streaks

Use the buttons below or type /help to see all commands!
"""

    # Create inline keyboard
    keyboard = [
        [
            InlineKeyboardButton("🎰 Play Slots", callback_data="game_slots"),
            InlineKeyboardButton("🃏 Blackjack", callback_data="game_blackjack")
        ],
        [
            InlineKeyboardButton("🎲 Roulette", callback_data="game_roulette"),
            InlineKeyboardButton("🎯 Dice Game", callback_data="game_dice")
        ],
        [
            InlineKeyboardButton("🃏 Poker", callback_data="game_poker"),
            InlineKeyboardButton("🏆 Achievements", callback_data="check_achievements")
        ],
        [
            InlineKeyboardButton("💰 Balance", callback_data="check_balance"),
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily_bonus")
        ],
        [
            InlineKeyboardButton("� Payments", callback_data="payment_menu"),
            InlineKeyboardButton("�📊 Statistics", callback_data="check_stats")
        ],
        [
            InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard_menu"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    help_text = """
🎰 **Casino Bot Commands** 🎰

**Basic Commands:**
/start - Welcome message and main menu
/help - Show this help message
/balance - Check your current chip balance
/daily - Claim your daily bonus chips
/stats - View your gaming statistics
/achievements - View your achievements
/leaderboard - View top players
/payments - Access payment center

**Games:**
/slots - Play the slot machine
/blackjack - Start a blackjack game
/roulette - Play roulette
/dice - Play various dice games
/poker - Play Texas Hold'em Poker

**Payments:**
💰 **Deposits** - Add chips to your account
💸 **Withdrawals** - Cash out your winnings
📊 **History** - View transaction history
💳 **Methods** - Manage payment methods

**How to Play:**
1. Each game requires chips to play
2. You start with 1000 free chips
3. Get daily bonus chips with /daily
4. Buy more chips via the payment center
5. Win more chips by playing games!
6. Cash out your winnings anytime!
7. Earn achievements for special rewards!

**Game Rules:**

🎰 **Slots**: Match 3 symbols to win!
- 🍒🍒🍒 = 10x bet
- 🍋🍋🍋 = 20x bet  
- 🍊🍊🍊 = 30x bet
- 🔔🔔🔔 = 50x bet
- 💎💎💎 = 100x bet

🃏 **Blackjack**: Get as close to 21 as possible without going over!

🎲 **Roulette**: Bet on numbers, colors, or odds/evens

🎯 **Dice**: Multiple games - High/Low, Exact Sum, Triple Dice

🃏 **Poker**: Texas Hold'em - Beat the dealer's hand!

🏆 **Achievements**: Complete challenges for bonus chips!

💱 **Exchange Rate**: 100 chips = $1 USD

Good luck and have fun! 🍀
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')
