# bot.py
"""
Enhanced Telegram Casino Bot v2.0
Professional-grade casino with security, anti-fraud, and comprehensive features.
Stake-style interface with advanced game mechanics and user protection.
"""

import os
import random
import asyncio
import logging
import hashlib
import hmac
import time
import json
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv
import aiohttp
import aiohttp.web
import signal
import sys
from datetime import datetime, timedelta
from collections import defaultdict, deque

import aiosqlite
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User as TelegramUser
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler
)
import nest_asyncio
from telegram.error import TelegramError, BadRequest, Forbidden

# --- Config ---
load_dotenv()
# Load additional environment from env.litecoin file
load_dotenv("env.litecoin")

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_PATH = os.environ.get("CASINO_DB", "casino.db")

# CryptoBot configuration
CRYPTOBOT_API_TOKEN = os.environ.get("CRYPTOBOT_API_TOKEN")
CRYPTOBOT_USD_ASSET = os.environ.get("CRYPTOBOT_USD_ASSET", "USDT")
CRYPTOBOT_WEBHOOK_SECRET = os.environ.get("CRYPTOBOT_WEBHOOK_SECRET")

# Render hosting configuration
PORT = int(os.environ.get("PORT", "8001"))
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL", "300"))  # 5 minutes default

if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN in environment or .env")

# Security Configuration
MAX_BET_PER_GAME = int(os.environ.get("MAX_BET_PER_GAME", "1000"))
MAX_DAILY_LOSSES = int(os.environ.get("MAX_DAILY_LOSSES", "5000"))
ANTI_SPAM_WINDOW = int(os.environ.get("ANTI_SPAM_WINDOW", "10"))  # seconds
MAX_COMMANDS_PER_WINDOW = int(os.environ.get("MAX_COMMANDS_PER_WINDOW", "20"))

# Admin Configuration
ADMIN_USER_IDS = list(map(int, os.environ.get("ADMIN_USER_IDS", "").split(","))) if os.environ.get("ADMIN_USER_IDS") else []
SUPPORT_CHANNEL = os.environ.get("SUPPORT_CHANNEL", "@casino_support")
BOT_VERSION = "2.0.1"

# WebApp Configuration
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://your-casino-webapp.vercel.app")
WEBAPP_ENABLED = os.environ.get("WEBAPP_ENABLED", "true").lower() == "true"
WEBAPP_SECRET_KEY = os.environ.get("WEBAPP_SECRET_KEY", "your-secret-key-here")

print("🎰 Mini App Integration Status:")
print(f"✅ WebApp URL: {WEBAPP_URL}")
print(f"✅ WebApp Enabled: {WEBAPP_ENABLED}")
print(f"✅ Secret Key: {'Set' if WEBAPP_SECRET_KEY != 'your-secret-key-here' else 'Default'}")

# Rest of the configuration (keeping existing)
# VIP Level Requirements
VIP_SILVER_REQUIRED = int(os.environ.get("VIP_SILVER_REQUIRED", "1000"))
VIP_GOLD_REQUIRED = int(os.environ.get("VIP_GOLD_REQUIRED", "5000"))
VIP_DIAMOND_REQUIRED = int(os.environ.get("VIP_DIAMOND_REQUIRED", "10000"))

# Game Configuration
WEEKLY_BONUS_RATE = float(os.environ.get("WEEKLY_BONUS_RATE", "0.05"))  # 5% of weekly bets
MIN_SLOTS_BET = int(os.environ.get("MIN_SLOTS_BET", "10"))
MIN_BLACKJACK_BET = int(os.environ.get("MIN_BLACKJACK_BET", "20"))

# Withdrawal Configuration
MIN_WITHDRAWAL_USD = float(os.environ.get("MIN_WITHDRAWAL_USD", "1.00"))
MAX_WITHDRAWAL_USD_DAILY = float(os.environ.get("MAX_WITHDRAWAL_USD_DAILY", "10000.00"))
WITHDRAWAL_FEE_PERCENT = float(os.environ.get("WITHDRAWAL_FEE_PERCENT", "0.02"))  # 2% withdrawal fee
WITHDRAWAL_COOLDOWN_SECONDS = int(os.environ.get("WITHDRAWAL_COOLDOWN_SECONDS", "300"))  # 5 minutes between withdrawals

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Import CryptoBot utilities
try:
    from bot.utils.cryptobot import create_litecoin_invoice, send_litecoin
except ImportError:
    logger.warning("CryptoBot utilities not available")

# --- Utility: Fetch LTC→USD rate and format as USD ---
async def get_ltc_usd_rate() -> float:
    """Fetch the current LTC to USD conversion rate from CryptoCompare."""
    url = "https://min-api.cryptocompare.com/data/price?fsym=LTC&tsyms=USD"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                return float(data['USD'])
    except Exception as e:
        logger.error(f"Failed to fetch LTC→USD rate from CryptoCompare: {e}")
        return 0.0

async def format_usd(ltc_amount: float) -> str:
    """Format an LTC amount as USD string using the latest LTC→USD rate."""
    rate = await get_ltc_usd_rate()
    if rate == 0.0:
        return f"~${ltc_amount:.2f} USD (rate unavailable)"
    usd = ltc_amount * rate
    return f"${usd:.2f} USD"

