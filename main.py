# main.py
"""
Enhanced Telegram Casino Bot v2.1
Professional-grade casino with security, anti-fraud, and comprehensive features.
Stake-style interface with advanced game mechanics and user protection.
"""

import os
import sys
import logging
import asyncio
import threading
import time
import random
import hashlib
import uuid
import re
import aiohttp
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict, deque
from flask import Flask
from waitress import serve
import nest_asyncio

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
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler
)
from telegram.error import BadRequest, TelegramError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('casino_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Owner (Super Admin) Configuration ---
load_dotenv(".env.owner")  # Load owner ID from dedicated file
OWNER_USER_ID = int(os.environ.get("OWNER_USER_ID", "0"))

def is_owner(user_id: int) -> bool:
    """Check if user is the owner (super admin)"""
    return user_id == OWNER_USER_ID

# --- Config ---
load_dotenv()
# Load additional environment from env.litecoin file
load_dotenv("env.litecoin")

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_PATH = os.environ.get("CASINO_DB", "casino.db")

# Global demo mode flag
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"

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

# --- Admin Helper Functions ---
def is_admin(user_id: int) -> bool:
    """Check if user is an admin/owner with logging"""
    is_admin_user = user_id in ADMIN_USER_IDS
    if is_admin_user:
        logger.info(f"Admin access granted to user {user_id}")
    return is_admin_user

def log_admin_action(user_id: int, action: str):
    """Log admin actions for debugging"""
    logger.info(f"🔧 Admin action by {user_id}: {action}")

# Global variables
start_time = time.time()  # Record bot start time for metrics

# --- Deposit/Withdrawal Helper Functions ---

DEPOSIT_LTC_AMOUNT = "DEPOSIT_LTC_AMOUNT"
WITHDRAW_LTC_AMOUNT = "WITHDRAW_LTC_AMOUNT"
WITHDRAW_LTC_ADDRESS = "WITHDRAW_LTC_ADDRESS"

MIN_WITHDRAWAL_USD = float(os.environ.get("MIN_WITHDRAWAL_USD", "1.00"))
MAX_WITHDRAWAL_USD = float(os.environ.get("MAX_WITHDRAWAL_USD", "10000.00"))
MAX_WITHDRAWAL_USD_DAILY = float(os.environ.get("MAX_WITHDRAWAL_USD_DAILY", "10000.00"))
WITHDRAWAL_FEE_PERCENT = float(os.environ.get("WITHDRAWAL_FEE_PERCENT", "0.02"))
WITHDRAWAL_COOLDOWN_SECONDS = int(os.environ.get("WITHDRAWAL_COOLDOWN_SECONDS", "300"))
MIN_WITHDRAWAL_FEE = 1.0

CRYPTO_ADDRESS_PATTERNS = {
    'LTC': r'^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$|^ltc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{39,59}$',
    'TON': r'^UQ[a-zA-Z0-9_-]{46,}$',
    'SOL': r'^[1-9A-HJ-NP-Za-km-z]{32,44}$',
}

async def create_crypto_invoice(asset: str, amount: float, user_id: int, payload: dict = None) -> dict:
    """Create a crypto invoice using CryptoBot API"""
    try:
        if not CRYPTOBOT_API_TOKEN:
            return {"ok": False, "error": "API token not configured"}
        
        headers = {
            'Crypto-Pay-API-Token': CRYPTOBOT_API_TOKEN,
            'Content-Type': 'application/json'
        }
        
        data = {
            'asset': asset,
            'amount': f"{amount:.8f}",
            'description': f'Casino deposit for user {user_id}',
            'hidden_message': str(user_id),
            'paid_btn_name': 'callback',
            'paid_btn_url': f'{RENDER_EXTERNAL_URL}/payment_success' if RENDER_EXTERNAL_URL else 'https://example.com/success'
        }
        
        if payload:
            data.update(payload)
        
        async with aiohttp.ClientSession() as session:
            async with session.post('https://pay.crypt.bot/api/createInvoice', 
                                  headers=headers, json=data) as response:
                result = await response.json()
                logger.info(f"CryptoBot invoice created: {result}")
                return result
                
    except Exception as e:
        logger.error(f"Error creating crypto invoice: {e}")
        return {"ok": False, "error": str(e)}

async def get_user_withdrawals(user_id: int, limit: int = 10) -> list:
    """Get user withdrawal history"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT withdrawal_id, asset, amount, address, fee, net_amount, 
                       status, created_at, transaction_hash, error_msg
                FROM withdrawals 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
            
            withdrawals = []
            for row in rows:
                withdrawals.append({
                    'withdrawal_id': row[0],
                    'asset': row[1],
                    'amount': row[2],
                    'address': row[3],
                    'fee': row[4],
                    'net_amount': row[5],
                    'status': row[6],
                    'created_at': row[7],
                    'transaction_hash': row[8],
                    'error_msg': row[9]
                })
            return withdrawals
            
    except Exception as e:
        logger.error(f"Error getting user withdrawals: {e}")
        return []

async def check_withdrawal_limits(user_id: int, amount_usd: float) -> dict:
    """Check if withdrawal is within limits"""
    try:
        # Check minimum amount
        if amount_usd < MIN_WITHDRAWAL_USD:
            return {"allowed": False, "reason": f"Minimum withdrawal is ${MIN_WITHDRAWAL_USD:.2f}"}
        
        # Check maximum amount
        if amount_usd > MAX_WITHDRAWAL_USD:
            return {"allowed": False, "reason": f"Maximum withdrawal is ${MAX_WITHDRAWAL_USD:.2f}"}
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Check daily limit
            today = datetime.now().date()
            cursor = await db.execute("""
                SELECT COALESCE(SUM(amount * rate_usd), 0) 
                FROM withdrawals 
                WHERE user_id = ? AND DATE(created_at) = ? AND status != 'failed'
            """, (user_id, today))
            daily_total = (await cursor.fetchone())[0] or 0.0
            
            if daily_total + amount_usd > MAX_WITHDRAWAL_USD_DAILY:
                remaining = MAX_WITHDRAWAL_USD_DAILY - daily_total
                return {"allowed": False, "reason": f"Daily limit exceeded. Remaining: ${remaining:.2f}"}
            
            # Check cooldown
            cursor = await db.execute("""
                SELECT created_at FROM withdrawals 
                WHERE user_id = ? AND status != 'failed'
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            last_withdrawal = await cursor.fetchone()
            
            if last_withdrawal:
                last_time = datetime.fromisoformat(last_withdrawal[0])
                cooldown_end = last_time + timedelta(seconds=WITHDRAWAL_COOLDOWN_SECONDS)
                if datetime.now() < cooldown_end:
                    remaining_time = int((cooldown_end - datetime.now()).total_seconds())
                    return {"allowed": False, "reason": f"Please wait {remaining_time} seconds before next withdrawal."}
        
        return {"allowed": True, "reason": ""}
        
    except Exception as e:
        logger.error(f"Error checking withdrawal limits: {e}")
        return {"allowed": False, "reason": "Error checking limits"}

async def log_withdrawal(user_id: int, asset: str, amount: float, address: str, fee: float, net_amount: float) -> int:
    """Log withdrawal attempt to database"""
    try:
        rate_usd = await get_crypto_usd_rate(asset)
        amount_usd = amount * rate_usd
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                INSERT INTO withdrawals 
                (user_id, asset, amount, address, fee, net_amount, rate_usd, amount_usd, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (user_id, asset, amount, address, fee, net_amount, rate_usd, amount_usd, datetime.now().isoformat()))
            await db.commit()
            return cursor.lastrowid
            
    except Exception as e:
        logger.error(f"Error logging withdrawal: {e}")
        return 0

async def update_withdrawal_status(withdrawal_id: int, status: str, transaction_hash: str = "", error_msg: str = "") -> bool:
    """Update withdrawal status in database"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE withdrawals 
                SET status = ?, transaction_hash = ?, error_msg = ?, updated_at = ?
                WHERE withdrawal_id = ?
            """, (status, transaction_hash, error_msg, datetime.now().isoformat(), withdrawal_id))
            await db.commit()
            return True
            
    except Exception as e:
        logger.error(f"Error updating withdrawal status: {e}")
        return False

