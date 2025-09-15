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
CRYPTOBOT_LITECOIN_ASSET = os.environ.get("CRYPTOBOT_LITECOIN_ASSET", "LTCTRC20")
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
    """Create new user with 0.1 LTC starting balance"""
    current_time = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users 
            (id, username, balance, created_at, last_active) 
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, 0.1, current_time, current_time))
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
    
    # Get or create user
    user_data = await get_user(user_id)
    if not user_data:
        user_data = await create_user(user_id, username)
    
    text = f"""
🎰 **CASINO BOT** 🎰

👋 *Welcome, {username}!*

💰 **Balance: {user_data['balance']:.8f} LTC**
🏆 **Games Played: {user_data['games_played']}**

Choose an action below:
"""
    
    keyboard = [
        [InlineKeyboardButton("🎮 Mini App Centre", callback_data="mini_app_centre"), InlineKeyboardButton("💰 Check Balance", callback_data="show_balance")],
        [InlineKeyboardButton("🎁 Bonuses", callback_data="bonus_centre"), InlineKeyboardButton("📊 My Statistics", callback_data="show_stats")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard"), InlineKeyboardButton("⚙️ Settings", callback_data="user_settings")],
        [InlineKeyboardButton("ℹ️ Help & Info", callback_data="show_help")]
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

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
        [InlineKeyboardButton("🔙 MAIN MENU", callback_data="main_panel")]
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
        [InlineKeyboardButton("🔙 Back to App Centre", callback_data="mini_app_centre")]
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
        [InlineKeyboardButton("🎪 DAILY CHALLENGE", callback_data="daily_challenge"), InlineKeyboardButton("🔙 Back to App Centre", callback_data="mini_app_centre")]
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
        [InlineKeyboardButton("🔙 Back to Classic", callback_data="classic_casino")]
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
        [InlineKeyboardButton("🔙 Back to Inline Games", callback_data="inline_games")]
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
    
    text = f"""
💰 **BALANCE OVERVIEW** 💰

💎 **Current Balance:** {user['balance']:.8f} LTC
🎮 **Games Played:** {user['games_played']}
💸 **Total Wagered:** {user['total_wagered']:.8f} LTC
💰 **Total Won:** {user['total_won']:.8f} LTC

Ready to manage your funds or play more games?
"""
    
    keyboard = [
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit"), InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre"), InlineKeyboardButton("🎁 Get Bonus", callback_data="bonus_centre")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def main_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main panel"""
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
        [InlineKeyboardButton("🔙 Back to Balance", callback_data="show_balance")]
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
    min_withdrawal = 0.01
    if user['balance'] < min_withdrawal:
        await query.answer(f"❌ Minimum withdrawal: {min_withdrawal} LTC", show_alert=True)
        return
    
    text = f"""
💸 **WITHDRAW FUNDS** 💸

💰 **Available Balance:** {user['balance']:.8f} LTC
👤 **Player:** {user['username']}

📋 **Withdrawal Requirements:**
• Minimum: {min_withdrawal} LTC
• Maximum: 100 LTC per day
• Processing: Instant via CryptoBot
• Network fees may apply

🏦 **Withdrawal Methods:**

**₿ Litecoin (CryptoBot)**
• Instant processing
• Direct to your LTC address
• Low network fees
• Min: {min_withdrawal} LTC

Choose your withdrawal method:
"""
    
    keyboard = [
        [InlineKeyboardButton("₿ Litecoin Withdraw", callback_data="withdraw_crypto")],
        [InlineKeyboardButton("🔙 Back to Balance", callback_data="show_balance")]
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
    min_deposit = 0.01
    text = (
        f"₿ <b>Litecoin Deposit</b>\n\n"
        f"Current Balance: <b>{user['balance']:.8f} LTC</b>\n\n"
        f"Enter the amount of LTC you want to deposit (min {min_deposit} LTC):"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    return DEPOSIT_LTC_AMOUNT

async def deposit_crypto_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        amount = float(update.message.text.strip())
        if amount < 0.01:
            raise ValueError
    except Exception:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid LTC amount (min 0.01):")
        return DEPOSIT_LTC_AMOUNT
    
    # Create invoice with unique address
    try:
        invoice = await create_litecoin_invoice(amount, user_id, address=True)
        if invoice.get("ok"):
            result = invoice["result"]
            pay_url = result.get("pay_url")
            address = result.get("address")
            text = f"✅ Deposit Invoice Created!\n\n" \
                   f"Send <b>{amount} LTC</b> to the unique address below:\n" \
                   f"<code>{address}</code>\n\n" \
                   f"Or pay using this link: {pay_url}\n\n" \
                   f"After payment, your balance will be updated automatically."
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("❌ Failed to create invoice. Please try again later.")
    except Exception as e:
        logger.error(f"Deposit error: {e}")
        await update.message.reply_text("❌ Deposit system temporarily unavailable. Please try again later.")
    
    return ConversationHandler.END

# --- Withdraw Conversation Handlers ---
async def withdraw_crypto_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    min_withdraw = 0.01
    text = (
        f"₿ <b>Litecoin Withdraw</b>\n\n"
        f"Available Balance: <b>{user['balance']:.8f} LTC</b>\n\n"
        f"Enter the amount of LTC you want to withdraw (min {min_withdraw} LTC):"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    return WITHDRAW_LTC_AMOUNT

async def withdraw_crypto_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    try:
        amount = float(update.message.text.strip())
        if amount < 0.01:
            raise ValueError("Amount too small")
        if amount > user['balance']:
            raise ValueError("Insufficient balance")
    except Exception:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid LTC amount (min 0.01) within your balance:")
        return WITHDRAW_LTC_AMOUNT
    
    # Store amount in context for next step
    context.user_data['withdraw_amount'] = amount
    
    text = (
        f"₿ <b>Litecoin Withdraw</b>\n\n"
        f"Amount: <b>{amount} LTC</b>\n\n"
        f"Now enter your Litecoin address:\n"
        f"(Example: ltc1q... or M...)"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    return WITHDRAW_LTC_ADDRESS

async def withdraw_crypto_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    address = update.message.text.strip()
    amount = context.user_data.get('withdraw_amount')
    
    if not amount:
        await update.message.reply_text("❌ Session expired. Please start withdrawal again.")
        return ConversationHandler.END
    
    # Basic address validation
    if not (address.startswith(('ltc1', 'L', 'M', '3')) and len(address) >= 26):
        await update.message.reply_text("❌ Invalid Litecoin address format. Please enter a valid address:")
        return WITHDRAW_LTC_ADDRESS
    
    # Process withdrawal
    try:
        # Check balance again
        if user['balance'] < amount:
            await update.message.reply_text("❌ Insufficient balance.")
            return ConversationHandler.END
        
        # Deduct balance
        if not await deduct_balance(user_id, amount):
            await update.message.reply_text("❌ Failed to process withdrawal.")
            return ConversationHandler.END
        
        # Send LTC via CryptoBot
        result = await send_litecoin(address, amount, f"Withdrawal for user {user_id}")
        
        if result.get("ok"):
            await update.message.reply_text(
                f"✅ Withdrawal Successful!\n\n"
                f"Amount: <b>{amount} LTC</b>\n"
                f"Address: <code>{address}</code>\n\n"
                f"Transaction has been processed via CryptoBot.",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Withdrawal processed: {amount} LTC to {address} for user {user_id}")
        else:
            # Refund balance if withdrawal failed
            await update_balance(user_id, amount)
            await update.message.reply_text("❌ Withdrawal failed. Your balance has been refunded. Please try again later.")
            logger.error(f"CryptoBot withdrawal failed for user {user_id}: {result}")
        
    except Exception as e:
        # Refund balance if withdrawal failed
        await update_balance(user_id, amount)
        await update.message.reply_text("❌ Withdrawal failed. Your balance has been refunded. Please try again later.")
        logger.error(f"Withdrawal error for user {user_id}: {e}")
    
    return ConversationHandler.END

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
        user_id = int(data["payload"]["hidden_message"])
        amount = float(data["payload"]["amount"])
        # Credit user balance directly in LTC (no conversion)
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
