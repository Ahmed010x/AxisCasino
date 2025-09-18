from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import aiosqlite
import random
from datetime import datetime, timedelta
from typing import Any

# Import or define all referenced utility functions and constants
# These should be imported from your main bot logic or utility modules
try:
    from main import (
        get_user, create_user, format_usd, is_owner, is_admin, BOT_VERSION, DEMO_MODE, logger,
        get_ltc_usd_rate, log_admin_action, deduct_balance, add_winnings, DB_PATH
    )
except ImportError:
    # Fallbacks for testing/standalone
    async def get_user(user_id: int) -> dict: return {'user_id': user_id, 'username': 'test', 'balance': 1000, 'games_played': 0, 'total_wagered': 0, 'total_won': 0}
    async def create_user(user_id: int, username: str) -> dict: return {'user_id': user_id, 'username': username, 'balance': 1000, 'games_played': 0, 'total_wagered': 0, 'total_won': 0}
    async def format_usd(amount: float) -> str: return f"${amount:.2f}"
    def is_owner(user_id: int) -> bool: return False
    def is_admin(user_id: int) -> bool: return False
    BOT_VERSION = "2.0.1"
    DEMO_MODE = False
    import logging
    logger = logging.getLogger(__name__)
    async def get_ltc_usd_rate() -> float: return 70.0
    def log_admin_action(user_id: int, action: str): pass
    async def deduct_balance(user_id: int, amount: float) -> bool: return True
    async def add_winnings(user_id: int, amount: float) -> bool: return True
    DB_PATH = "casino.db"

# --- Bot Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start command"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    
    user_data = await get_user(user_id)
    if not user_data:
        user_data = await create_user(user_id, username)
    
    balance_usd = await format_usd(user_data['balance'])
    
    # Check if user is owner
    if is_owner(user_id):
        status_text = "👑 OWNER "
    elif is_admin(user_id):
        status_text = "🔑 ADMIN "
    else:
        status_text = ""
    
    text = (
        f"🎰 <b>CASINO BOT v{BOT_VERSION}</b> 🎰\n\n"
        f"👋 Welcome, {status_text}{username}!\n\n"
        f"💰 <b>Balance:</b> {balance_usd}\n"
        f"🏆 <b>Games Played:</b> {user_data['games_played']}\n"
        f"🎮 <b>Supported Assets:</b> LTC, TON, SOL\n\n"
        "Choose an action below:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre"), InlineKeyboardButton("💰 Balance", callback_data="show_balance")],
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit"), InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🎁 Redeem", callback_data="redeem_panel"), InlineKeyboardButton("ℹ️ Help", callback_data="show_help")],
        [InlineKeyboardButton("📊 Statistics", callback_data="show_stats")]
    ]
    
    # Add admin/owner buttons
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    if is_owner(user_id):
        keyboard.append([InlineKeyboardButton("👑 Owner Panel", callback_data="owner_panel")])
    
    # Edit the message if possible, otherwise send a new one
    if hasattr(update, 'callback_query') and update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        message = getattr(update, 'message', None) or getattr(getattr(update, 'callback_query', None), 'message', None)
        if message:
            await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        else:
            logger.error("No message object found")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information"""
    text = """
🎰 **CASINO BOT HELP** 🎰

**Commands:**
• /start - Main menu
• /help - Show this help
• /balance - Check balance
• /app - Mini app centre

**Games Available:**
• 🎰 Slots - Classic slot machines
• 🪙 Coin Flip - Heads or tails
• 🎲 Dice - Predict the outcome
• 🃏 Blackjack - Beat the dealer
• 🎡 Roulette - Red or black

**Features:**
• Multi-asset deposits (LTC, TON, SOL)
• Instant withdrawals
• Demo mode for testing
• Fair random results