# --- Production Database System ---
async def init_db():
    """Initialize production database"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Users table with LTC balance
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 0.1,
                games_played INTEGER DEFAULT 0,
                total_wagered REAL DEFAULT 0.0,
                total_won REAL DEFAULT 0.0,
                created_at TEXT DEFAULT '',
                last_active TEXT DEFAULT ''
            )
        """)
        
        # Game sessions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                game_type TEXT NOT NULL,
                bet_amount REAL NOT NULL,
                win_amount REAL DEFAULT 0,
                result TEXT NOT NULL,
                timestamp TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Withdrawals table for tracking and security
        await db.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount_ltc REAL NOT NULL,
                amount_usd REAL NOT NULL,
                fee_ltc REAL NOT NULL,
                fee_usd REAL NOT NULL,
                to_address TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                transaction_id TEXT DEFAULT '',
                created_at TEXT DEFAULT '',
                processed_at TEXT DEFAULT '',
                error_message TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Daily withdrawal limits tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_withdrawal_limits (
                user_id INTEGER PRIMARY KEY,
                date TEXT NOT NULL,
                total_withdrawn_usd REAL DEFAULT 0.0,
                withdrawal_count INTEGER DEFAULT 0,
                last_withdrawal_time TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Create indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_balance ON users (balance)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_game_sessions_user ON game_sessions (user_id)")
        
        await db.commit()
    logger.info(f"✅ Production database initialized at {DB_PATH}")

async def get_user(user_id: int):
    """Get user data from database"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cur.fetchone()
        if row:
            return dict(row)
        return None

async def create_user(user_id: int, username: str):
    """Create new user with 0.00 LTC starting balance"""
    current_time = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users 
            (id, username, balance, created_at, last_active) 
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, 0.0, current_time, current_time))
        await db.commit()
    return await get_user(user_id)

async def update_balance(user_id: int, amount: float):
    """Update user balance (amount in LTC)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
        await db.commit()
    user = await get_user(user_id)
    return user['balance'] if user else 0.0

async def deduct_balance(user_id: int, amount: float):
    """Deduct balance with validation (amount in LTC)"""
    user = await get_user(user_id)
    if not user or user['balance'] < amount:
        return False
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET 
                balance = balance - ?, 
                total_wagered = total_wagered + ?, 
                games_played = games_played + 1 
            WHERE id = ?
        """, (amount, amount, user_id))
        await db.commit()
    
    return True

async def add_winnings(user_id: int, amount: float):
    """Add winnings to user balance (amount in LTC)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET 
                balance = balance + ?, 
                total_won = total_won + ? 
            WHERE id = ?
        """, (amount, amount, user_id))
        await db.commit()
    user = await get_user(user_id)
    return user['balance'] if user else 0.0

# --- Start Command ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    user_data = await get_user(user_id)
    if not user_data:
        user_data = await create_user(user_id, username)
    balance_usd = await format_usd(user_data['balance'])
    text = (
        f"🎰 CASINO BOT 🎰\n\n"
        f"👋 Welcome, {username}!\n\n"
        f"💰 Balance: {balance_usd}\n"
        f"🏆 Games Played: {user_data['games_played']}\n\n"
        "Choose an action below:"
    )
    keyboard = [
        [InlineKeyboardButton("🎮 Play", callback_data="mini_app_centre"), InlineKeyboardButton("💰 Balance", callback_data="show_balance")],
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit"), InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="show_help")]
    ]
    # Edit the message if possible, otherwise send a new one
    if hasattr(update, 'callback_query') and update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Failed to edit message in start_command: {e}")
            message = getattr(update, 'message', None) or getattr(getattr(update, 'callback_query', None), 'message', None)
            if message:
                await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        message = getattr(update, 'message', None) or getattr(getattr(update, 'callback_query', None), 'message', None)
        if message:
            await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            logger.error("No message object found in update for start_command")

# --- Mini App Centre ---
async def show_mini_app_centre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the comprehensive Mini App Centre with WebApp integration"""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    balance = user['balance']
    total_games = user['games_played']
    username = user['username']
    
    text = f"""
🎮 **CASINO MINI APP CENTRE** 🎮
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎲 **{username}** | Balance: **{balance:,}** chips
🎯 **Games Played:** {total_games}

🔥 **GAME CATEGORIES**

🎰 **STAKE ORIGINALS** 
*Premium in-house games with best RTP*
• 🚀 Crash • 💣 Mines • 🏀 Plinko
• 🃏 Hi-Lo • 🎲 Limbo • 🎡 Wheel

🎲 **CLASSIC CASINO**
*Traditional casino favorites*  
• 🎰 Slots • 🃏 Blackjack • 🎡 Roulette
• 🎲 Dice • 🃄 Poker • 🎯 More

🏆 **TOURNAMENTS**
*Compete for massive prizes*
• 🔥 Weekly Events • 💎 Championships
• ⚡ Speed Rounds • 👑 VIP Tournaments

💎 **VIP GAMES**
*Exclusive high-limit experiences*
• 💰 High Stakes • 🎪 Private Tables

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎁 **ACTIVE PROMOTIONS:**
• 🎊 Weekly Bonus: 5% of all bets
• 🔗 Referral Bonus: 100 chips per friend
• 🏆 Achievement rewards for milestones

Choose your gaming experience:
"""
    
    keyboard = []
    
    # Add WebApp button if enabled (disabled for compatibility)
    # if WEBAPP_ENABLED:
    #     web_app = WebApp(url=f"{WEBAPP_URL}?user_id={user_id}&balance={balance}")
    #     keyboard.append([InlineKeyboardButton("🚀 PLAY IN WEBAPP", web_app=web_app)])
    
    # Add regular game category buttons
    keyboard.extend([
        [InlineKeyboardButton("🔥 STAKE ORIGINALS", callback_data="stake_originals")],
        [InlineKeyboardButton("🎰 CLASSIC CASINO", callback_data="classic_casino"), InlineKeyboardButton("🎮 INLINE GAMES", callback_data="inline_games")],
        [InlineKeyboardButton("🏆 TOURNAMENTS", callback_data="stake_tournaments"), InlineKeyboardButton("💎 VIP GAMES", callback_data="vip_games")],
        [InlineKeyboardButton("🎁 BONUSES", callback_data="bonus_centre"), InlineKeyboardButton("📊 STATISTICS", callback_data="show_stats")],
        [InlineKeyboardButton("⚙️ SETTINGS", callback_data="user_settings"), InlineKeyboardButton("❓ HELP", callback_data="show_help")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Mini App Command ---
async def mini_app_centre_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command handler for /app"""
    await show_mini_app_centre(update, context)

# --- Classic Casino Handler ---
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

💰 **Your Balance:** {balance:,} chips
👤 **Player:** {username}

🎮 **Traditional Casino Favorites:**

**🎰 SLOT MACHINES**
*Spin the reels for massive jackpots*
• Classic 3-reel slots
• Progressive jackpots
• Bonus rounds & free spins
• RTP: 96.5%

**🃏 BLACKJACK**
*Beat the dealer with strategy*
• Traditional 21 gameplay
• Insurance & double down
• Multiple betting options
• RTP: 98.5%

**🎡 ROULETTE**
*Red or black? Place your bets*
• European & American styles
• Inside & outside bets
• Live dealer experience
• RTP: 97.3%

**🎲 DICE GAMES**
*Simple odds, instant results*
• Even/odd predictions
• High/low bets
• Quick gameplay
• RTP: 98%

**🃄 POKER**
*Coming soon - Texas Hold'em*
• Tournament play
• Cash games
• Multi-table action

Select your classic game:
"""
    
    keyboard = [
        [InlineKeyboardButton("🎰 SLOTS", callback_data="play_slots"), InlineKeyboardButton("🃏 BLACKJACK", callback_data="play_blackjack")],
        [InlineKeyboardButton("🎡 ROULETTE", callback_data="play_roulette"), InlineKeyboardButton("🎲 DICE", callback_data="play_dice")],
        [InlineKeyboardButton("🃄 POKER", callback_data="play_poker"), InlineKeyboardButton("🎯 ALL GAMES", callback_data="all_classic_games")],
        [InlineKeyboardButton("🔙 Back to App Centre", callback_data="mini_app_centre")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Inline Games Handler ---
async def inline_games_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline games callback"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    balance = user['balance']
    username = user['username']
    
    text = f"""
🎮 **INLINE MINI GAMES** 🎮

💰 **Your Balance:** {balance:,} chips
👤 **Player:** {username}

⚡ **Quick Play Games:**
*Fast, fun, and instant results!*

**🎯 QUICK SHOTS**
*Instant win/lose games*
• Coin flip - 50/50 odds
• Lucky number - Pick 1-10
• Color guess - Red/Blue
• Instant results

**🎪 MINI CHALLENGES**
*Skill-based quick games*
• Memory match
• Number sequence
• Pattern recognition
• Reaction time

**🎊 BONUS ROUNDS**
*Special event games*
• Daily challenges
• Hourly bonuses
• Achievement unlocks
• Streak rewards

**⚡ TURBO MODE**
*Ultra-fast gameplay*
• Auto-bet options
• Quick spins
• Rapid fire games
• Time challenges

Choose your quick game:
"""
    
    keyboard = [
        [InlineKeyboardButton("🪙 COIN FLIP", callback_data="coin_flip"), InlineKeyboardButton("🎯 LUCKY NUMBER", callback_data="lucky_number")],
        [InlineKeyboardButton("🌈 COLOR GUESS", callback_data="color_guess"), InlineKeyboardButton("🧠 MEMORY GAME", callback_data="memory_game")],
        [InlineKeyboardButton("⚡ TURBO SPIN", callback_data="turbo_spin"), InlineKeyboardButton("🎁 BONUS HUNT", callback_data="bonus_hunt")],
        [InlineKeyboardButton("🎪 DAILY CHALLENGE", callback_data="daily_challenge"), InlineKeyboardButton("🔙 Back to App Centre", callback_data="mini_app_centre")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Simple Game Implementations ---

# Slots Game
async def play_slots_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle slots game"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
🎰 **SLOT MACHINES** 🎰

💰 Choose your bet amount:

🎯 **Game Info:**
• 3-reel classic slots
• Multiple paylines
• Bonus symbols
• Progressive jackpots

Select your bet:
"""
    
    keyboard = [
        [InlineKeyboardButton("🎰 Bet 10 chips", callback_data="slots_bet_10"), InlineKeyboardButton("🎰 Bet 25 chips", callback_data="slots_bet_25")],
        [InlineKeyboardButton("🎰 Bet 50 chips", callback_data="slots_bet_50"), InlineKeyboardButton("🎰 Bet 100 chips", callback_data="slots_bet_100")],
        [InlineKeyboardButton("🔙 Back to Classic", callback_data="classic_casino")],
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
        bet = int(data.split("_")[-1])
    except:
        await query.answer("Invalid bet", show_alert=True)
        return

    user = await get_user(user_id)
    result = await deduct_balance(user_id, bet)
    
    if result is False:
        await query.answer("❌ Not enough chips", show_alert=True)
        return

    # Simple slots simulation
    symbols = ["🍒", "🍋", "🍊", "🔔", "💎"]
    reel = [random.choice(symbols) for _ in range(3)]

    if reel[0] == reel[1] == reel[2]:
        # Jackpot!
        multiplier = {"🍒": 10, "🍋": 20, "🍊": 30, "🔔": 50, "💎": 100}.get(reel[0], 10)
        win_amount = bet * multiplier
        await update_balance(user_id, win_amount)
        text = f"🎰 {' '.join(reel)}\n\n🎉 **JACKPOT!** You won **{win_amount:,} chips** (x{multiplier})!"
    else:
        text = f"🎰 {' '.join(reel)}\n\n😢 No match. You lost **{bet:,} chips**."

    user_after = await get_user(user_id)
    keyboard = [
        [InlineKeyboardButton("🔄 Play Again", callback_data="play_slots"), InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    text += f"\n\n💰 **Balance:** {user_after['balance']:,} chips"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# Coin Flip Game
async def coin_flip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle coin flip game"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    text = f"""
🪙 **COIN FLIP** 🪙

💰 **Your Balance:** {user['balance']:,} chips

⚡ **Quick & Simple:**
• Choose Heads or Tails
• 50/50 odds
• Instant results
• 2x payout on win

🎯 **Betting Options:**
Choose your bet amount and side:
"""
    
    keyboard = [
        [InlineKeyboardButton("🟡 Heads - 10 chips", callback_data="coinflip_heads_10"), InlineKeyboardButton("⚫ Tails - 10 chips", callback_data="coinflip_tails_10")],
        [InlineKeyboardButton("🟡 Heads - 25 chips", callback_data="coinflip_heads_25"), InlineKeyboardButton("⚫ Tails - 25 chips", callback_data="coinflip_tails_25")],
        [InlineKeyboardButton("🟡 Heads - 50 chips", callback_data="coinflip_heads_50"), InlineKeyboardButton("⚫ Tails - 50 chips", callback_data="coinflip_tails_50")],
        [InlineKeyboardButton("🔙 Back to Inline Games", callback_data="inline_games")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def handle_coinflip_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle coin flip bet"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    try:
        parts = data.split("_")
        choice = parts[1]  # heads or tails
        bet = int(parts[2])
    except:
        await query.answer("Invalid bet format", show_alert=True)
        return
    
    user = await get_user(user_id)
    result = await deduct_balance(user_id, bet)
    
    if result is False:
        await query.answer("❌ Not enough chips", show_alert=True)
        return
    
    # Flip coin
    coin_result = random.choice(["heads", "tails"])
    coin_emoji = "🟡" if coin_result == "heads" else "⚫"
    choice_emoji = "🟡" if choice == "heads" else "⚫"
    
    if choice == coin_result:
        # Win - 2x payout
        win_amount = bet * 2
        await update_balance(user_id, win_amount)
        outcome = f"🎉 **YOU WIN!**\n\n{coin_emoji} Coin landed on **{coin_result.upper()}**\n{choice_emoji} You chose **{choice.upper()}**\n\n💰 Won: **{win_amount:,} chips**"
    else:
        outcome = f"😢 **YOU LOSE!**\n\n{coin_emoji} Coin landed on **{coin_result.upper()}**\n{choice_emoji} You chose **{choice.upper()}**\n\n💸 Lost: **{bet:,} chips**"
    
    user_after = await get_user(user_id)
    
    text = f"""
🪙 **COIN FLIP RESULT** 🪙

{outcome}

💰 **New Balance:** {user_after['balance']:,} chips

Play again or try another game:
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Flip Again", callback_data="coin_flip"), InlineKeyboardButton("🎮 Other Games", callback_data="inline_games")],
        [InlineKeyboardButton("🎰 Slots", callback_data="play_slots"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Simple Placeholder Handlers ---

async def show_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show balance with deposit/withdraw options"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    if not user:
        user = await create_user(user_id, query.from_user.username or query.from_user.first_name)
    # Await the format_usd coroutine for all balance fields
    current_balance = await format_usd(user['balance'])
    total_wagered = await format_usd(user['total_wagered'])
    total_won = await format_usd(user['total_won'])
    text = (
        f"💰 BALANCE\n\n"
        f"Current Balance: {current_balance}\n"
        f"Games Played: {user['games_played']}\n"
        f"Total Wagered: {total_wagered}\n"
        f"Total Won: {total_won}\n"
    )
    keyboard = [
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit"), InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🎮 Play", callback_data="mini_app_centre")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def main_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main panel"""
    if update.callback_query:
        await update.callback_query.answer()
    await start_command(update, context)

# Placeholder handlers
async def placeholder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder for unimplemented features"""
    query = update.callback_query
    await query.answer("🚧 This feature is coming soon! Stay tuned for updates.", show_alert=True)

# --- Deposit Handler ---
async def deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "💳 <b>Deposit</b>\n\n"
        "Choose your deposit method below.\n\n"
        "• Litecoin (CryptoBot, instant)\n"
    )
    keyboard = [
        [InlineKeyboardButton("Ł Litecoin (CryptoBot)", callback_data="deposit_crypto")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# --- Withdraw Handler ---
async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdrawal requests"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    # Check minimum withdrawal amount
    if user['balance'] < MIN_WITHDRAWAL_USD / await get_ltc_usd_rate():
        await query.answer(f"❌ Minimum withdrawal: ${MIN_WITHDRAWAL_USD:.2f}", show_alert=True)
        return
    
    # Get withdrawal history
    recent_withdrawals = await get_user_withdrawals(user_id, 3)
    pending_withdrawals = [w for w in recent_withdrawals if w['status'] == 'pending']
    
    # Check for pending withdrawals
    if pending_withdrawals:
        await query.answer("❌ You have pending withdrawals. Please wait for them to complete.", show_alert=True)
        return
    
    balance_usd = await format_usd(user['balance'])
    
    # Show recent withdrawals if any
    withdrawal_history = ""
    if recent_withdrawals:
        withdrawal_history = "\n📊 **Recent Withdrawals:**\n"
        for w in recent_withdrawals[:3]:
            status_emoji = {"completed": "✅", "pending": "⏳", "failed": "❌"}.get(w['status'], "❓")
            date = w['created_at'][:10] if w['created_at'] else "Unknown"
            withdrawal_history += f"• {status_emoji} ${w['amount_usd']:.2f} - {date}\n"
    
    text = f"""
💸 **WITHDRAW FUNDS** 💸

💰 **Available Balance:** {balance_usd}
👤 **Player:** {user['username']}

📋 **Withdrawal Requirements:**
• Minimum: ${MIN_WITHDRAWAL_USD:.2f}
• Daily Limit: ${MAX_WITHDRAWAL_USD_DAILY:.2f}
• Fee: {WITHDRAWAL_FEE_PERCENT}% of amount
• Processing: Instant via CryptoBot
• Cooldown: {WITHDRAWAL_COOLDOWN_SECONDS//60} minutes between withdrawals

🏦 **Withdrawal Methods:**

**₿ Litecoin (CryptoBot)**
• Instant processing
• Direct to your LTC address
• Low network fees
• Secure and reliable
{withdrawal_history}
Choose your withdrawal method:
"""
    
    keyboard = [
        [InlineKeyboardButton("₿ Litecoin Withdraw", callback_data="withdraw_crypto")],
        [InlineKeyboardButton("📊 Withdrawal History", callback_data="withdrawal_history")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Withdrawal History Handler ---
async def withdrawal_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's withdrawal history"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    withdrawals = await get_user_withdrawals(user_id, 10)
    
    if not withdrawals:
        text = """
📊 **WITHDRAWAL HISTORY** 📊

No withdrawals found.
        """
    else:
        text = "📊 **WITHDRAWAL HISTORY** 📊\n\n"
        
        total_withdrawn = sum(w['amount_usd'] for w in withdrawals if w['status'] == 'completed')
        total_fees = sum(w['fee_usd'] for w in withdrawals if w['status'] == 'completed')
        
        text += f"📈 **Summary:**\n"
        text += f"• Total Withdrawn: ${total_withdrawn:.2f}\n"
        text += f"• Total Fees Paid: ${total_fees:.2f}\n"
        text += f"• Total Transactions: {len(withdrawals)}\n\n"
        
        text += "📋 **Recent Withdrawals:**\n"
        
        for i, w in enumerate(withdrawals[:8], 1):
            status_emoji = {
                "completed": "✅",
                "pending": "⏳", 
                "failed": "❌"
            }.get(w['status'], "❓")
            
            date = w['created_at'][:16].replace('T', ' ') if w['created_at'] else "Unknown"
            amount_display = f"${w['amount_usd']:.2f}"
            fee_display = f"${w['fee_usd']:.4f}" if w['fee_usd'] > 0 else "Free"
            
            text += f"{i}. {status_emoji} {amount_display} (Fee: {fee_display})\n"
            text += f"   📅 {date}\n"
            if w['status'] == 'failed' and w['error_message']:
                text += f"   ❌ {w['error_message'][:30]}...\n"
            text += "\n"
    
    keyboard = [
        [InlineKeyboardButton("💸 New Withdrawal", callback_data="withdraw_crypto")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Conversation States ---
DEPOSIT_LTC_AMOUNT = 1001
WITHDRAW_LTC_AMOUNT = 1002
WITHDRAW_LTC_ADDRESS = 1003

# --- Deposit Conversation Handlers ---
async def deposit_crypto_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    min_deposit_usd = 0.50  # Set minimum deposit to $0.50
    text = (
        f"₿ Litecoin Deposit\n\n"
        f"Current Balance: {await format_usd(user['balance'])}\n\n"
        f"Enter the amount in <b>USD</b> you want to deposit (min ${min_deposit_usd:.2f}):"
    )
    message = getattr(update, 'message', None) or getattr(getattr(update, 'callback_query', None), 'message', None)
    if message:
        await message.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        logger.error("No message object found in update for deposit_crypto_start")
    return DEPOSIT_LTC_AMOUNT

async def deposit_crypto_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        usd_amount = float(update.message.text.strip())
        if usd_amount < 0.50:  # Enforce minimum deposit of $0.50
            raise ValueError
    except Exception:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid USD amount (min $0.50):")
        return DEPOSIT_LTC_AMOUNT
    try:
        # Convert USD to LTC
        ltc_usd_rate = await get_ltc_usd_rate()
        if ltc_usd_rate == 0.0:
            await update.message.reply_text("❌ Unable to fetch LTC/USD rate. Please try again later.")
            return ConversationHandler.END
        ltc_amount = usd_amount / ltc_usd_rate
        # Check required env vars before proceeding
        missing_env = []
        if not CRYPTOBOT_API_TOKEN:
            missing_env.append("CRYPTOBOT_API_TOKEN")
        if not CRYPTOBOT_WEBHOOK_SECRET:
            missing_env.append("CRYPTOBOT_WEBHOOK_SECRET")
        if missing_env:
            logger.error(f"Missing required env vars: {missing_env}")
            await update.message.reply_text(
                "❌ Deposit system misconfigured. Please contact support. [Missing env vars]"
            )
            for admin_id in ADMIN_USER_IDS:
                try:
                    await context.bot.send_message(
                        admin_id,
                        f"[ALERT] Deposit failed for user {user_id}. Missing env vars: {missing_env}"
                    )
                except Exception:
                    pass
            return ConversationHandler.END
        payload = {"hidden_message": str(user_id)}
        invoice = await create_litecoin_invoice(
            ltc_amount, user_id, address=True, invoice_type='miniapp', payload=payload
        )
        logger.info(f"CryptoBot invoice response: {invoice}")
        if invoice.get("ok"):
            result = invoice["result"]
            mini_app_url = result.get("mini_app_invoice_url")
            # Remove bot_invoice_url and address instructions to avoid external links
            text = f"✅ Deposit Invoice Created!\n\n" \
                   f"<b>Tap the button below to pay instantly in Telegram:</b>\n"
            buttons = []
            if mini_app_url:
                buttons.append([InlineKeyboardButton("💸 Pay in Mini App (Recommended)", url=mini_app_url)])
            text += "\n<b>Your balance will update automatically after payment.</b>"
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None, parse_mode=ParseMode.HTML)
        else:
            logger.error(f"CryptoBot API error: {invoice}")
            await update.message.reply_text("❌ Failed to create invoice. Please try again later.")
            for admin_id in ADMIN_USER_IDS:
                try:
                    await context.bot.send_message(
                        admin_id,
                        f"[ALERT] Deposit failed for user {user_id}. API response: {invoice}"
                    )
                except Exception:
                    pass
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Deposit error: {e}\n{tb}")
        await update.message.reply_text("❌ Deposit system temporarily unavailable. Please try again later.")
        for admin_id in ADMIN_USER_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"[ALERT] Deposit exception for user {user_id}: {e}\n{tb}"
                )
            except Exception:
                pass
    return ConversationHandler.END

# --- Withdraw Conversation Handlers ---
async def withdraw_crypto_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    # Check withdrawal limits first
    limits_check = await check_withdrawal_limits(user_id, MIN_WITHDRAWAL_USD)
    if not limits_check['allowed']:
        await update.message.reply_text(f"❌ {limits_check['reason']}")
        return ConversationHandler.END
    
    balance_usd = await format_usd(user['balance'])
    ltc_rate = await get_ltc_usd_rate()
    max_withdraw_ltc = user['balance']
    max_withdraw_usd = max_withdraw_ltc * ltc_rate
    
    # Calculate fees for display
    example_fee_ltc = calculate_withdrawal_fee(0.1)  # Example with 0.1 LTC
    example_fee_usd = example_fee_ltc * ltc_rate
    
    text = (
        f"💵 **Litecoin Withdrawal**\n\n"
        f"💰 **Available Balance:** {balance_usd}\n"
        f"📊 **Current LTC Rate:** ${ltc_rate:.2f}\n\n"
        f"📋 **Withdrawal Details:**\n"
        f"• Minimum: ${MIN_WITHDRAWAL_USD:.2f}\n"
        f"• Maximum: ${min(max_withdraw_usd, MAX_WITHDRAWAL_USD_DAILY):.2f}\n"
        f"• Fee: {WITHDRAWAL_FEE_PERCENT}% (Example: ${example_fee_usd:.4f})\n\n"
        f"💡 **Note:** Fee is deducted from withdrawal amount\n\n"
        f"Enter the amount in <b>USD</b> you want to withdraw:"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    return WITHDRAW_LTC_AMOUNT

async def withdraw_crypto_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    try:
        usd_amount = float(update.message.text.strip())
        
        # Validate minimum amount
        if usd_amount < MIN_WITHDRAWAL_USD:
            raise ValueError(f"Amount below minimum ${MIN_WITHDRAWAL_USD:.2f}")
        
        # Check withdrawal limits
        limits_check = await check_withdrawal_limits(user_id, usd_amount)
        if not limits_check['allowed']:
            await update.message.reply_text(f"❌ {limits_check['reason']}")
            return WITHDRAW_LTC_AMOUNT
        
        # Convert USD to LTC
        ltc_usd_rate = await get_ltc_usd_rate()
        if ltc_usd_rate == 0.0:
            await update.message.reply_text("❌ Unable to fetch LTC/USD rate. Please try again later.")
            return WITHDRAW_LTC_AMOUNT
        
        ltc_amount = usd_amount / ltc_usd_rate
        
        # Check if user has sufficient balance
        if ltc_amount > user['balance']:
            max_usd = user['balance'] * ltc_usd_rate
            await update.message.reply_text(f"❌ Insufficient balance. Maximum available: ${max_usd:.2f}")
            return WITHDRAW_LTC_AMOUNT
        
        # Calculate fees
        fee_ltc = calculate_withdrawal_fee(ltc_amount)
        fee_usd = fee_ltc * ltc_usd_rate
        net_ltc = ltc_amount - fee_ltc
        net_usd = net_ltc * ltc_usd_rate
        
        # Validate that after fees, user still gets meaningful amount
        if net_ltc <= 0:
            await update.message.reply_text("❌ Amount too small after fees. Please enter a larger amount.")
            return WITHDRAW_LTC_AMOUNT
        
    except ValueError as e:
        await update.message.reply_text(f"❌ Invalid amount. {str(e)}\nPlease enter a valid USD amount:")
        return WITHDRAW_LTC_AMOUNT
    except Exception as e:
        await update.message.reply_text("❌ Error processing amount. Please try again:")
        return WITHDRAW_LTC_AMOUNT
    
    # Store withdrawal details
    context.user_data['withdraw_amount_ltc'] = ltc_amount
    context.user_data['withdraw_amount_usd'] = usd_amount
    context.user_data['withdraw_fee_ltc'] = fee_ltc
    context.user_data['withdraw_fee_usd'] = fee_usd
    context.user_data['withdraw_net_ltc'] = net_ltc
    context.user_data['withdraw_net_usd'] = net_usd
    
    text = (
        f"💵 **Withdrawal Summary**\n\n"
        f"📊 **Amount Details:**\n"
        f"• Requested: <b>${usd_amount:.2f}</b> (≈ {ltc_amount:.8f} LTC)\n"
        f"• Fee ({WITHDRAWAL_FEE_PERCENT}%): <b>${fee_usd:.4f}</b> (≈ {fee_ltc:.8f} LTC)\n"
        f"• You'll receive: <b>${net_usd:.2f}</b> (≈ {net_ltc:.8f} LTC)\n\n"
        f"📍 **Next Step:**\n"
        f"Enter your Litecoin address:\n\n"
        f"💡 **Supported formats:**\n"
        f"• Legacy: L... or M...\n"
        f"• SegWit: 3...\n"
        f"• Bech32: ltc1...\n\n"
        f"⚠️ **Warning:** Double-check your address!"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    return WITHDRAW_LTC_ADDRESS

async def withdraw_crypto_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    address = update.message.text.strip()
    
    # Get withdrawal details from context
    ltc_amount = context.user_data.get('withdraw_amount_ltc')
    usd_amount = context.user_data.get('withdraw_amount_usd')
    fee_ltc = context.user_data.get('withdraw_fee_ltc')
    fee_usd = context.user_data.get('withdraw_fee_usd')
    net_ltc = context.user_data.get('withdraw_net_ltc')
    net_usd = context.user_data.get('withdraw_net_usd')
    
    if not all([ltc_amount, usd_amount, fee_ltc, fee_usd, net_ltc, net_usd]):
        await update.message.reply_text("❌ Session expired. Please start withdrawal again.")
        return ConversationHandler.END
    
    # Validate Litecoin address
    if not validate_ltc_address(address):
        await update.message.reply_text(
            "❌ Invalid Litecoin address format.\n\n"
            "Please enter a valid address:\n"
            "• Legacy: L... or M...\n"
            "• SegWit: 3...\n"
            "• Bech32: ltc1..."
        )
        return WITHDRAW_LTC_ADDRESS
    
    # Final validation: Check balance and limits again
    if user['balance'] < ltc_amount:
        await update.message.reply_text("❌ Insufficient balance.")
        return ConversationHandler.END
    
    limits_check = await check_withdrawal_limits(user_id, usd_amount)
    if not limits_check['allowed']:
        await update.message.reply_text(f"❌ {limits_check['reason']}")
        return ConversationHandler.END
    
    # Log withdrawal attempt
    withdrawal_id = await log_withdrawal(
        user_id, ltc_amount, usd_amount, fee_ltc, fee_usd, address
    )
    
    try:
        # Deduct full amount from balance (including fees)
        if not await deduct_balance(user_id, ltc_amount):
            await update_withdrawal_status(withdrawal_id, 'failed', '', 'Failed to deduct balance')
            await update.message.reply_text("❌ Failed to process withdrawal. Please try again.")
            return ConversationHandler.END
        
        # Send Litecoin via CryptoBot (send net amount after fees)
        result = await send_litecoin(address, net_ltc, f"Withdrawal for user {user_id}")
        
        if result.get("ok"):
            # Successful withdrawal
            transaction_id = result.get("result", {}).get("transfer_id", "unknown")
            await update_withdrawal_status(withdrawal_id, 'completed', str(transaction_id))
            await update_withdrawal_limits(user_id, usd_amount)
            
            success_text = (
                f"✅ **Withdrawal Successful!**\n\n"
                f"💰 **Amount:** ${net_usd:.2f} (≈ {net_ltc:.8f} LTC)\n"
                f"💸 **Fee:** ${fee_usd:.4f} (≈ {fee_ltc:.8f} LTC)\n"
                f"📍 **Address:** <code>{address}</code>\n"
                f"🆔 **Transaction ID:** <code>{transaction_id}</code>\n\n"
                f"💡 **Processing:** Your withdrawal has been processed via CryptoBot.\n"
                f"🔍 **Confirmation:** Check your wallet in a few minutes."
            )
            
            await update.message.reply_text(success_text, parse_mode=ParseMode.HTML)
            logger.info(f"Withdrawal completed: {net_ltc} LTC to {address} for user {user_id}, TX: {transaction_id}")
            
        else:
            # Failed withdrawal - refund user
            await update_balance(user_id, ltc_amount)  # Refund full amount
            error_msg = result.get("error", {}).get("name", "Unknown error")
            await update_withdrawal_status(withdrawal_id, 'failed', '', error_msg)
            
            await update.message.reply_text(
                f"❌ **Withdrawal Failed**\n\n"
                f"Your balance has been refunded.\n"
                f"Error: {error_msg}\n\n"
                f"Please try again later or contact support."
            )
            logger.error(f"CryptoBot withdrawal failed for user {user_id}: {result}")
            
    except Exception as e:
        # Exception occurred - refund user
        await update_balance(user_id, ltc_amount)  # Refund full amount
        await update_withdrawal_status(withdrawal_id, 'failed', '', str(e))
        
        await update.message.reply_text(
            "❌ **Withdrawal Failed**\n\n"
            "Your balance has been refunded.\n"
            "Please try again later or contact support."
        )
        logger.error(f"Withdrawal exception for user {user_id}: {e}")
    
    return ConversationHandler.END

# --- Withdrawal Security Functions ---

async def check_withdrawal_limits(user_id: int, usd_amount: float) -> dict:
    """Check if user can withdraw the requested amount within daily limits"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT * FROM daily_withdrawal_limits 
            WHERE user_id = ? AND date = ?
        """, (user_id, today))
        limit_data = await cur.fetchone()
        
        if limit_data:
            total_withdrawn = limit_data['total_withdrawn_usd']
            withdrawal_count = limit_data['withdrawal_count']
            last_withdrawal = limit_data['last_withdrawal_time']
            
            # Check daily amount limit
            if total_withdrawn + usd_amount > MAX_WITHDRAWAL_USD_DAILY:
                return {
                    'allowed': False,
                    'reason': f'Daily limit exceeded. Remaining: ${MAX_WITHDRAWAL_USD_DAILY - total_withdrawn:.2f}'
                }
            
            # Check cooldown period
            if last_withdrawal:
                last_time = datetime.fromisoformat(last_withdrawal)
                if (datetime.now() - last_time).total_seconds() < WITHDRAWAL_COOLDOWN_SECONDS:
                    remaining = WITHDRAWAL_COOLDOWN_SECONDS - (datetime.now() - last_time).total_seconds()
                    return {
                        'allowed': False,
                        'reason': f'Cooldown active. Wait {int(remaining/60)} minutes.'
                    }
        
        return {'allowed': True, 'reason': 'OK'}

async def update_withdrawal_limits(user_id: int, usd_amount: float):
    """Update daily withdrawal tracking"""
    today = datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.now().isoformat()
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO daily_withdrawal_limits 
            (user_id, date, total_withdrawn_usd, withdrawal_count, last_withdrawal_time)
            VALUES (
                ?, ?, 
                COALESCE((SELECT total_withdrawn_usd FROM daily_withdrawal_limits WHERE user_id = ? AND date = ?), 0) + ?,
                COALESCE((SELECT withdrawal_count FROM daily_withdrawal_limits WHERE user_id = ? AND date = ?), 0) + 1,
                ?
            )
        """, (user_id, today, user_id, today, usd_amount, user_id, today, current_time))
        await db.commit()

async def log_withdrawal(user_id: int, amount_ltc: float, amount_usd: float, fee_ltc: float, fee_usd: float, to_address: str, status: str = 'pending', transaction_id: str = '', error_message: str = '') -> int:
    """Log withdrawal attempt to database"""
    current_time = datetime.now().isoformat()
    
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO withdrawals 
            (user_id, amount_ltc, amount_usd, fee_ltc, fee_usd, to_address, status, transaction_id, created_at, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, amount_ltc, amount_usd, fee_ltc, fee_usd, to_address, status, transaction_id, current_time, error_message))
        await db.commit()
        return cur.lastrowid

async def update_withdrawal_status(withdrawal_id: int, status: str, transaction_id: str = '', error_message: str = ''):
    """Update withdrawal status"""
    current_time = datetime.now().isoformat()
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE withdrawals 
            SET status = ?, transaction_id = ?, processed_at = ?, error_message = ?
            WHERE id = ?
        """, (status, transaction_id, current_time, error_message, withdrawal_id))
        await db.commit()

async def get_user_withdrawals(user_id: int, limit: int = 10) -> list:
    """Get user's recent withdrawals"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT * FROM withdrawals 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (user_id, limit))
        rows = await cur.fetchall()
        return [dict(row) for row in rows]

def validate_ltc_address(address: str) -> bool:
    """Validate Litecoin address format"""
    if not address or len(address) < 26 or len(address) > 35:
        return False
    
    # Check for valid Litecoin address prefixes
    valid_prefixes = ['ltc1', 'L', 'M', '3']  # Bech32, P2PKH, P2SH, SegWit
    
    for prefix in valid_prefixes:
        if address.startswith(prefix):
            return True
    
    return False

def calculate_withdrawal_fee(amount_ltc: float) -> float:
    """Calculate withdrawal fee in LTC"""
    return amount_ltc * (WITHDRAWAL_FEE_PERCENT / 100)

# --- CryptoBot Webhook Endpoint (for payment detection) ---
async def cryptobot_webhook(request):
    secret = os.environ.get("CRYPTOBOT_WEBHOOK_SECRET")
    body = await request.text()
    signature = request.headers.get("X-CryptoPay-Signature")
    if not secret or not signature:
        return aiohttp.web.Response(status=401)
    expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return aiohttp.web.Response(status=403)
    data = json.loads(body)
    # Only process paid invoices
    if data.get("event") == "invoice_paid":
        payload = data["payload"]
        user_id = int(payload.get("hidden_message"))
        amount = float(payload["amount"])
        await update_balance(user_id, amount)
        logger.info(f"Credited {amount} LTC to user {user_id}")
    return aiohttp.web.Response(status=200)

# --- Main Callback Handler ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    try:
        # Main navigation
        if data == "main_panel":
            await main_panel_callback(update, context)
        elif data == "mini_app_centre":
            await show_mini_app_centre(update, context)
        elif data == "show_balance":
            await show_balance_callback(update, context)
        elif data == "deposit":
            await deposit_callback(update, context)
        elif data == "withdraw":
            await withdraw_callback(update, context)
        elif data == "deposit_crypto":
            await deposit_crypto_start(update, context)
        elif data == "withdraw_crypto":
            await withdraw_crypto_start(update, context)
        
        # Game categories
        elif data == "classic_casino":
            await classic_casino_callback(update, context)
        elif data == "inline_games":
            await inline_games_callback(update, context)
        
        # Individual games
        elif data == "play_slots":
            await play_slots_callback(update, context)
        elif data.startswith("slots_bet_"):
            await handle_slots_bet(update, context)
        elif data == "coin_flip":
            await coin_flip_callback(update, context)
        elif data.startswith("coinflip_"):
            await handle_coinflip_bet(update, context)
        
        # Deposit and withdraw
        elif data == "deposit":
            await deposit_callback(update, context)
        elif data == "withdraw":
            await withdraw_callback(update, context)
        elif data == "withdrawal_history":
            await withdrawal_history_callback(update, context)
        
        # Placeholder handlers
        else:
            await placeholder_callback(update, context)
            
    except Exception as e:
        logger.error(f"Error handling callback {data}: {e}")
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

# --- Bot Commands ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    help_text = f"""
🎰 **CASINO BOT HELP** 🎰

**Commands:**
/start - Main panel
/app - Mini App Centre
/help - This help

**Features:**
🚀 **WebApp Integration** - Play in full browser
🎮 **Classic Casino** - Slots, Blackjack, Roulette
🎯 **Inline Games** - Quick coin flip, mini games
💰 **Balance System** - Earn and spend chips

**WebApp Status:**
• URL: {WEBAPP_URL}
• Enabled: {'✅ Yes' if WEBAPP_ENABLED else '❌ No'}

Ready to play? Use /start!
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# --- Main Application ---
async def main():
    """Start the bot"""
    await init_db()  # Use production database instead of simple DB
    
    # Create application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add conversation handlers
    application.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(deposit_crypto_start, pattern="^deposit_crypto$")],
        states={
            DEPOSIT_LTC_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_crypto_amount)]
        },
        fallbacks=[]
    ))
    
    application.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(withdraw_crypto_start, pattern="^withdraw_crypto$")],
        states={
            WITHDRAW_LTC_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_crypto_amount)],
            WITHDRAW_LTC_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_crypto_address)]
        },
        fallbacks=[]
    ))
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("app", mini_app_centre_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("🎰 Casino Bot with LTC Payment System starting...")
    logger.info(f"✅ WebApp URL: {WEBAPP_URL}")
    logger.info(f"✅ WebApp Enabled: {WEBAPP_ENABLED}")
    logger.info(f"✅ Database: {DB_PATH}")
    
    # Start web server for webhook
    app = aiohttp.web.Application()
    app.router.add_post('/cryptobot/webhook', cryptobot_webhook)
    
    # Start aiohttp server
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"✅ Webhook server started on port {PORT}")
    
    # Start the bot
    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        # Keep running
        stop_event = asyncio.Event()
        
        def signal_handler():
            stop_event.set()
        
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)
        
        await stop_event.wait()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    finally:
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    print("🎰 Starting Casino Bot with Mini App Integration...")
    print(f"🚀 WebApp URL: {WEBAPP_URL}")
    print(f"✅ WebApp Enabled: {WEBAPP_ENABLED}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