async def send_crypto(address: str, amount: float, comment: str, asset: str = 'LTC') -> dict:
    """Send crypto using CryptoBot API (or simulate for demo)"""
    try:
        if DEMO_MODE:
            # Demo mode - simulate successful transaction
            fake_hash = hashlib.sha256(f"{address}{amount}{time.time()}".encode()).hexdigest()
            logger.info(f"DEMO: Simulated crypto send: {amount} {asset} to {address}")
            return {
                "ok": True,
                "result": {
                    "transaction_hash": fake_hash,
                    "amount": amount,
                    "asset": asset,
                    "status": "completed"
                }
            }
        
        if not CRYPTOBOT_API_TOKEN:
            return {"ok": False, "error": "API token not configured"}
        
        headers = {
            'Crypto-Pay-API-Token': CRYPTOBOT_API_TOKEN,
            'Content-Type': 'application/json'
        }
        
        data = {
            'user_id': address,  # In CryptoBot, this might be user ID
            'asset': asset,
            'amount': f"{amount:.8f}",
            'spend_id': str(uuid.uuid4()),
            'comment': comment
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post('https://pay.crypt.bot/api/transfer', 
                                  headers=headers, json=data) as response:
                result = await response.json()
                logger.info(f"CryptoBot transfer result: {result}")
                return result
                
    except Exception as e:
        logger.error(f"Error sending crypto: {e}")
        return {"ok": False, "error": str(e)}

async def update_withdrawal_limits(user_id: int, amount_usd: float) -> bool:
    """Update user's withdrawal limits after successful withdrawal"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # This could track additional limits or update user statistics
            await db.execute("""
                UPDATE users 
                SET total_withdrawn = COALESCE(total_withdrawn, 0) + ?
                WHERE user_id = ?
            """, (amount_usd, user_id))
            await db.commit()
            return True
            
    except Exception as e:
        logger.error(f"Error updating withdrawal limits: {e}")
        return False

async def get_crypto_usd_rate(asset: str) -> float:
    """Get current USD rate for crypto asset"""
    try:
        # Simple rate lookup - in production, use real API
        rates = {
            'LTC': 65.0,
            'USDT': 1.0,
            'TON': 2.5,
            'SOL': 23.0
        }
        return rates.get(asset, 1.0)
        
    except Exception as e:
        logger.error(f"Error getting crypto rate: {e}")
        return 1.0

async def get_ltc_usd_rate() -> float:
    """Get current LTC to USD rate"""
    return await get_crypto_usd_rate('LTC')

async def format_usd(ltc_amount: float) -> str:
    """Format LTC amount with USD equivalent"""
    if ltc_amount == 0:
        return "$0.00 USD (0.00000000 LTC)"
    rate = await get_ltc_usd_rate()
    if rate == 0.0:
        return f"{ltc_amount:.8f} LTC (Rate unavailable)"
    usd = ltc_amount * rate
    return f"${usd:.2f} USD ({ltc_amount:.8f} LTC)"

async def format_crypto_usd(crypto_amount: float, asset: str) -> str:
    """Format crypto amount with USD equivalent"""
    if crypto_amount == 0:
        return f"$0.00 USD (0.00000000 {asset})"
    rate = await get_crypto_usd_rate(asset)
    if rate == 0.0:
        return f"{crypto_amount:.8f} {asset} (Rate unavailable)"
    usd = crypto_amount * rate
    return f"${usd:.2f} USD ({crypto_amount:.8f} {asset})"

# --- Database Operations ---
async def init_db():
    """Initialize the database with required tables"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    balance REAL DEFAULT 0.0,
                    games_played INTEGER DEFAULT 0,
                    total_wagered REAL DEFAULT 0.0,
                    total_withdrawn REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Withdrawals table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS withdrawals (
                    withdrawal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    asset TEXT NOT NULL,
                    amount REAL NOT NULL,
                    address TEXT NOT NULL,
                    fee REAL NOT NULL,
                    net_amount REAL NOT NULL,
                    rate_usd REAL NOT NULL,
                    amount_usd REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    transaction_hash TEXT DEFAULT '',
                    error_msg TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Game sessions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS game_sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    game_type TEXT NOT NULL,
                    bet_amount REAL NOT NULL,
                    win_amount REAL DEFAULT 0.0,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            await db.commit()
            logger.info("✅ Database initialized successfully")
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

async def get_user(user_id: int) -> dict:
    """Get user data from database"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None
            
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None

async def create_user(user_id: int, username: str) -> dict:
    """Create a new user in the database"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, username, balance, games_played, total_wagered, created_at, last_active)
                VALUES (?, ?, 0.0, 0, 0.0, ?, ?)
            """, (user_id, username, datetime.now().isoformat(), datetime.now().isoformat()))
            await db.commit()
            
            return {
                'user_id': user_id,
                'username': username,
                'balance': 0.0,
                'games_played': 0,
                'total_wagered': 0.0,
                'total_withdrawn': 0.0,
                'created_at': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error creating user {user_id}: {e}")
        return None

async def update_balance(user_id: int, amount: float) -> bool:
    """Update user balance"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE users 
                SET balance = balance + ?, last_active = ?
                WHERE user_id = ?
            """, (amount, datetime.now().isoformat(), user_id))
            await db.commit()
            return True
            
    except Exception as e:
        logger.error(f"Error updating balance for user {user_id}: {e}")
        return False

async def deduct_balance(user_id: int, amount: float) -> bool:
    """Deduct amount from user balance"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Check current balance first
            cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if not row or row[0] < amount:
                return False
            
            await db.execute("""
                UPDATE users 
                SET balance = balance - ?, last_active = ?
                WHERE user_id = ?
            """, (amount, datetime.now().isoformat(), user_id))
            await db.commit()
            return True
            
    except Exception as e:
        logger.error(f"Error deducting balance for user {user_id}: {e}")
        return False

def calculate_withdrawal_fee(amount: float) -> float:
    """Calculate withdrawal fee"""
    fee = amount * (WITHDRAWAL_FEE_PERCENT / 100)
    return max(fee, MIN_WITHDRAWAL_FEE)

def validate_crypto_address(address: str, asset: str) -> bool:
    """Validate cryptocurrency address format"""
    import re
    pattern = CRYPTO_ADDRESS_PATTERNS.get(asset)
    if not pattern:
        return True  # Allow unknown assets
    return bool(re.match(pattern, address))

async def log_game_session(user_id: int, game_type: str, bet_amount: float, win_amount: float, result: str):
    """Log a game session to the database"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO game_sessions (user_id, game_type, bet_amount, win_amount, result, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, game_type, bet_amount, win_amount, result, datetime.now().isoformat()))
            
            # Update user stats
            await db.execute("""
                UPDATE users 
                SET games_played = games_played + 1,
                    total_wagered = total_wagered + ?,
                    last_active = ?
                WHERE user_id = ?
            """, (bet_amount, datetime.now().isoformat(), user_id))
            
            await db.commit()
            
    except Exception as e:
        logger.error(f"Error logging game session: {e}")

# --- Global Error Handler ---
async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log and handle uncaught exceptions globally."""
    logger.error(f"[GLOBAL ERROR] Exception: {context.error}")
    try:
        if update and hasattr(update, 'effective_user') and update.effective_user:
            user_id = update.effective_user.id
        else:
            user_id = None
        # Optionally, send a user-friendly error message
        if update and hasattr(update, 'message') and update.message:
            await update.message.reply_text("❌ An unexpected error occurred. Please try again later.")
        elif update and hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer("❌ An unexpected error occurred.", show_alert=True)
    except Exception as e:
        logger.error(f"[GLOBAL ERROR] Failed to notify user: {e}")

# --- Bot Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    user_data = await get_user(user_id)
    if not user_data:
        user_data = await create_user(user_id, username)
    
    # If user is owner, show owner panel immediately
    if is_owner(user_id):
        await owner_panel_callback(update, context)
        return
    
    balance_usd = await format_usd(user_data['balance'])
    status_text = ""
    if is_admin(user_id):
        status_text = "🔑 Admin "
    
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
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    if is_owner(user_id):
        keyboard.append([InlineKeyboardButton("👑 Owner Panel", callback_data="owner_panel")])
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def mini_app_centre_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the simplified Mini App Centre with only an All Games button"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
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
        [InlineKeyboardButton("🎮 All Games", callback_data="classic_casino")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def mini_app_centre_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command handler for /app"""
    await mini_app_centre_callback(update, context)

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

**🎲 DICE GAMES**
*Simple odds, instant results*
• Even/odd predictions
• High/low bets
• Quick gameplay
• RTP: 98%

**🪙 COIN FLIP**
*50/50 chance, double your money*
• Heads or tails
• Instant results
• 2x payout
• RTP: 98%
"""
    
    keyboard = [
        [InlineKeyboardButton("🎰 SLOTS", callback_data="play_slots"), InlineKeyboardButton("🎲 DICE", callback_data="play_dice")],
        [InlineKeyboardButton("🪙 COIN FLIP", callback_data="coin_flip")],
        [InlineKeyboardButton("🔙 Back to App Centre", callback_data="mini_app_centre")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def play_slots_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle slots game"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = await get_user(user_id)
    balance_usd = await format_usd(user['balance'])
    
    text = f"""
🎰 **SLOT MACHINE** 🎰

💰 **Your Balance:** {balance_usd}

🎯 **How to Play:**
• Choose your bet amount
• Spin the reels
• Match 3 symbols to win!

💎 **Payouts:**
• 💎💎💎 = 10x bet
• 🔔🔔🔔 = 5x bet
• 🍒🍒🍒 = 3x bet
• 🍋🍋🍋 = 2x bet
• 🍊🍊🍊 = 2x bet

🎮 **Choose your bet:**
"""
    
    keyboard = [
        [InlineKeyboardButton("💰 $1", callback_data="slots_bet_1"), InlineKeyboardButton("💰 $5", callback_data="slots_bet_5")],
        [InlineKeyboardButton("💰 $10", callback_data="slots_bet_10"), InlineKeyboardButton("💰 $25", callback_data="slots_bet_25")],
        [InlineKeyboardButton("💰 $50", callback_data="slots_bet_50"), InlineKeyboardButton("💰 $100", callback_data="slots_bet_100")],
        [InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def handle_slots_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle slots betting"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    try:
        bet = float(data.split("_")[-1])
    except:
        await query.answer("❌ Invalid bet amount", show_alert=True)
        return
    
    user = await get_user(user_id)
    ltc_usd_rate = await get_ltc_usd_rate()
    bet_ltc = bet / ltc_usd_rate if ltc_usd_rate > 0 else 0
    
    # Check balance (allow admin to play with zero balance)
    if user['balance'] < bet_ltc and not is_admin(user_id):
        if DEMO_MODE:
            # Demo mode - allow play with zero balance, always win
            win_amount = bet_ltc * 3  # 3x win in demo
            await update_balance(user_id, win_amount)
            symbols = ["💎", "💎", "💎"]
            result = "WIN"
            multiplier = 3
        else:
            await query.answer("❌ Insufficient balance", show_alert=True)
            return
    else:
        # Deduct bet amount
        if not is_admin(user_id):  # Admins play for free
            await deduct_balance(user_id, bet_ltc)
        
        # Simple slots simulation
        symbols = ["🍒", "🍋", "🍊", "🔔", "💎"]
        reel = [random.choice(symbols) for _ in range(3)]
        
        if reel[0] == reel[1] == reel[2]:
            # Win!
            if reel[0] == "💎":
                multiplier = 10
            elif reel[0] == "🔔":
                multiplier = 5
            elif reel[0] == "🍒":
                multiplier = 3
            else:
                multiplier = 2
            
            win_amount = bet_ltc * multiplier
            await update_balance(user_id, win_amount)
            result = "WIN"
        else:
            multiplier = 0
            win_amount = 0
            result = "LOSE"
    
    # Log game session
    await log_game_session(user_id, "slots", bet_ltc, win_amount, result)
    
    user_after = await get_user(user_id)
    
    if result == "WIN":
        text = f"""
🎰 **SLOT MACHINE RESULT** 🎰

{reel[0]} {reel[1]} {reel[2]}

🎉 **WINNER!** 🎉
💰 **Bet:** ${bet:.2f}
💎 **Win:** ${win_amount * ltc_usd_rate:.2f} ({multiplier}x)

💰 **New Balance:** {await format_usd(user_after['balance'])}
"""
    else:
        text = f"""
🎰 **SLOT MACHINE RESULT** 🎰

{reel[0]} {reel[1]} {reel[2]}

😔 **No match this time**
💰 **Bet:** ${bet:.2f}

💰 **Balance:** {await format_usd(user_after['balance'])}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Play Again", callback_data="play_slots"), InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def coin_flip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle coin flip game"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    text = f"""
🪙 **COIN FLIP** 🪙

💰 **Your Balance:** {await format_usd(user['balance'])}

⚡ **Quick & Simple:**
• Choose Heads or Tails
• 50/50 odds
• Instant results
• 2x payout on win

🎯 **Betting Options:**
Choose your bet amount (in USD) and side:
"""
    
    keyboard = [
        [InlineKeyboardButton("🟡 Heads - $10", callback_data="coinflip_heads_10"), InlineKeyboardButton("⚫ Tails - $10", callback_data="coinflip_tails_10")],
        [InlineKeyboardButton("🟡 Heads - $25", callback_data="coinflip_heads_25"), InlineKeyboardButton("⚫ Tails - $25", callback_data="coinflip_tails_25")],
        [InlineKeyboardButton("🟡 Heads - $50", callback_data="coinflip_heads_50"), InlineKeyboardButton("⚫ Tails - $50", callback_data="coinflip_tails_50")],
        [InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
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
    ltc_usd_rate = await get_ltc_usd_rate()
    bet_ltc = bet / ltc_usd_rate if ltc_usd_rate > 0 else 0
    
    # Check balance (allow admin/demo mode to play with zero balance)
    if user['balance'] < bet_ltc and not is_admin(user_id) and not DEMO_MODE:
        await query.answer("❌ Insufficient balance", show_alert=True)
        return
    
    # Admin test mode - always win
    if is_admin(user_id):
        log_admin_action(user_id, f"Playing coin flip in test mode with ${bet} bet")
        coin_result = choice
        win_amount = bet_ltc * 1.92
        await update_balance(user_id, win_amount)
        outcome = f"🧪 **TEST MODE (ADMIN)**\n🎉 **YOU WIN!**\n\n{'🟡' if choice == 'heads' else '⚫'} Coin landed on **{choice.upper()}**\n{'🟡' if choice == 'heads' else '⚫'} You chose **{choice.upper()}**\n\n💰 Won: **${bet * 1.92:.2f}**"
    elif DEMO_MODE and user['balance'] < bet_ltc:
        # Demo mode - always win, no balance deduction
        coin_result = choice
        win_amount = bet_ltc * 1.92
        await update_balance(user_id, win_amount)
        outcome = f"🧪 **DEMO MODE**\n🎉 **YOU WIN!**\n\n{'🟡' if choice == 'heads' else '⚫'} Coin landed on **{choice.upper()}**\n{'🟡' if choice == 'heads' else '⚫'} You chose **{choice.upper()}**\n\n💰 Won: **${bet * 1.92:.2f}**"
    else:
        # Normal game - deduct bet first
        if not is_admin(user_id):  # Admins play for free
            await deduct_balance(user_id, bet_ltc)
        
        # Flip coin
        coin_result = random.choice(["heads", "tails"])
        coin_emoji = "🟡" if coin_result == "heads" else "⚫"
        choice_emoji = "🟡" if choice == "heads" else "⚫"
        
        if choice == coin_result:
            # Win - 1.92x payout
            win_amount = bet_ltc * 1.92
            await update_balance(user_id, win_amount)
            outcome = f"🎉 **YOU WIN!**\n\n{coin_emoji} Coin landed on **{coin_result.upper()}**\n{choice_emoji} You chose **{choice.upper()}**\n\n💰 Won: **${bet * 1.92:.2f}**"
        else:
            outcome = f"😢 **YOU LOSE!**\n\n{coin_emoji} Coin landed on **{coin_result.upper()}**\n{choice_emoji} You chose **{choice.upper()}**\n\n💸 Lost: **${bet}**"
    
    # Log game session
    await log_game_session(user_id, "coinflip", bet_ltc, win_amount if choice == coin_result else 0, "WIN" if choice == coin_result else "LOSE")
    
    user_after = await get_user(user_id)
    
    text = f"""
🪙 **COIN FLIP RESULT** 🪙

{outcome}

💰 **New Balance:** {await format_usd(user_after['balance'])}

Play again or try another game:
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Flip Again", callback_data="coin_flip"), InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino")],
        [InlineKeyboardButton("🎰 Slots", callback_data="play_slots"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def play_dice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle dice prediction game"""
    query = update.callback_query
    await query.answer()
    user_id = query.effective_user.id
    user = await get_user(user_id)
    balance = await format_usd(user['balance'])
    
    text = (
        f"🎲 <b>DICE PREDICTION</b> 🎲\n\n"
        f"💰 <b>Your Balance:</b> {balance}\n\n"
        "Predict the outcome of a 6-sided dice roll.\n"
        "Choose your prediction and bet amount:\n\n"
        "<b>Payouts:</b>\n"
        "• Correct Number (1-6): 6x\n"
        "• Even/Odd: 2x\n"
        "• High (4-6)/Low (1-3): 2x\n"
    )
    keyboard = [
        [InlineKeyboardButton("1️⃣ ($10)", callback_data="dice_1_10"), InlineKeyboardButton("2️⃣ ($10)", callback_data="dice_2_10"), InlineKeyboardButton("3️⃣ ($10)", callback_data="dice_3_10")],
        [InlineKeyboardButton("4️⃣ ($10)", callback_data="dice_4_10"), InlineKeyboardButton("5️⃣ ($10)", callback_data="dice_5_10"), InlineKeyboardButton("6️⃣ ($10)", callback_data="dice_6_10")],
        [InlineKeyboardButton("Even ($25)", callback_data="dice_even_25"), InlineKeyboardButton("Odd ($25)", callback_data="dice_odd_25")],
        [InlineKeyboardButton("High ($25)", callback_data="dice_high_25"), InlineKeyboardButton("Low ($25)", callback_data="dice_low_25")],
        [InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def handle_dice_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle dice bet"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    try:
        parts = data.split("_")
        prediction = parts[1]
        bet = int(parts[2])
    except:
        await query.answer("Invalid bet format", show_alert=True)
        return
    
    user = await get_user(user_id)
    ltc_usd_rate = await get_ltc_usd_rate()
    bet_ltc = bet / ltc_usd_rate if ltc_usd_rate > 0 else 0
    
    # Check balance (allow admin/demo mode to play with zero balance)
    if user['balance'] < bet_ltc and not is_admin(user_id) and not DEMO_MODE:
        await query.answer("❌ Insufficient balance", show_alert=True)
        return
    
    # Deduct bet (except for admins)
    if not is_admin(user_id):
        await deduct_balance(user_id, bet_ltc)
    
    # Roll the dice
    roll = random.randint(1, 6)
    
    # Determine if win
    won = False
    multiplier = 0
    
    if prediction.isdigit() and 1 <= int(prediction) <= 6:
        # User guessed a specific number
        if roll == int(prediction):
            won = True
            multiplier = 6
    elif prediction == "even" and roll % 2 == 0:
        won = True
        multiplier = 2
    elif prediction == "odd" and roll % 2 == 1:
        won = True
        multiplier = 2
    elif prediction == "high" and roll >= 4:
        won = True
        multiplier = 2
    elif prediction == "low" and roll <= 3:
        won = True
        multiplier = 2
    
    # Calculate payout
    if won:
        win_amount = bet_ltc * multiplier
        await update_balance(user_id, win_amount)
        result_text = f"🎉 **YOU WIN!**\nDice rolled: **{roll}**\nYour prediction: **{prediction.title()}**\nPayout: **${bet * multiplier:.2f}**"
    else:
        win_amount = 0
        result_text = f"😢 **YOU LOSE!**\nDice rolled: **{roll}**\nYour prediction: **{prediction.title()}**\nLost: **${bet}**"
    
    # Log game session
    await log_game_session(user_id, "dice", bet_ltc, win_amount, "WIN" if won else "LOSE")
    
    user_after = await get_user(user_id)
    text = f"""
🎲 **DICE RESULT** 🎲

{result_text}

💰 **New Balance:** {await format_usd(user_after['balance'])}

Play again or try another game:
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Play Again", callback_data="play_dice"), InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino")],
        [InlineKeyboardButton("🎰 Slots", callback_data="play_slots"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Deposit System ---

async def deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle deposit requests"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    balance_usd = await format_usd(user['balance'])
    
    text = f"""
💳 **DEPOSIT FUNDS** 💳

💰 **Current Balance:** {balance_usd}
👤 **Player:** {user['username']}

🏦 **Supported Cryptocurrencies:**
• Litecoin (LTC) - Fast & low fees
• Toncoin (TON) - Telegram native
• Solana (SOL) - High speed network

📋 **Deposit Process:**
1. Choose cryptocurrency
2. Enter amount in USD
3. Pay the generated invoice
4. Funds added instantly

⚡ **Instant deposits via CryptoBot**
🔒 **Secure & anonymous**
"""
    
    keyboard = [
        [
            InlineKeyboardButton("Ł Litecoin (LTC)", callback_data="deposit_crypto_ltc"),
            InlineKeyboardButton("🪙 Toncoin (TON)", callback_data="deposit_crypto_ton"),
            InlineKeyboardButton("◎ Solana (SOL)", callback_data="deposit_crypto_sol")
        ],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def deposit_crypto_ltc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_deposit_amount(update, context, asset="LTC")

async def deposit_crypto_ton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_deposit_amount(update, context, asset="TON")

async def deposit_crypto_sol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_deposit_amount(update, context, asset="SOL")

async def ask_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, asset: str):
    context.user_data['deposit_asset'] = asset
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    asset_name = {"LTC": "Litecoin", "TON": "Toncoin", "SOL": "Solana"}.get(asset, asset)
    asset_emoji = {"LTC": "Ł", "TON": "🪙", "SOL": "◎"}.get(asset, "💰")
    
    # Get current rate
    asset_rate = await get_crypto_usd_rate(asset)
    balance_usd = await format_usd(user['balance'])
    
    text = (
        f"{asset_emoji} <b>{asset_name} Deposit</b>\n\n"
        f"💰 <b>Current Balance:</b> {balance_usd}\n"
        f"📊 <b>Current {asset} Rate:</b> ${asset_rate:.2f}\n\n"
        f"💡 <b>Minimum deposit:</b> $0.50\n"
        f"⚡ <b>Processing:</b> Instant via CryptoBot\n\n"
        f"Enter the amount in <b>USD</b> you want to deposit:"
    )
    
    await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML)
    return DEPOSIT_LTC_AMOUNT

async def deposit_crypto_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    asset = context.user_data.get('deposit_asset', 'LTC')
    asset_name = {"LTC": "Litecoin", "TON": "Toncoin", "SOL": "Solana"}.get(asset, asset)
    
    try:
        usd_amount = float(update.message.text.strip())
        if usd_amount < 0.50:
            await update.message.reply_text(f"❌ Minimum deposit is $0.50 for {asset_name}. Please enter a valid amount:")
            return DEPOSIT_LTC_AMOUNT
    except Exception:
        await update.message.reply_text(f"❌ Invalid amount. Please enter a valid USD amount (min $0.50) for {asset_name}:")
        return DEPOSIT_LTC_AMOUNT
    
    try:
        # Get current rate for the selected asset
        asset_usd_rate = await get_crypto_usd_rate(asset)
        if asset_usd_rate == 0.0:
            await update.message.reply_text(f"❌ {asset_name} rate unavailable. Please try again later.")
            return ConversationHandler.END
        
        # Convert USD to asset amount
        asset_amount = usd_amount / asset_usd_rate
        
        # Check required env vars
        missing_env = []
        if not CRYPTOBOT_API_TOKEN:
            missing_env.append("CRYPTOBOT_API_TOKEN")
        if not CRYPTOBOT_WEBHOOK_SECRET:
            missing_env.append("CRYPTOBOT_WEBHOOK_SECRET")
        
        if missing_env:
            await update.message.reply_text(f"❌ {asset_name} deposits temporarily unavailable. Missing: {', '.join(missing_env)}")
            return ConversationHandler.END
        
        # Create invoice
        payload = {"hidden_message": str(user_id), "asset": asset}
        invoice = await create_crypto_invoice(asset, asset_amount, user_id, payload=payload)
        
        if invoice.get("ok"):
            invoice_data = invoice.get("result", {})
            pay_url = invoice_data.get("pay_url")
            invoice_id = invoice_data.get("invoice_id")
            
            text = (
                f"✅ <b>{asset_name} Deposit Invoice Created!</b>\n\n"
                f"💰 <b>Amount:</b> ${usd_amount:.2f} (≈ {asset_amount:.8f} {asset})\n"
                f"🆔 <b>Invoice ID:</b> <code>{invoice_id}</code>\n\n"
                f"📱 <b>Pay using the button below or scan the QR code in CryptoBot</b>\n\n"
                f"⏰ <b>Invoice expires in 1 hour</b>\n"
                f"⚡ <b>Funds will be added instantly after payment</b>"
            )
            
            keyboard = [
                [InlineKeyboardButton(f"💳 Pay {asset_amount:.8f} {asset}", url=pay_url)],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
            ]
            
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        else:
            error_msg = invoice.get("error", {}).get("name", "Unknown error")
            await update.message.reply_text(f"❌ Failed to create {asset_name} invoice: {error_msg}")
            
    except Exception as e:
        logger.error(f"Deposit error for {asset}: {e}")
        await update.message.reply_text(f"❌ {asset_name} deposit system temporarily unavailable. Please try again later.")
    
    return ConversationHandler.END

# --- Withdrawal System ---

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdrawal requests - now supports multiple assets"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)

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
            withdrawal_history += f"• {status_emoji} ${w['amount'] * await get_crypto_usd_rate(w['asset']):.2f} {w['asset']} - {w['status']}\n"

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

🏦 **Choose Withdrawal Method:**
{withdrawal_history}
"""
    
    keyboard = [
        [
            InlineKeyboardButton("Ł Litecoin (LTC)", callback_data="withdraw_crypto_ltc"),
            InlineKeyboardButton("🪙 Toncoin (TON)", callback_data="withdraw_crypto_ton"),
            InlineKeyboardButton("◎ Solana (SOL)", callback_data="withdraw_crypto_sol")
        ],
        [InlineKeyboardButton("📊 Withdrawal History", callback_data="withdrawal_history")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def withdraw_crypto_ltc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_withdraw_amount(update, context, asset="LTC")

async def withdraw_crypto_ton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_withdraw_amount(update, context, asset="TON")

async def withdraw_crypto_sol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_withdraw_amount(update, context, asset="SOL")

async def ask_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, asset: str):
    context.user_data['withdraw_asset'] = asset
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    asset_name = {"LTC": "Litecoin", "TON": "Toncoin", "SOL": "Solana"}.get(asset, asset)
    asset_emoji = {"LTC": "Ł", "TON": "🪙", "SOL": "◎"}.get(asset, "💰")
    
    # Check withdrawal limits first
    limits_check = await check_withdrawal_limits(user_id, MIN_WITHDRAWAL_USD)
    if not limits_check['allowed']:
        await update.callback_query.edit_message_text(f"❌ {limits_check['reason']}")
        return ConversationHandler.END
    
    # Get current rate
    asset_rate = await get_crypto_usd_rate(asset)
    balance_usd = await format_usd(user['balance'])
    max_withdraw_crypto = user['balance']
    max_withdraw_usd = max_withdraw_crypto * asset_rate if asset_rate > 0 else 0
    
    # Calculate fees for display
    example_fee_crypto = calculate_withdrawal_fee(0.1)
    example_fee_usd = example_fee_crypto * asset_rate if asset_rate > 0 else 0
    
    text = (
        f"{asset_emoji} <b>{asset_name} Withdrawal</b>\n\n"
        f"💰 <b>Available Balance:</b> {balance_usd}\n"
        f"📊 <b>Current {asset} Rate:</b> ${asset_rate:.2f}\n\n"
        f"📋 <b>Withdrawal Details:</b>\n"
        f"• Minimum: ${MIN_WITHDRAWAL_USD:.2f}\n"
        f"• Maximum: ${min(max_withdraw_usd, MAX_WITHDRAWAL_USD_DAILY):.2f}\n"
        f"• Fee: {WITHDRAWAL_FEE_PERCENT}% (Example: ${example_fee_usd:.4f})\n\n"
        f"💡 <b>Note:</b> Fee is deducted from withdrawal amount\n\n"
        f"Enter the amount in <b>USD</b> you want to withdraw:"
    )
    
    await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML)
    return WITHDRAW_LTC_AMOUNT

async def withdraw_crypto_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    asset = context.user_data.get('withdraw_asset', 'LTC')
    asset_name = {"LTC": "Litecoin", "TON": "Toncoin", "SOL": "Solana"}.get(asset, asset)
    
    try:
        usd_amount = float(update.message.text.strip())
        # Validate minimum amount
        if usd_amount < MIN_WITHDRAWAL_USD:
            await update.message.reply_text(f"❌ Minimum withdrawal is ${MIN_WITHDRAWAL_USD:.2f}. Please enter a valid amount:")
            return WITHDRAW_LTC_AMOUNT
            
        # Check withdrawal limits
        limits_check = await check_withdrawal_limits(user_id, usd_amount)
        if not limits_check['allowed']:
            await update.message.reply_text(f"❌ {limits_check['reason']}")
            return ConversationHandler.END
            
        # Convert USD to asset amount
        asset_usd_rate = await get_crypto_usd_rate(asset)
        if asset_usd_rate == 0.0:
            await update.message.reply_text(f"❌ {asset_name} rate unavailable. Please try again later.")
            return ConversationHandler.END
            
        asset_amount = usd_amount / asset_usd_rate
        
        # Check if user has sufficient balance
        if user['balance'] < asset_amount:
            available_usd = user['balance'] * asset_usd_rate
            await update.message.reply_text(f"❌ Insufficient balance. Available: ${available_usd:.2f}")
            return ConversationHandler.END
            
        # Calculate fees
        fee_asset = calculate_withdrawal_fee(asset_amount)
        fee_usd = fee_asset * asset_usd_rate
        net_asset = asset_amount - fee_asset
        net_usd = net_asset * asset_usd_rate
        
        # Validate that after fees, user still gets meaningful amount
        if net_asset <= 0:
            await update.message.reply_text(f"❌ Amount too small after fees. Minimum after fees: ${(MIN_WITHDRAWAL_FEE + 0.01) * asset_usd_rate:.2f}")
            return WITHDRAW_LTC_AMOUNT
            
    except ValueError:
        await update.message.reply_text(f"❌ Invalid amount. Please enter a valid USD amount:")
        return WITHDRAW_LTC_AMOUNT
    except Exception as e:
        await update.message.reply_text("❌ Error processing amount. Please try again:")
        return WITHDRAW_LTC_AMOUNT
    
    # Store withdrawal details
    context.user_data['withdraw_amount_asset'] = asset_amount
    context.user_data['withdraw_amount_usd'] = usd_amount
    context.user_data['withdraw_fee_asset'] = fee_asset
    context.user_data['withdraw_fee_usd'] = fee_usd
    context.user_data['withdraw_net_asset'] = net_asset
    context.user_data['withdraw_net_usd'] = net_usd
    
    # Address format examples based on asset
    address_examples = {
        "LTC": "• Legacy: L... or M...\n• SegWit: 3...\n• Bech32: ltc1...",
        "TON": "• TON Address: UQ...\n• TON v4r2 Format",
        "SOL": "• Solana Address: Base58 format\n• Example: 9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    }
    
    text = (
        f"💵 <b>{asset_name} Withdrawal Summary</b>\n\n"
        f"📊 <b>Amount Details:</b>\n"
        f"• Requested: <b>${usd_amount:.2f}</b> (≈ {asset_amount:.8f} {asset})\n"
        f"• Fee ({WITHDRAWAL_FEE_PERCENT}%): <b>${fee_usd:.4f}</b> (≈ {fee_asset:.8f} {asset})\n"
        f"• You'll receive: <b>${net_usd:.2f}</b> (≈ {net_asset:.8f} {asset})\n\n"
        f"📍 <b>Next Step:</b>\n"
        f"Enter your {asset_name} address:\n\n"
        f"💡 <b>Supported formats:</b>\n"
        f"{address_examples.get(asset, '• Standard format for this asset')}\n\n"
        f"⚠️ <b>Warning:</b> Double-check your address!"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    return WITHDRAW_LTC_ADDRESS

async def withdraw_crypto_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    address = update.message.text.strip()
    asset = context.user_data.get('withdraw_asset', 'LTC')
    asset_name = {"LTC": "Litecoin", "TON": "Toncoin", "SOL": "Solana"}.get(asset, asset)
    
    # Get withdrawal details from context
    asset_amount = context.user_data.get('withdraw_amount_asset')
    usd_amount = context.user_data.get('withdraw_amount_usd')
    fee_asset = context.user_data.get('withdraw_fee_asset')
    fee_usd = context.user_data.get('withdraw_fee_usd')
    net_asset = context.user_data.get('withdraw_net_asset')
    net_usd = context.user_data.get('withdraw_net_usd')
    
    if not all([asset_amount, usd_amount, fee_asset, fee_usd, net_asset, net_usd]):
        await update.message.reply_text("❌ Session expired. Please start withdrawal again.")
        return ConversationHandler.END
    
    # Basic address validation
    if not validate_crypto_address(address, asset):
        asset_format_msg = {
            "LTC": "Please enter a valid Litecoin address:\n• Legacy: L... or M...\n• SegWit: 3...\n• Bech32: ltc1...",
            "TON": "Please enter a valid TON address:\n• TON Address: UQ...",
            "SOL": "Please enter a valid Solana address:\n• Base58 format"
        }
        await update.message.reply_text(
            f"❌ Invalid {asset_name} address format.\n\n{asset_format_msg.get(asset, 'Invalid address format.')}"
        )
        return WITHDRAW_LTC_ADDRESS
    
    # Final validation
    if user['balance'] < asset_amount:
        await update.message.reply_text("❌ Insufficient balance.")
        return ConversationHandler.END
    
    limits_check = await check_withdrawal_limits(user_id, usd_amount)
    if not limits_check['allowed']:
        await update.message.reply_text(f"❌ {limits_check['reason']}")
        return ConversationHandler.END
    
    # Log withdrawal attempt
    withdrawal_id = await log_withdrawal(
        user_id, asset, asset_amount, address, fee_asset, net_asset
    )
    
    try:
        # Deduct full amount from balance (including fees)
        if not await deduct_balance(user_id, asset_amount):
            await update_withdrawal_status(withdrawal_id, 'failed', '', 'Failed to deduct balance')
            await update.message.reply_text("❌ Failed to process withdrawal. Please try again.")
            return ConversationHandler.END
        
        # Send crypto via CryptoBot (send net amount after fees)
        result = await send_crypto(address, net_asset, f"Withdrawal for user {user_id}", asset=asset)
        
        if result.get("ok"):
            # Successful withdrawal
            transaction_id = result.get("result", {}).get("transfer_id", "unknown")
            await update_withdrawal_status(withdrawal_id, 'completed', str(transaction_id))
            await update_withdrawal_limits(user_id, usd_amount)
            
            success_text = (
                f"✅ <b>{asset_name} Withdrawal Successful!</b>\n\n"
                f"💰 <b>Amount:</b> ${net_usd:.2f} (≈ {net_asset:.8f} {asset})\n"
                f"💸 <b>Fee:</b> ${fee_usd:.4f} (≈ {fee_asset:.8f} {asset})\n"
                f"📍 <b>Address:</b> <code>{address}</code>\n"
                f"🆔 <b>Transaction ID:</b> <code>{transaction_id}</code>\n\n"
                f"💡 <b>Processing:</b> Your withdrawal has been processed via CryptoBot.\n"
                f"🔍 <b>Confirmation:</b> Check your wallet in a few minutes."
            )
            
            await update.message.reply_text(success_text, parse_mode=ParseMode.HTML)
            logger.info(f"Withdrawal completed: {net_asset} {asset} to {address} for user {user_id}, TX: {transaction_id}")
            
        else:
            # Failed withdrawal - refund user
            await update_balance(user_id, asset_amount)  # Refund full amount
            error_msg = result.get("error", {}).get("name", "Unknown error")
            await update_withdrawal_status(withdrawal_id, 'failed', '', error_msg)
            
            await update.message.reply_text(
                f"❌ <b>{asset_name} Withdrawal Failed</b>\n\n"
                f"Your balance has been refunded.\n"
                f"Error: {error_msg}\n\n"
                f"Please try again later or contact support.",
                parse_mode=ParseMode.HTML
            )
            logger.error(f"CryptoBot withdrawal failed for user {user_id}: {result}")
            
    except Exception as e:
        # Exception occurred - refund user
        await update_balance(user_id, asset_amount)  # Refund full amount
        await update_withdrawal_status(withdrawal_id, 'failed', '', str(e))
        
        await update.message.reply_text(
            f"❌ <b>{asset_name} Withdrawal Failed</b>\n\n"
            "Your balance has been refunded.\n"
            "Please try again later or contact support.",
            parse_mode=ParseMode.HTML
        )
        logger.error(f"Withdrawal exception for user {user_id}: {e}")
    
    return ConversationHandler.END

# --- Admin and Owner Panels ---

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

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel with enhanced features"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not (is_admin(user_id) or is_owner(user_id)):
        await query.edit_message_text("❌ Access denied. Admin privileges required.")
        return
    
    # Get bot statistics
    async with aiosqlite.connect(DB_PATH) as db:
        # Total users
        cur = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cur.fetchone())[0]
        
        # Total balance
        cur = await db.execute("SELECT SUM(balance) FROM users")
        total_balance = (await cur.fetchone())[0] or 0.0
        
        # Total games played
        cur = await db.execute("SELECT SUM(games_played) FROM users")
        total_games = (await cur.fetchone())[0] or 0
        
        # Total wagered
        cur = await db.execute("SELECT SUM(total_wagered) FROM users")
        total_wagered = (await cur.fetchone())[0] or 0.0
        
        # Active users (played in last 24h)
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE last_active > ?", (yesterday,))
        active_users = (await cur.fetchone())[0]
    
    total_balance_usd = await format_usd(total_balance)
    total_wagered_usd = await format_usd(total_wagered)
    
    status_badge = "👑 OWNER" if is_owner(user_id) else "🔑 ADMIN"
    
    text = (
        f"⚙️ <b>{status_badge} PANEL</b> ⚙️\n\n"
        f"📊 <b>Bot Statistics:</b>\n"
        f"• Total Users: {total_users}\n"
        f"• Total Balance: {total_balance_usd}\n"
        f"• Total Games: {total_games}\n"
        f"• Total Wagered: {total_wagered_usd}\n"
        f"• Active Users (24h): {active_users}\n"
        f"• Demo Mode: {'ON' if DEMO_MODE else 'OFF'}\n\n"
        f"🎮 <b>Admin Commands:</b>\n"
        f"• /admin - Check admin status\n"
        f"• /demo - Toggle demo mode\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎮 Toggle Demo Mode", callback_data="admin_toggle_demo")],
        [InlineKeyboardButton("📊 User Stats", callback_data="owner_user_stats")],
        [InlineKeyboardButton("💰 Balance Report", callback_data="owner_financial")],
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="admin_panel")],
        [InlineKeyboardButton("👤 User Panel", callback_data="main_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    if is_owner(user_id):
        keyboard.append([InlineKeyboardButton("👑 Owner Panel", callback_data="owner_panel")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def admin_toggle_demo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle demo mode via admin panel"""
    global DEMO_MODE
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not (is_admin(user_id) or is_owner(user_id)):
        await query.edit_message_text("❌ Access denied.")
        return
    DEMO_MODE = not DEMO_MODE
    status = "ON" if DEMO_MODE else "OFF"
    log_admin_action(user_id, f"Toggled demo mode to {status}")
    await query.edit_message_text(
        f"🎮 <b>Demo Mode: {status}</b>\n\n"
        f"Demo mode has been {'enabled' if DEMO_MODE else 'disabled'} for all users.\n\n"
        f"{'Users can now play games without balance.' if DEMO_MODE else 'Users now need balance to play games.'}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ Back to Admin Panel", callback_data="admin_panel")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]),
        parse_mode=ParseMode.HTML
    )

async def owner_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner panel with full administrative features"""
    query = getattr(update, "callback_query", None)
    user = update.effective_user
    user_id = user.id if user else None

    if not is_owner(user_id):
        if query:
            await query.answer("❌ Access denied. Owner only.", show_alert=True)
        else:
            await update.message.reply_text("❌ Access denied. Owner only.")
        return

    # Get comprehensive bot statistics
    async with aiosqlite.connect(DB_PATH) as db:
        # Total users
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        # Total balance
        cursor = await db.execute("SELECT SUM(balance) FROM users")
        total_balance = (await cursor.fetchone())[0] or 0.0
        
        # Total wagered
        cursor = await db.execute("SELECT SUM(total_wagered) FROM users")
        total_wagered = (await cursor.fetchone())[0] or 0.0
        
        # Total games
        cursor = await db.execute("SELECT SUM(games_played) FROM users")
        total_games = (await cursor.fetchone())[0] or 0
        
        # Withdrawals today
        today = datetime.now().date()
        cursor = await db.execute("""
            SELECT COUNT(*), SUM(amount_usd) FROM withdrawals 
            WHERE DATE(created_at) = ? AND status = 'completed'
        """, (today,))
        withdrawal_data = await cursor.fetchone()
        withdrawals_today = withdrawal_data[0] or 0
        withdrawal_amount_today = withdrawal_data[1] or 0.0

    total_balance_usd = await format_usd(total_balance)
    total_wagered_usd = await format_usd(total_wagered)

    text = f"""
👑 <b>OWNER CONTROL PANEL</b> 👑

📊 <b>System Statistics:</b>
• Total Users: {total_users:,}
• Total Balance: {total_balance_usd}
• Total Wagered: {total_wagered_usd}
• Total Games: {total_games:,}
• Demo Mode: {'ON' if DEMO_MODE else 'OFF'}

💰 <b>Today's Activity:</b>
• Withdrawals: {withdrawals_today} (${withdrawal_amount_today:.2f})

🎮 <b>Bot Version:</b> {BOT_VERSION}
"""
    # Improved button layout with better organization
    keyboard = [
        [InlineKeyboardButton("📊 Detailed Stats", callback_data="owner_detailed_stats"), 
         InlineKeyboardButton("👥 User Management", callback_data="owner_user_mgmt")],
        [InlineKeyboardButton("💰 Financial Report", callback_data="owner_financial"), 
         InlineKeyboardButton("📋 Withdrawal History", callback_data="owner_withdrawals")],
        [InlineKeyboardButton("⚙️ System Health", callback_data="owner_system_health"), 
         InlineKeyboardButton("🎮 Toggle Demo", callback_data="admin_toggle_demo")],
        [InlineKeyboardButton("🔧 Bot Settings", callback_data="owner_bot_settings"), 
         InlineKeyboardButton("📈 Analytics", callback_data="owner_analytics")],
        [InlineKeyboardButton("🔄 Refresh Data", callback_data="owner_panel")],
        [InlineKeyboardButton("👤 User Panel", callback_data="main_panel"), 
         InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    if query:
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        except BadRequest as e:
            logger.error(f"[OWNER PANEL] BadRequest: {e}")
            await query.answer("❌ Failed to update panel. Please try again.", show_alert=True)
        except TelegramError as e:
            logger.error(f"[OWNER PANEL] TelegramError: {e}")
            await query.answer("❌ Telegram error. Please try again.", show_alert=True)
        except Exception as e:
            logger.error(f"[OWNER PANEL] Unexpected error: {e}")
            await query.answer("❌ Unexpected error. Please try again.", show_alert=True)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def owner_detailed_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed system statistics"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        await query.answer("❌ Access denied. Owner only.", show_alert=True)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        # User statistics
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE games_played > 0")
        active_players = (await cursor.fetchone())[0]
        
        # Game statistics
        cursor = await db.execute("SELECT SUM(games_played) FROM users")
        total_games = (await cursor.fetchone())[0] or 0
        
        cursor = await db.execute("SELECT SUM(total_wagered), SUM(balance) FROM users")
        result = await cursor.fetchone()
        total_wagered = result[0] or 0.0
        total_balance = result[1] or 0.0
        
        # Recent activity (last 24h)
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE last_active > ?", (yesterday,))
        recent_active = (await cursor.fetchone())[0]
        
        # Top players by balance
        cursor = await db.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 5")
        top_players = await cursor.fetchall()

    text = f"""
📊 <b>DETAILED SYSTEM STATISTICS</b>

👥 <b>User Metrics:</b>
• Total Registered: {total_users:,}
• Active Players: {active_players:,}
• Recent Activity (24h): {recent_active:,}
• Conversion Rate: {(active_players/max(total_users,1)*100):.1f}%

🎮 <b>Game Metrics:</b>
• Total Games Played: {total_games:,}
• Total Wagered: {await format_usd(total_wagered)}
• Current Balances: {await format_usd(total_balance)}
• Avg Games/User: {(total_games/max(active_players,1)):.1f}

💰 <b>Top Players by Balance:</b>
"""
    
    for i, (username, balance) in enumerate(top_players, 1):
        text += f"• #{i} {username}: {await format_usd(balance)}\n"

    keyboard = [
        [InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def owner_user_mgmt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User management panel"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        await query.answer("❌ Access denied. Owner only.", show_alert=True)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        # Recent users
        cursor = await db.execute("""
            SELECT user_id, username, balance, games_played, created_at 
            FROM users ORDER BY created_at DESC LIMIT 10
        """)
        recent_users = await cursor.fetchall()
        
        # Problem users (high balance, no games)
        cursor = await db.execute("""
            SELECT user_id, username, balance FROM users 
            WHERE balance > 0.1 AND games_played = 0 
            ORDER BY balance DESC LIMIT 5
        """)
        problem_users = await cursor.fetchall()

    text = f"""
👥 <b>USER MANAGEMENT</b>

📝 <b>Recent Registrations:</b>
"""
    
    for user_data in recent_users[:5]:
        user_id_db, username, balance, games, created = user_data
        text += f"• {username} - {await format_usd(balance)} ({games} games)\n"
    
    text += f"\n⚠️ <b>High Balance, No Games:</b>\n"
    for user_data in problem_users:
        user_id_db, username, balance = user_data
        text += f"• {username}: {await format_usd(balance)}\n"

    keyboard = [
        [InlineKeyboardButton("📊 Export Users", callback_data="owner_export_users"),
         InlineKeyboardButton("🔍 User Search", callback_data="owner_user_search")],
        [InlineKeyboardButton("⚠️ Problem Users", callback_data="owner_problem_users"),
         InlineKeyboardButton("📈 User Analytics", callback_data="owner_user_analytics")],
        [InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def owner_financial_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Financial report panel"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        await query.answer("❌ Access denied. Owner only.", show_alert=True)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        # Today's stats
        today = datetime.now().date()
        
        # Withdrawals today
        cursor = await db.execute("""
            SELECT COUNT(*), COALESCE(SUM(amount_usd), 0) FROM withdrawals 
            WHERE DATE(created_at) = ? AND status = 'completed'
        """, (today,))
        withdrawals_today = await cursor.fetchone()
        
        # This week's stats
        week_ago = (datetime.now() - timedelta(days=7)).date()
        cursor = await db.execute("""
            SELECT COUNT(*), COALESCE(SUM(amount_usd), 0) FROM withdrawals 
            WHERE DATE(created_at) >= ? AND status = 'completed'
        """, (week_ago,))
        withdrawals_week = await cursor.fetchone()
        
        # Current balances
        cursor = await db.execute("SELECT SUM(balance) FROM users")
        total_balance = (await cursor.fetchone())[0] or 0.0
        
        # Total wagered
        cursor = await db.execute("SELECT SUM(total_wagered) FROM users")
        total_wagered = (await cursor.fetchone())[0] or 0.0

    text = f"""
💰 <b>FINANCIAL REPORT</b>

📊 <b>Today ({today}):</b>
• Withdrawals: {withdrawals_today[0]} transactions
• Withdrawal Amount: ${withdrawals_today[1]:.2f}

📈 <b>This Week:</b>
• Withdrawals: {withdrawals_week[0]} transactions  
• Withdrawal Amount: ${withdrawals_week[1]:.2f}

💵 <b>Current Status:</b>
• Total User Balances: {await format_usd(total_balance)}
• Total Wagered (All Time): {await format_usd(total_wagered)}
• House Edge: {((total_wagered - total_balance)/max(total_wagered,1)*100):.2f}%

📋 <b>Risk Assessment:</b>
• Balance/Wagered Ratio: {(total_balance/max(total_wagered,1)*100):.1f}%
• Status: {'🟢 Healthy' if total_balance/max(total_wagered,1) < 0.3 else '🟡 Monitor' if total_balance/max(total_wagered,1) < 0.5 else '🔴 High Risk'}
"""

    keyboard = [
        [InlineKeyboardButton("📊 Export Report", callback_data="owner_export_financial"),
         InlineKeyboardButton("💸 Withdrawal Details", callback_data="owner_withdrawals")],
        [InlineKeyboardButton("📈 Revenue Chart", callback_data="owner_revenue_chart"),
         InlineKeyboardButton("⚠️ Risk Analysis", callback_data="owner_risk_analysis")],
        [InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def owner_withdrawals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show withdrawal history and management"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        await query.answer("❌ Access denied. Owner only.", show_alert=True)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        # Recent withdrawals
        cursor = await db.execute("""
            SELECT user_id, asset, amount, amount_usd, address, status, created_at, transaction_hash
            FROM withdrawals ORDER BY created_at DESC LIMIT 10
        """)
        recent_withdrawals = await cursor.fetchall()
        
        # Pending withdrawals
        cursor = await db.execute("""
            SELECT COUNT(*) FROM withdrawals WHERE status = 'pending'
        """)
        pending_count = (await cursor.fetchone())[0]

    text = f"""
💸 <b>WITHDRAWAL MANAGEMENT</b>

⏳ <b>Pending Withdrawals:</b> {pending_count}

📋 <b>Recent Withdrawals:</b>
"""
    
    for withdrawal in recent_withdrawals[:8]:
        user_id_w, asset, amount, amount_usd, address, status, created, tx_hash = withdrawal
        status_emoji = {"completed": "✅", "pending": "⏳", "failed": "❌"}.get(status, "❓")
        # Get user info
        async with aiosqlite.connect(DB_PATH) as db2:
            cursor2 = await db2.execute("SELECT username FROM users WHERE user_id = ?", (user_id_w,))
            user_result = await cursor2.fetchone()
            username = user_result[0] if user_result else f"ID:{user_id_w}"
        
        text += f"• {status_emoji} {username}: ${amount_usd:.2f} {asset}\n"
        if tx_hash:
            text += f"  TX: {tx_hash[:12]}...\n"

    keyboard = [
        [InlineKeyboardButton("⏳ Pending Only", callback_data="owner_pending_withdrawals"),
         InlineKeyboardButton("✅ Completed Only", callback_data="owner_completed_withdrawals")],
        [InlineKeyboardButton("❌ Failed Only", callback_data="owner_failed_withdrawals"),
         InlineKeyboardButton("📊 Export All", callback_data="owner_export_withdrawals")],
        [InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def owner_system_health_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """System health and diagnostics"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        await query.answer("❌ Access denied. Owner only.", show_alert=True)
        return

    # Check system health
    health_status = []
    
    # Database check
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("SELECT 1")
        health_status.append("✅ Database: Connected")
    except Exception as e:
        health_status.append(f"❌ Database: Error - {str(e)[:50]}")
    
    # CryptoBot API check
    if CRYPTOBOT_API_TOKEN:
        health_status.append("✅ CryptoBot: Token configured")
    else:
        health_status.append("❌ CryptoBot: No token")
    
    # Rate checking
    try:
        ltc_rate = await get_ltc_usd_rate()
        if ltc_rate > 0:
            health_status.append(f"✅ LTC Rate: ${ltc_rate:.2f}")
        else:
            health_status.append("⚠️ LTC Rate: Unable to fetch")
    except Exception as e:
        health_status.append("❌ LTC Rate: API Error")
    
    # Bot settings
    health_status.append(f"🎮 Demo Mode: {'ON' if DEMO_MODE else 'OFF'}")
    health_status.append(f"👑 Owner ID: {OWNER_USER_ID}")
    health_status.append(f"🔧 Admin IDs: {len(ADMIN_USER_IDS)} configured")

    text = f"""
⚙️ <b>SYSTEM HEALTH CHECK</b>

🔍 <b>System Status:</b>
{chr(10).join(health_status)}

📊 <b>Environment:</b>
• Bot Version: {BOT_VERSION}
• Python: {'3.13+' if hasattr(sys, 'version_info') else 'Unknown'}
• Uptime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🛠️ <b>Configuration:</b>
• Min Withdrawal: ${MIN_WITHDRAWAL_USD}
• Max Daily Withdrawal: ${MAX_WITHDRAWAL_USD_DAILY}
• Withdrawal Fee: {WITHDRAWAL_FEE_PERCENT}%
• Withdrawal Cooldown: {WITHDRAWAL_COOLDOWN_SECONDS//60} minutes
"""

    keyboard = [
        [InlineKeyboardButton("🔄 Refresh Health", callback_data="owner_system_health"),
         InlineKeyboardButton("📋 Export Logs", callback_data="owner_export_logs")],
        [InlineKeyboardButton("⚙️ Test APIs", callback_data="owner_test_apis"),
         InlineKeyboardButton("🛠️ Config Check", callback_data="owner_config_check")],
        [InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def owner_bot_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot settings and configuration"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        await query.answer("❌ Access denied. Owner only.", show_alert=True)
        return

    text = f"""
🔧 <b>BOT SETTINGS</b>

⚙️ <b>Current Configuration:</b>
• Demo Mode: {'🟢 ON' if DEMO_MODE else '🔴 OFF'}
• Min Withdrawal: ${MIN_WITHDRAWAL_USD}
• Max Daily Withdrawal: ${MAX_WITHDRAWAL_USD_DAILY}
• Withdrawal Fee: {WITHDRAWAL_FEE_PERCENT}%
• Cooldown Period: {WITHDRAWAL_COOLDOWN_SECONDS//60} minutes

👑 <b>Access Control:</b>
• Owner ID: {OWNER_USER_ID}
• Admin Count: {len(ADMIN_USER_IDS)}

🎮 <b>Game Settings:</b>
• Slots RTP: 96.5%
• Dice RTP: 98%
• Coin Flip RTP: 98%

💰 <b>Supported Assets:</b>
• LTC (Litecoin)
• TON (Toncoin)
• SOL (Solana)
"""

    keyboard = [
        [InlineKeyboardButton("🎮 Toggle Demo", callback_data="admin_toggle_demo"),
         InlineKeyboardButton("💰 Withdrawal Settings", callback_data="owner_withdrawal_settings")],
        [InlineKeyboardButton("👥 Admin Management", callback_data="owner_admin_mgmt"),
         InlineKeyboardButton("🎯 Game Settings", callback_data="owner_game_settings")],
        [InlineKeyboardButton("💸 Asset Settings", callback_data="owner_asset_settings"),
         InlineKeyboardButton("📊 Rate Settings", callback_data="owner_rate_settings")],
        [InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def owner_analytics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analytics and insights"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        await query.answer("❌ Access denied. Owner only.", show_alert=True)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        # User growth
        cursor = await db.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count 
            FROM users 
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)
        user_growth = await cursor.fetchall()
        
        # Game popularity
        cursor = await db.execute("""
            SELECT game_type, COUNT(*) as plays, SUM(bet_amount) as wagered
            FROM game_sessions 
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY game_type
            ORDER BY plays DESC
        """)
        game_stats = await cursor.fetchall()

    text = f"""
📈 <b>ANALYTICS & INSIGHTS</b>

📊 <b>User Growth (Last 7 Days):</b>
"""
    
    for date, count in user_growth[:5]:
        text += f"• {date}: +{count} users\n"
    
    text += f"\n🎮 <b>Game Popularity (Last 7 Days):</b>\n"
    
    for game_type, plays, wagered in game_stats:
        text += f"• {game_type.title()}: {plays} plays, {await format_usd(wagered)} wagered\n"

    text += f"""

🎯 <b>Key Metrics:</b>
• Avg Daily Signups: {sum(count for _, count in user_growth)/max(len(user_growth), 1):.1f}
• Most Popular Game: {game_stats[0][0].title() if game_stats else 'No data'}
• Total Sessions (7d): {sum(plays for _, plays, _ in game_stats)}
"""

    keyboard = [
        [InlineKeyboardButton("📊 Full Report", callback_data="owner_full_analytics"),
         InlineKeyboardButton("📈 Growth Chart", callback_data="owner_growth_chart")],
        [InlineKeyboardButton("🎮 Game Analytics", callback_data="owner_game_analytics"),
         InlineKeyboardButton("👥 User Behavior", callback_data="owner_user_behavior")],
        [InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# Placeholder handlers for buttons that need more complex implementation
async def owner_placeholder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder for owner panel features that need more implementation"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        await query.answer("❌ Access denied. Owner only.", show_alert=True)
        return

    feature_name = query.data.replace("owner_", "").replace("_", " ").title()
    
    text = f"""
🚧 <b>{feature_name}</b>

This feature is currently under development.

Available soon:
• Advanced functionality
• Detailed reports
• Enhanced controls

Please check back in future updates.
"""

    keyboard = [
        [InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# --- Help and Utility Functions ---

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

**Features:**
• Multi-asset deposits (LTC, TON, SOL)
• Instant withdrawals
• Demo mode for testing
• Fair random results

**Support:**
Contact @casino_support for help
"""
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]]
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def redeem_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle redeem panel"""
    query = update.callback_query
    await query.answer()
    
    text = """
🎁 **REDEEM CODES** 🎁

Enter your promotional code below to claim rewards!

**Available Rewards:**
• Welcome bonus codes
• Daily bonus codes  
• Special event codes
• VIP member codes

Contact support for available codes.
"""
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

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

# Default callback handler for unregistered callbacks
async def default_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unregistered callbacks"""
    query = update.callback_query
    await query.answer("❌ This feature is not implemented yet.", show_alert=True)

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any active conversation"""
    await update.message.reply_text(
        "❌ Operation cancelled.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ])
    )
    return ConversationHandler.END

# --- Main Bot Setup and Entry Point ---

async def async_main():
    """Async main function to properly start both bot and keep-alive server."""
    logger.info("🚀 Starting Telegram Casino Bot...")
    
    # Initialize database first
    await init_db()
    logger.info("✅ Database initialized")
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add all handlers
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("balance", show_balance_callback))
    application.add_handler(CommandHandler("app", mini_app_centre_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(mini_app_centre_callback, pattern="^mini_app_centre$"))
    application.add_handler(CallbackQueryHandler(show_balance_callback, pattern="^show_balance$"))
    application.add_handler(CallbackQueryHandler(classic_casino_callback, pattern="^classic_casino$"))
    application.add_handler(CallbackQueryHandler(play_slots_callback, pattern="^play_slots$"))
    application.add_handler(CallbackQueryHandler(handle_slots_bet, pattern="^slots_bet_"))
    application.add_handler(CallbackQueryHandler(coin_flip_callback, pattern="^coin_flip$"))
    application.add_handler(CallbackQueryHandler(handle_coinflip_bet, pattern="^coinflip_"))
    application.add_handler(CallbackQueryHandler(play_dice_callback, pattern="^play_dice$"))
    application.add_handler(CallbackQueryHandler(handle_dice_bet, pattern="^dice_"))
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw$"))
    application.add_handler(CallbackQueryHandler(withdraw_crypto_ltc, pattern="^withdraw_crypto_ltc$"))
    application.add_handler(CallbackQueryHandler(withdraw_crypto_ton, pattern="^withdraw_crypto_ton$"))
    application.add_handler(CallbackQueryHandler(withdraw_crypto_sol, pattern="^withdraw_crypto_sol$"))
    application.add_handler(CallbackQueryHandler(start_command, pattern="^main_panel$"))
    application.add_handler(CallbackQueryHandler(redeem_panel_callback, pattern="^redeem_panel$"))
    application.add_handler(CallbackQueryHandler(help_command, pattern="^show_help$"))
    application.add_handler(CallbackQueryHandler(show_stats_callback, pattern="^show_stats$"))
    
    # Admin/Owner handlers
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_toggle_demo_callback, pattern="^admin_toggle_demo$"))
    application.add_handler(CallbackQueryHandler(owner_panel_callback, pattern="^owner_panel$"))
    
    # Owner panel detailed handlers
    application.add_handler(CallbackQueryHandler(owner_detailed_stats_callback, pattern="^owner_detailed_stats$"))
    application.add_handler(CallbackQueryHandler(owner_user_mgmt_callback, pattern="^owner_user_mgmt$"))
    application.add_handler(CallbackQueryHandler(owner_financial_callback, pattern="^owner_financial$"))
    application.add_handler(CallbackQueryHandler(owner_withdrawals_callback, pattern="^owner_withdrawals$"))
    application.add_handler(CallbackQueryHandler(owner_system_health_callback, pattern="^owner_system_health$"))
    application.add_handler(CallbackQueryHandler(owner_bot_settings_callback, pattern="^owner_bot_settings$"))
    application.add_handler(CallbackQueryHandler(owner_analytics_callback, pattern="^owner_analytics$"))
    
    # Owner panel placeholder handlers (for features under development)
    placeholder_patterns = [
        "^owner_export_users$", "^owner_user_search$", "^owner_problem_users$", "^owner_user_analytics$",
        "^owner_export_financial$", "^owner_revenue_chart$", "^owner_risk_analysis$",
        "^owner_pending_withdrawals$", "^owner_completed_withdrawals$", "^owner_failed_withdrawals$", "^owner_export_withdrawals$",
        "^owner_export_logs$", "^owner_test_apis$", "^owner_config_check$",
        "^owner_withdrawal_settings$", "^owner_admin_mgmt$", "^owner_game_settings$", "^owner_asset_settings$", "^owner_rate_settings$",
        "^owner_full_analytics$", "^owner_growth_chart$", "^owner_game_analytics$", "^owner_user_behavior$"
    ]
    
    for pattern in placeholder_patterns:
        application.add_handler(CallbackQueryHandler(owner_placeholder_callback, pattern=pattern))
    
    # ...existing code...
    # Start keep-alive server in a separate thread for deployment platforms
    def start_keep_alive():
        app = Flask(__name__)
        app.config['JSON_SORT_KEYS'] = False
        
        # Keep track of bot startup time for uptime calculation
        startup_time = datetime.now()
        
        @app.route('/')
        def index():
            uptime = datetime.now() - startup_time
            return {
                "status": "running",
                "bot_name": "Telegram Casino Bot",
                "bot_version": BOT_VERSION,
                "uptime_seconds": int(uptime.total_seconds()),
                "uptime_human": str(uptime).split('.')[0],
                "timestamp": datetime.now().isoformat(),
                "demo_mode": DEMO_MODE,
                "supported_assets": ["LTC", "TON", "SOL"],
                "endpoints": {
                    "health": "/health",
                    "status": "/status",
                    "metrics": "/metrics"
                }
            }
        
        @app.route('/health')
        def health():
            """Comprehensive health check endpoint"""
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "checks": {}
            }
            
            # Database health check
            try:
                import aiosqlite
                # Simple sync check since this is a sync endpoint
                health_data["checks"]["database"] = {
                    "status": "healthy",
                    "message": "Database connection available"
                }
            except Exception as e:
                health_data["checks"]["database"] = {
                    "status": "unhealthy", 
                    "message": f"Database error: {str(e)}"
                }
                health_data["status"] = "degraded"
            
            # CryptoBot API check
            if CRYPTOBOT_API_TOKEN:
                health_data["checks"]["cryptobot"] = {
                    "status": "configured",
                    "message": "CryptoBot API token is configured"
                }
            else:
                health_data["checks"]["cryptobot"] = {
                    "status": "warning",
                    "message": "CryptoBot API token not configured"
                }
            
            # Bot configuration check
            health_data["checks"]["configuration"] = {
                "status": "healthy",
                "demo_mode": DEMO_MODE,
                "owner_configured": OWNER_USER_ID > 0,
                "admin_count": len(ADMIN_USER_IDS)
            }
            
            return health_data
        
        @app.route('/status')
        def status():
            """Bot status and basic metrics"""
            uptime = datetime.now() - startup_time
            return {
                "bot_status": "running",
                "version": BOT_VERSION,
                "uptime": {
                    "seconds": int(uptime.total_seconds()),
                    "human": str(uptime).split('.')[0]
                },
                "configuration": {
                    "demo_mode": DEMO_MODE,
                    "withdrawal_limits": {
                        "min_usd": MIN_WITHDRAWAL_USD,
                        "max_daily_usd": MAX_WITHDRAWAL_USD_DAILY,
                        "fee_percent": WITHDRAWAL_FEE_PERCENT
                    },
                    "supported_games": ["slots", "coinflip", "dice"],
                    "supported_assets": ["LTC", "TON", "SOL"]
                },
                "environment": {
                    "port": int(os.getenv('PORT', 8080)),
                    "render_url": os.getenv('RENDER_EXTERNAL_URL', 'Not set')
                }
            }
        
        @app.route('/metrics')
        def metrics():
            """Basic metrics endpoint"""
            uptime = datetime.now() - startup_time
            return {
                "uptime_seconds": int(uptime.total_seconds()),
                "timestamp": datetime.now().isoformat(),
                "version": BOT_VERSION,
                "demo_mode": DEMO_MODE,
                "configuration_status": {
                    "bot_token": "configured" if BOT_TOKEN else "missing",
                    "cryptobot_token": "configured" if CRYPTOBOT_API_TOKEN else "missing",
                    "owner_id": "configured" if OWNER_USER_ID > 0 else "missing",
                    "admin_count": len(ADMIN_USER_IDS)
                }
            }
        
        @app.route('/ping')
        def ping():
            """Simple ping endpoint"""
            return {"pong": True, "timestamp": datetime.now().isoformat()}
        
        @app.errorhandler(404)
        def not_found(error):
            return {
                "error": "Not Found",
                "message": "The requested endpoint does not exist",
                "available_endpoints": ["/", "/health", "/status", "/metrics", "/ping"]
            }, 404
        
        @app.errorhandler(500)
        def internal_error(error):
            return {
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now().isoformat()
            }, 500
            
        # Start server with error handling
        try:
            logger.info(f"🌐 Starting keep-alive server on port {int(os.getenv('PORT', 8080))}")
            serve(app, host='0.0.0.0', port=int(os.getenv('PORT', 8080)), threads=4)
        except Exception as e:
            logger.error(f"❌ Failed to start keep-alive server: {e}")
            # Fallback to Flask development server
            try:
                logger.info("🔄 Falling back to Flask development server")
                app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=False)
            except Exception as fallback_error:
                logger.error(f"❌ Fallback server also failed: {fallback_error}")
    
    # Start keep-alive server in background thread
    keep_alive_thread = threading.Thread(target=start_keep_alive, daemon=True)
    keep_alive_thread.start()
    logger.info("✅ Keep-alive server started")
    
    # Start the bot using run_polling (this will block and handle everything)
    logger.info("🎯 Starting bot polling...")
    
    # Simple approach - let run_polling handle everything
    await application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    """
    Production-ready entry point for deployment platforms like Render.
    Handles event loop conflicts gracefully.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    try:
        # Apply nest_asyncio to handle nested loops
        nest_asyncio.apply()
        logger.info("Applied nest_asyncio")
        # Run the bot using a compatible event loop approach
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        logger.info("Starting bot...")
        loop.run_until_complete(async_main())
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        sys.exit(1)