**Support:**
Contact @casino_support for help
"""
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Balance and Statistics ---
async def show_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the user's current balance"""
    user = update.effective_user
    user_id = user.id
    user_data = await get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("❌ User not found. Please /start to register.")
        return
    
    balance_usd = await format_usd(user_data['balance'])
    text = (
        f"💰 <b>Your Balance</b>\n\n"
        f"👤 <b>User:</b> {user_data['username']}\n"
        f"💵 <b>Balance:</b> {balance_usd}\n"
        f"🏆 <b>Games Played:</b> {user_data['games_played']}\n"
        f"📊 <b>Total Wagered:</b> {await format_usd(user_data['total_wagered'])}\n"
        f"🎯 <b>Total Won:</b> {await format_usd(user_data['total_won'])}"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre")],
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def show_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    query = update.callback_query
    await query.answer()
    
    # Get basic stats
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Total users
        cur = await db.execute("SELECT COUNT(*) as count FROM users")
        total_users = (await cur.fetchone())['count']
        
        # Total games played
        cur = await db.execute("SELECT SUM(games_played) as total FROM users")
        total_games = (await cur.fetchone())['total'] or 0
        
        # Total wagered
        cur = await db.execute("SELECT SUM(total_wagered) as total FROM users")
        total_wagered = (await cur.fetchone())['total'] or 0.0
        
        # Active users (played in last 24h)
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        cur = await db.execute("SELECT COUNT(*) as count FROM users WHERE last_active > ?", (yesterday,))
        active_users = (await cur.fetchone())['count']
    
    wagered_usd = await format_usd(total_wagered)
    
    text = f"""
📊 <b>BOT STATISTICS</b> 📊

👥 <b>Users:</b> {total_users:,}
🎮 <b>Games Played:</b> {total_games:,}
💰 <b>Total Wagered:</b> {wagered_usd}
⚡ <b>Active Users (24h):</b> {active_users:,}

🎯 <b>Supported Assets:</b>
• Litecoin (LTC)
• Toncoin (TON)  
• Solana (SOL)

🔧 <b>Version:</b> {BOT_VERSION}
"""
    
    keyboard = [
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# --- Mini App Centre ---
async def show_mini_app_centre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the simplified Mini App Centre"""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    balance = user['balance']
    total_games = user['games_played']
    username = user['username']

    text = f"""
🎮 <b>CASINO MINI APP CENTRE</b> 🎮
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 <b>{username}</b> | Balance: <b>{await format_usd(balance)}</b>
🎯 <b>Games Played:</b> {total_games}

Welcome to the Casino! Access all games below:
"""

    keyboard = [
        [InlineKeyboardButton("🎮 All Games", callback_data="all_games")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def mini_app_centre_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command handler for /app"""
    await show_mini_app_centre(update, context)

async def mini_app_centre_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mini app centre callback"""
    await show_mini_app_centre(update, context)

async def all_games_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available games"""
    await classic_casino_callback(update, context)

# --- Classic Casino Games ---
async def classic_casino_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle classic casino games callback"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    balance = user['balance']
    username = user['username']
    
    text = f"""
🎰 **CLASSIC CASINO GAMES** 🎰

💰 **Your Balance:** {await format_usd(balance)}
👤 **Player:** {username}

🎮 **Traditional Casino Favorites:**

**🎰 SLOT MACHINES**
*Spin the reels for massive jackpots*
• Classic 3-reel slots
• Progressive jackpots
• Bonus rounds & free spins
• RTP: 96.5%

**🪙 COIN FLIP**
*Simple 50/50 chance*
• Choose heads or tails
• Instant results
• 1.92x payout
• RTP: 96%

**🎲 DICE GAMES**
*Simple odds, instant results*
• Even/odd predictions
• High/low bets
• Number predictions
• RTP: 98%
"""
    
    keyboard = [
        [InlineKeyboardButton("🎰 SLOTS", callback_data="play_slots"), InlineKeyboardButton("🪙 COIN FLIP", callback_data="coin_flip")],
        [InlineKeyboardButton("🎲 DICE", callback_data="play_dice")],
        [InlineKeyboardButton("🔙 Back to App Centre", callback_data="mini_app_centre")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Slots Game ---
async def play_slots_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle slots game"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    text = f"""
🎰 **SLOT MACHINES** 🎰

💰 Choose your bet amount (in USD):

🎯 **Game Info:**
• 3-reel classic slots
• Multiple paylines
• Bonus symbols
• Progressive jackpots

Select your bet:
"""
    
    keyboard = [
        [InlineKeyboardButton("🎰 Bet $10", callback_data="slots_bet_10"), InlineKeyboardButton("🎰 Bet $25", callback_data="slots_bet_25")],
        [InlineKeyboardButton("🎰 Bet $50", callback_data="slots_bet_50"), InlineKeyboardButton("🎰 Bet $100", callback_data="slots_bet_100")],
        [InlineKeyboardButton("🔙 Back to Games", callback_data="all_games")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def handle_slots_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle slots betting"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    try:
        bet_usd = int(data.split("_")[-1])
    except:
        await query.answer("Invalid bet", show_alert=True)
        return

    user = await get_user(user_id)
    
    # Convert USD bet to LTC
    ltc_rate = await get_ltc_usd_rate()
    bet_ltc = bet_usd / ltc_rate if ltc_rate > 0 else bet_usd * 0.01
    
    # TRUE ADMIN TEST MODE: allow all admins/owners to play with zero balance, always win, no deduction
    if is_admin(user_id):
        log_admin_action(user_id, f"Playing slots in test mode with ${bet_usd} bet")
        symbols = ["💎", "💎", "💎"]
        multiplier = 100
        win_amount_usd = bet_usd * multiplier
        text = f"🎰 {' '.join(symbols)}\n\n🧪 <b>TEST MODE (ADMIN/OWNER)</b>\n🎉 <b>JACKPOT!</b> You won <b>${win_amount_usd:,}</b> (x{multiplier})!\n\n💰 <b>Balance:</b> {await format_usd(user['balance'])}"
        keyboard = [
            [InlineKeyboardButton("🔄 Play Again", callback_data="play_slots"), InlineKeyboardButton("🎮 Other Games", callback_data="all_games")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return
    
    # DEMO MODE: allow all users to play with zero balance, always win, no deduction
    if DEMO_MODE:
        symbols = ["💎", "💎", "💎"]
        multiplier = 100
        win_amount_usd = bet_usd * multiplier
        text = f"🎰 {' '.join(symbols)}\n\n🧪 <b>DEMO MODE</b>\n🎉 <b>JACKPOT!</b> You won <b>${win_amount_usd:,}</b> (x{multiplier})!\n\n💰 <b>Balance:</b> {await format_usd(user['balance'])}"
        keyboard = [
            [InlineKeyboardButton("🔄 Play Again", callback_data="play_slots"), InlineKeyboardButton("🎮 Other Games", callback_data="all_games")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return
    
    # Check balance
    if user['balance'] < bet_ltc:
        await query.edit_message_text(
            "❌ Insufficient balance. Please deposit to continue.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Deposit", callback_data="deposit")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
            ])
        )
        return
    
    # Deduct balance
    if not await deduct_balance(user_id, bet_ltc):
        await query.edit_message_text(
            "❌ Failed to process bet. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
            ])
        )
        return

    # Simple slots simulation
    symbols = ["🍒", "🍋", "🍊", "🔔", "💎"]
    reel = [random.choice(symbols) for _ in range(3)]

    if reel[0] == reel[1] == reel[2]:
        # Jackpot!
        multiplier = {"🍒": 10, "🍋": 20, "🍊": 30, "🔔": 50, "💎": 100}.get(reel[0], 10)
        win_amount_ltc = bet_ltc * multiplier
        await add_winnings(user_id, win_amount_ltc)
        win_amount_usd = win_amount_ltc * ltc_rate if ltc_rate > 0 else win_amount_ltc * 100
        text = f"🎰 {' '.join(reel)}\n\n🎉 **JACKPOT!** You won **${win_amount_usd:.2f}** (x{multiplier})!"
    else:
        text = f"🎰 {' '.join(reel)}\n\n😢 No match. You lost **${bet_usd}**."

    user_after = await get_user(user_id)
    keyboard = [
        [InlineKeyboardButton("🔄 Play Again", callback_data="play_slots"), InlineKeyboardButton("🎮 Other Games", callback_data="all_games")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    text += f"\n\n💰 **Balance:** {await format_usd(user_after['balance'])}"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# Continue in next part...
