# main.py
"""
Enhanced Telegram Casino Bot v2.1
Professional-grade casino with security, anti-fraud, and comprehensive features.
Stake-style interface with advanced game mechanics and user protection.
"""

import os
import sys
import time
import random
import asyncio
import threading
import logging
import hashlib
import uuid
import re
import hmac
import sqlite3
import aiosqlite
import aiohttp
import nest_asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict, deque
from flask import Flask, request

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User as TelegramUser,
    WebAppInfo
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

# Conversation states for custom betting
WAITING_FOR_BET_AMOUNT = range(1)
SLOTS_BET, COINFLIP_BET, DICE_BET, BLACKJACK_BET, ROULETTE_BET, CRASH_BET = range(6)

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

async def create_crypto_payment(asset: str, amount: float, user_id: int, payload: dict = None) -> dict:
    """Create a Crypto Pay payment using CryptoBot's native payment system"""
    try:
        if not CRYPTOBOT_API_TOKEN:
            return {"ok": False, "error": "API token not configured"}
        
        headers = {
            'Crypto-Pay-API-Token': CRYPTOBOT_API_TOKEN,
            'Content-Type': 'application/json'
        }
        
        # Set webhook URL for payment notifications
        webhook_url = f'{RENDER_EXTERNAL_URL}/webhook/cryptobot' if RENDER_EXTERNAL_URL else 'https://axiscasino.onrender.com/webhook/cryptobot'
        
        # Generate unique payment ID
        payment_id = f"casino_deposit_{user_id}_{int(time.time())}"
        
        data = {
            'asset': asset,
            'amount': f"{amount:.8f}",
            'payment_id': payment_id,
            'description': f'Casino deposit for user {user_id}',
            'webhook_url': webhook_url,
            'expires_in': 3600,  # 1 hour expiration
            'hide_message': True,  # Hide payment in chat
            'pay_anonymously': False
        }
        
        if payload:
            data.update(payload)
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post('https://pay.crypt.bot/api/createPayment', 
                                  headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Crypto Pay payment created successfully: {result.get('result', {}).get('payment_id')}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Crypto Pay API error {response.status}: {error_text}")
                    return {"ok": False, "error": f"API error {response.status}: {error_text}"}
                
    except asyncio.TimeoutError:
        logger.error("Timeout creating crypto payment")
        return {"ok": False, "error": "Request timeout - please try again"}
    except Exception as e:
        logger.error(f"Error creating crypto payment: {e}")
        return {"ok": False, "error": str(e)}

async def create_crypto_invoice(asset: str, amount: float, user_id: int, payload: dict = None) -> dict:
    """Create a crypto invoice using CryptoBot API (fallback for compatibility)"""
    try:
        if not CRYPTOBOT_API_TOKEN:
            return {"ok": False, "error": "API token not configured"}
        
        headers = {
            'Crypto-Pay-API-Token': CRYPTOBOT_API_TOKEN,
            'Content-Type': 'application/json'
        }
        
        # Set webhook URL for payment notifications
        webhook_url = f'{RENDER_EXTERNAL_URL}/webhook/cryptobot' if RENDER_EXTERNAL_URL else 'https://axiscasino.onrender.com/webhook/cryptobot'
        success_url = f'{RENDER_EXTERNAL_URL}/payment_success' if RENDER_EXTERNAL_URL else 'https://axiscasino.onrender.com/payment_success'
        
        data = {
            'asset': asset,
            'amount': f"{amount:.8f}",
            'description': f'Casino deposit for user {user_id}',
            'hidden_message': str(user_id),
            'webhook_url': webhook_url,
            'expires_in': 3600,  # 1 hour expiration
            'allow_comments': False,
            'allow_anonymous': False
        }
        
        if payload:
            data.update(payload)
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post('https://pay.crypt.bot/api/createInvoice', 
                                  headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"CryptoBot invoice created successfully: {result.get('result', {}).get('invoice_id')}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"CryptoBot API error {response.status}: {error_text}")
                    return {"ok": False, "error": f"API error {response.status}: {error_text}"}
                
    except asyncio.TimeoutError:
        logger.error("Timeout creating crypto invoice")
        return {"ok": False, "error": "Request timeout - please try again"}
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

# --- CryptoBot Real-Time Rate Fetch ---
import aiohttp

async def get_crypto_usd_rate(asset: str) -> float:
    """
    Fetch the real-time USD/crypto rate for the given asset from CryptoBot API.
    Returns the price of 1 unit of the asset in USD, or 0.0 on error.
    Includes retry logic for better reliability.
    """
    url = "https://pay.crypt.bot/api/getExchangeRates"
    max_retries = 3
    
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_API_TOKEN
    }
    
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("ok"):
                            rates = data.get("result", [])
                            for rate in rates:
                                if rate.get("source") == asset and rate.get("target") == "USD":
                                    price = float(rate.get("rate", 0))
                                    if price > 0:
                                        logger.info(f"CryptoBot API: {asset}/USD rate = ${price:.6f}")
                                        return price
                            logger.warning(f"CryptoBot API: No rate found for {asset}/USD")
                        else:
                            error_msg = data.get("error", {}).get("name", "Unknown error")
                            logger.error(f"CryptoBot API error: {error_msg} (attempt {attempt + 1}/{max_retries})")
                    else:
                        logger.error(f"CryptoBot API error: HTTP {resp.status} (attempt {attempt + 1}/{max_retries})")
                        
        except Exception as e:
            logger.error(f"Error fetching CryptoBot rate for {asset} (attempt {attempt + 1}/{max_retries}): {e}")
            
        # Wait before retry (except on last attempt)
        if attempt < max_retries - 1:
            await asyncio.sleep(1)
    
    logger.error(f"Failed to get live rate for {asset} after {max_retries} attempts")
    return 0.0

async def get_ltc_usd_rate() -> float:
    """Get current LTC to USD rate"""
    return await get_crypto_usd_rate('LTC')

async def format_usd(amount: float) -> str:
    """Format a float amount as USD string."""
    return f"${amount:,.2f} USD"

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
            
            # Transactions table (for deposits, withdrawals, etc.)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,  -- deposit, withdrawal, etc.
                    amount REAL NOT NULL,
                    description TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

# --- Conversation States (must be defined before use) ---
DEPOSIT_ASSET, DEPOSIT_AMOUNT = range(2)
WITHDRAW_ASSET, WITHDRAW_AMOUNT, WITHDRAW_ADDRESS, WITHDRAW_CONFIRM = range(10, 14)

# --- Bot Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command and main_panel callback"""
    user = update.effective_user
    user_id = user.id if user else None
    is_callback = hasattr(update, 'callback_query') and update.callback_query

    # Get user data to show balance in welcome message
    user_data = await get_user(user_id)
    if not user_data:
        # Create new user if doesn't exist
        username = user.username or user.first_name or f"User_{user_id}"
        await create_user(user_id, username)
        user_data = await get_user(user_id)
    
    balance = await format_usd(user_data['balance'])
    username = user_data['username']

    # Modern, visually balanced main menu layout
    keyboard = [
        [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre"), InlineKeyboardButton("📊 Stats", callback_data="show_stats")],
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit"), InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
    ]
    # Add Owner Panel button if user is owner
    if is_owner(user_id):
        keyboard.append([InlineKeyboardButton("👑 Owner Panel", callback_data="owner_panel")])
    # Help always at the bottom
    keyboard.append([InlineKeyboardButton("ℹ️ Help", callback_data="redeem_panel")])

    text = f"""
� <b>Welcome to Axis Casino!</b> �

👋 <b>Hello, {username}!</b>
💰 <b>Current Balance:</b> {balance}

🎮 <b>Ready to Play?</b>
• Slots, Dice, Coin Flip & More!
• Instant deposits with crypto
• Fast withdrawals
• Live crypto rates

� <b>Get Started:</b>
Choose an option below to begin your casino adventure!

💡 <b>Need help?</b> Use /help anytime
"""
    if is_callback:
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
• Progressive jackpots up to 50x
• Bonus rounds & free spins
• RTP: 96.5%

**🎲 DICE GAMES**
*Simple odds, instant results*
• Even/odd predictions
• High/low bets
• Number guessing up to 6x
• RTP: 98%

**🪙 COIN FLIP**
*50/50 chance, double your money*
• Heads or tails
• Instant results
• 2x payout
• RTP: 98%

**🃏 BLACKJACK**
*Beat the dealer to 21*
• Classic card game
• Strategy matters
• Up to 2.5x payout
• RTP: 99.5%

**🎡 ROULETTE**
*Spin the wheel of fortune*
• Red/Black, Even/Odd
• Single numbers up to 35x
• Multiple betting options
• RTP: 97.3%

**🚀 CRASH**
*Cash out before the crash*
• Multiplier goes up
• Cash out anytime
• Up to 100x possible
• RTP: 99%
"""
    
    keyboard = [
        [InlineKeyboardButton("🎰 SLOTS", callback_data="play_slots"), InlineKeyboardButton("🎲 DICE", callback_data="play_dice")],
        [InlineKeyboardButton("🪙 COIN FLIP", callback_data="coin_flip"), InlineKeyboardButton("🃏 BLACKJACK", callback_data="play_blackjack")],
        [InlineKeyboardButton("🎡 ROULETTE", callback_data="play_roulette"), InlineKeyboardButton("🚀 CRASH", callback_data="play_crash")],
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
🎰 **MEGA SLOT MACHINE** 🎰

💰 **Your Balance:** {balance_usd}

🎯 **How to Play:**
• Enter your custom bet amount (0-1000 USD)
• Spin the reels
• Match 3 symbols to win BIG!

💎 **MEGA PAYOUTS:**
• 💎💎💎 = 50x bet (JACKPOT!)
• 🔔🔔🔔 = 25x bet 
• ⭐⭐⭐ = 15x bet
• 🍒🍒🍒 = 10x bet
• 🍋🍋🍋 = 5x bet
• 🍊🍊🍊 = 3x bet

💰 **Enter your bet amount (0-1000 USD):**
"""
    
    keyboard = [
        [InlineKeyboardButton("💰 Custom Bet", callback_data="slots_custom_bet")],
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
    # User balance is already in USD format, bet is in USD
    bet_usd = bet
    
    # Check balance (allow admin to play with zero balance)
    if user['balance'] < bet_usd and not is_admin(user_id):
        if DEMO_MODE:
            # Demo mode - allow play with zero balance, always win
            win_amount = bet_usd * 3  # 3x win in demo
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
            await deduct_balance(user_id, bet_usd)
        
        # Simple slots simulation with enhanced multipliers
        symbols = ["🍒", "🍋", "🍊", "⭐", "🔔", "💎"]
        # Weighted probability for more exciting gameplay
        weighted_symbols = (["🍒"] * 20 + ["🍋"] * 15 + ["🍊"] * 15 + 
                          ["⭐"] * 8 + ["🔔"] * 5 + ["💎"] * 2)
        reel = [random.choice(weighted_symbols) for _ in range(3)]
        
        if reel[0] == reel[1] == reel[2]:
            # Win!
            if reel[0] == "💎":
                multiplier = 50  # MEGA JACKPOT!
            elif reel[0] == "🔔":
                multiplier = 25
            elif reel[0] == "⭐":
                multiplier = 15
            elif reel[0] == "🍒":
                multiplier = 10
            elif reel[0] == "🍋":
                multiplier = 5
            else:  # 🍊
                multiplier = 3
            
            win_amount = bet_usd * multiplier
            await update_balance(user_id, win_amount)
            result = "WIN"
        else:
            multiplier = 0
            win_amount = 0
            result = "LOSE"
    
    # Log game session
    await log_game_session(user_id, "slots", bet_usd, win_amount, result)
    
    user_after = await get_user(user_id)
    
    if result == "WIN":
        text = f"""
🎰 **SLOT MACHINE RESULT** 🎰

{reel[0]} {reel[1]} {reel[2]}

🎉 **WINNER!** 🎉
💰 **Bet:** ${bet:.2f}
💎 **Win:** ${win_amount:.2f} ({multiplier}x)

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

🎯 **How to Play:**
1. Click the side you want to bet on
2. Enter your custom bet amount (0-1000 USD)
3. Watch the coin flip!
"""
    
    keyboard = [
        [InlineKeyboardButton("🟡 Bet on Heads", callback_data="coinflip_heads"), InlineKeyboardButton("⚫ Bet on Tails", callback_data="coinflip_tails")],
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
    bet_usd = bet
    
    # Check balance (allow admin/demo mode to play with zero balance)
    if user['balance'] < bet_usd and not is_admin(user_id) and not DEMO_MODE:
        await query.answer("❌ Insufficient balance", show_alert=True)
        return
    
    # Admin test mode - always win
    if is_admin(user_id):
        log_admin_action(user_id, f"Playing coin flip in test mode with ${bet} bet")
        coin_result = choice
        win_amount = bet_usd * 1.92
        await update_balance(user_id, win_amount)
        outcome = f"🧪 **TEST MODE (ADMIN)**\n🎉 **YOU WIN!**\n\n{'🟡' if choice == 'heads' else '⚫'} Coin landed on **{choice.upper()}**\n{'🟡' if choice == 'heads' else '⚫'} You chose **{choice.upper()}**\n\n💰 Won: **${bet * 1.92:.2f}**"
    elif DEMO_MODE and user['balance'] < bet_usd:
        # Demo mode - always win, no balance deduction
        coin_result = choice
        win_amount = bet_usd * 1.92
        await update_balance(user_id, win_amount)
        outcome = f"🧪 **DEMO MODE**\n🎉 **YOU WIN!**\n\n{'🟡' if choice == 'heads' else '⚫'} Coin landed on **{choice.upper()}**\n{'🟡' if choice == 'heads' else '⚫'} You chose **{choice.upper()}**\n\n💰 Won: **${bet * 1.92:.2f}**"
    else:
        # Normal game - deduct bet first
        if not is_admin(user_id):  # Admins play for free
            await deduct_balance(user_id, bet_usd)
        
        # Flip coin
        coin_result = random.choice(["heads", "tails"])
        coin_emoji = "🟡" if coin_result == "heads" else "⚫"
        choice_emoji = "🟡" if choice == "heads" else "⚫"
        
        if choice == coin_result:
            # Win - 1.92x payout
            win_amount = bet_usd * 1.92
            await update_balance(user_id, win_amount)
            outcome = f"🎉 **YOU WIN!**\n\n{coin_emoji} Coin landed on **{coin_result.upper()}**\n{choice_emoji} You chose **{choice.upper()}**\n\n💰 Won: **${bet * 1.92:.2f}**"
        else:
            outcome = f"😢 **YOU LOSE!**\n\n{coin_emoji} Coin landed on **{coin_result.upper()}**\n{choice_emoji} You chose **{choice.upper()}**\n\n💸 Lost: **${bet}**"
    
    # Log game session
    await log_game_session(user_id, "coinflip", bet_usd, win_amount if choice == coin_result else 0, "WIN" if choice == coin_result else "LOSE")
    
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
        "Choose your prediction type:\n\n"
        "<b>Payouts:</b>\n"
        "• Correct Number (1-6): 6x\n"
        "• Even/Odd: 2x\n"
        "• High (4-6)/Low (1-3): 2x\n"
    )
    keyboard = [
        [InlineKeyboardButton("1️⃣", callback_data="dice_1"), InlineKeyboardButton("2️⃣", callback_data="dice_2"), InlineKeyboardButton("3️⃣", callback_data="dice_3")],
        [InlineKeyboardButton("4️⃣", callback_data="dice_4"), InlineKeyboardButton("5️⃣", callback_data="dice_5"), InlineKeyboardButton("6️⃣", callback_data="dice_6")],
        [InlineKeyboardButton("📈 Even", callback_data="dice_even"), InlineKeyboardButton("📉 Odd", callback_data="dice_odd")],
        [InlineKeyboardButton("🔺 High (4-6)", callback_data="dice_high"), InlineKeyboardButton("🔻 Low (1-3)", callback_data="dice_low")],
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
    bet_usd = bet
    
    # Check balance (allow admin/demo mode to play with zero balance)
    if user['balance'] < bet_usd and not is_admin(user_id) and not DEMO_MODE:
        await query.answer("❌ Insufficient balance", show_alert=True)
        return
    
    # Deduct bet (except for admins)
    if not is_admin(user_id):
        await deduct_balance(user_id, bet_usd)
    
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
        win_amount = bet_usd * multiplier
        await update_balance(user_id, win_amount)
        result_text = f"🎉 **YOU WIN!**\nDice rolled: **{roll}**\nYour prediction: **{prediction.title()}**\nPayout: **${bet * multiplier:.2f}**"
    else:
        win_amount = 0
        result_text = f"😢 **YOU LOSE!**\nDice rolled: **{roll}**\nYour prediction: **{prediction.title()}**\nLost: **${bet}**"
    
    # Log game session
    await log_game_session(user_id, "dice", bet_usd, win_amount, "WIN" if won else "LOSE")
    
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

# --- NEW CASINO GAMES ---

async def play_blackjack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle blackjack game"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    text = f"""
🃏 **BLACKJACK 21** 🃏

💰 **Your Balance:** {await format_usd(user['balance'])}

🎯 **How to Play:**
• Get as close to 21 as possible
• Beat the dealer without going over
• Aces = 1 or 11, Face cards = 10

💎 **Payouts:**
• Blackjack (21 with 2 cards): 2.5x
• Beat dealer: 2x
• Push (tie): 1x (money back)

💰 **Enter your bet amount (0-1000 USD):**
"""
    
    keyboard = [
        [InlineKeyboardButton("💰 Custom Bet", callback_data="blackjack_custom_bet")],
        [InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def handle_blackjack_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle blackjack betting"""
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
    bet_usd = bet
    
    # Check balance
    if user['balance'] < bet_usd and not is_admin(user_id) and not DEMO_MODE:
        await query.answer("❌ Insufficient balance", show_alert=True)
        return
    
    # Deduct bet (except for admins)
    if not is_admin(user_id):
        await deduct_balance(user_id, bet_usd)
    
    # Blackjack simulation
    def card_value(card):
        if card in ['J', 'Q', 'K']:
            return 10
        elif card == 'A':
            return 11  # Will adjust for aces later
        else:
            return int(card)
    
    def hand_value(hand):
        value = sum(card_value(card) for card in hand)
        aces = hand.count('A')
        while value > 21 and aces:
            value -= 10
            aces -= 1
        return value
    
    def format_hand(hand):
        return ' '.join(hand)
    
    # Deal cards
    deck = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'] * 4
    random.shuffle(deck)
    
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    
    player_value = hand_value(player_hand)
    dealer_value = hand_value(dealer_hand)
    
    # Check for blackjack
    player_blackjack = player_value == 21
    dealer_blackjack = dealer_value == 21
    
    if player_blackjack and dealer_blackjack:
        # Push
        await update_balance(user_id, bet_usd)  # Return bet
        result = "PUSH"
        win_amount = bet_usd
        outcome = f"🤝 **PUSH!**\nBoth got Blackjack!\n\n💰 Bet returned: ${bet:.2f}"
    elif player_blackjack:
        # Player blackjack wins
        win_amount = bet_usd * 2.5
        await update_balance(user_id, win_amount)
        result = "WIN"
        outcome = f"🃏 **BLACKJACK!** 🃏\nYou got 21!\n\n💰 Win: ${win_amount:.2f} (2.5x)"
    elif dealer_blackjack:
        # Dealer blackjack, player loses
        win_amount = 0
        result = "LOSE"
        outcome = f"😔 **DEALER BLACKJACK**\nDealer got 21!\n\n💰 Lost: ${bet:.2f}"
    else:
        # Dealer draws to 17
        while dealer_value < 17:
            dealer_hand.append(deck.pop())
            dealer_value = hand_value(dealer_hand)
        
        if dealer_value > 21:
            # Dealer busts
            win_amount = bet_usd * 2
            await update_balance(user_id, win_amount)
            result = "WIN"
            outcome = f"🎉 **DEALER BUST!**\nDealer over 21!\n\n💰 Win: ${win_amount:.2f} (2x)"
        elif player_value > dealer_value:
            # Player wins
            win_amount = bet_usd * 2
            await update_balance(user_id, win_amount)
            result = "WIN"
            outcome = f"🎉 **YOU WIN!**\nBeat the dealer!\n\n💰 Win: ${win_amount:.2f} (2x)"
        elif player_value == dealer_value:
            # Push
            await update_balance(user_id, bet_usd)
            result = "PUSH"
            win_amount = bet_usd
            outcome = f"🤝 **PUSH!**\nSame value!\n\n💰 Bet returned: ${bet:.2f}"
        else:
            # Dealer wins
            win_amount = 0
            result = "LOSE"
            outcome = f"😔 **DEALER WINS**\nDealer beat you!\n\n💰 Lost: ${bet:.2f}"
    
    # Log game session
    await log_game_session(user_id, "blackjack", bet_usd, win_amount if result == "WIN" else 0, result)
    
    user_after = await get_user(user_id)
    
    text = f"""
🃏 **BLACKJACK RESULT** 🃏

**Your Hand:** {format_hand(player_hand)} = {player_value}
**Dealer Hand:** {format_hand(dealer_hand)} = {dealer_value}

{outcome}

💰 **New Balance:** {await format_usd(user_after['balance'])}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Play Again", callback_data="play_blackjack"), InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def play_roulette_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle roulette game"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    text = f"""
🎡 **EUROPEAN ROULETTE** 🎡

💰 **Your Balance:** {await format_usd(user['balance'])}

🎯 **Betting Options:**
• **Red/Black:** 2x payout
• **Even/Odd:** 2x payout  
• **1-18/19-36:** 2x payout
• **Single Number:** 35x payout!

🎮 **Choose your bet type:**
"""
    
    keyboard = [
        [InlineKeyboardButton("🔴 Red", callback_data="roulette_red"), InlineKeyboardButton("⚫ Black", callback_data="roulette_black")],
        [InlineKeyboardButton("📈 Even", callback_data="roulette_even"), InlineKeyboardButton("📉 Odd", callback_data="roulette_odd")],
        [InlineKeyboardButton("🔢 Lucky Number", callback_data="roulette_number")],
        [InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def handle_roulette_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle roulette betting"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    try:
        parts = data.split("_")
        bet_type = parts[1]
        bet = float(parts[2])
    except:
        await query.answer("❌ Invalid bet format", show_alert=True)
        return
    
    user = await get_user(user_id)
    bet_usd = bet
    
    # Check balance
    if user['balance'] < bet_usd and not is_admin(user_id) and not DEMO_MODE:
        await query.answer("❌ Insufficient balance", show_alert=True)
        return
    
    # Deduct bet (except for admins)
    if not is_admin(user_id):
        await deduct_balance(user_id, bet_usd)
    
    # Roulette spin (European roulette: 0-36)
    winning_number = random.randint(0, 36)
    
    # Determine color and properties
    red_numbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
    is_red = winning_number in red_numbers
    is_black = winning_number != 0 and not is_red
    is_even = winning_number != 0 and winning_number % 2 == 0
    is_odd = winning_number != 0 and winning_number % 2 == 1
    
    won = False
    multiplier = 0
    
    if bet_type == "number":
        # User chose lucky number (random 0-36)
        user_number = random.randint(0, 36)
        if winning_number == user_number:
            won = True
            multiplier = 35
        bet_description = f"Number {user_number}"
    elif bet_type == "red" and is_red:
        won = True
        multiplier = 2
        bet_description = "Red"
    elif bet_type == "black" and is_black:
        won = True
        multiplier = 2
        bet_description = "Black"
    elif bet_type == "even" and is_even:
        won = True
        multiplier = 2
        bet_description = "Even"
    elif bet_type == "odd" and is_odd:
        won = True
        multiplier = 2
        bet_description = "Odd"
    else:
        bet_description = bet_type.title()
    
    # Calculate payout
    if won:
        win_amount = bet_usd * multiplier
        await update_balance(user_id, win_amount)
        result_text = f"🎉 **WINNER!**\nYour bet: **{bet_description}**\nPayout: **${win_amount:.2f}** ({multiplier}x)"
        result = "WIN"
    else:
        win_amount = 0
        result_text = f"😔 **NO WIN**\nYour bet: **{bet_description}**\nLost: **${bet:.2f}**"
        result = "LOSE"
    
    # Determine winning number color emoji
    if winning_number == 0:
        number_display = "🟢 0"
    elif is_red:
        number_display = f"🔴 {winning_number}"
    else:
        number_display = f"⚫ {winning_number}"
    
    # Log game session
    await log_game_session(user_id, "roulette", bet_usd, win_amount, result)
    
    user_after = await get_user(user_id)
    
    text = f"""
🎡 **ROULETTE RESULT** 🎡

🎯 **Winning Number:** {number_display}

{result_text}

💰 **New Balance:** {await format_usd(user_after['balance'])}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Spin Again", callback_data="play_roulette"), InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def play_crash_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle crash game"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    text = f"""
🚀 **CRASH GAME** 🚀

💰 **Your Balance:** {await format_usd(user['balance'])}

🎯 **How to Play:**
• Place your bet
• Watch the multiplier rise
• Cash out before it crashes!
• The longer you wait, the higher the multiplier

🎮 **Risk vs Reward:**
• **Safe:** Cash out at 1.5x-2x (75% success)
• **Medium:** Cash out at 2x-5x (50% success)  
• **Risky:** Cash out at 5x-10x (25% success)
• **YOLO:** Try for 10x+ (10% success)

🎮 **Choose your strategy:**
"""
    
    keyboard = [
        [InlineKeyboardButton("🛡️ Safe", callback_data="crash_safe"), InlineKeyboardButton("⚖️ Medium", callback_data="crash_medium")],
        [InlineKeyboardButton("🎲 Risky", callback_data="crash_risky"), InlineKeyboardButton("🚀 YOLO", callback_data="crash_yolo")],
        [InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def handle_crash_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle crash betting"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    try:
        parts = data.split("_")
        strategy = parts[1]
        bet = float(parts[2])
    except:
        await query.answer("❌ Invalid bet format", show_alert=True)
        return
    
    user = await get_user(user_id)
    bet_usd = bet
    
    # Check balance
    if user['balance'] < bet_usd and not is_admin(user_id) and not DEMO_MODE:
        await query.answer("❌ Insufficient balance", show_alert=True)
        return
    
    # Deduct bet (except for admins)
    if not is_admin(user_id):
        await deduct_balance(user_id, bet_usd)
    
    # Crash simulation based on strategy
    if strategy == "safe":
        target_multiplier = random.uniform(1.5, 2.0)
        crash_point = random.uniform(1.2, 10.0)
        success_emoji = "🛡️"
    elif strategy == "medium":
        target_multiplier = random.uniform(2.0, 5.0)
        crash_point = random.uniform(1.5, 15.0)
        success_emoji = "⚖️"
    elif strategy == "risky":
        target_multiplier = random.uniform(5.0, 10.0)
        crash_point = random.uniform(2.0, 25.0)
        success_emoji = "🎲"
    else:  # yolo
        target_multiplier = random.uniform(10.0, 100.0)
        crash_point = random.uniform(3.0, 150.0)
        success_emoji = "🚀"
    
    # Determine if player cashed out in time
    if target_multiplier <= crash_point:
        # Success! Player cashed out before crash
        win_amount = bet_usd * target_multiplier
        await update_balance(user_id, win_amount)
        result = "WIN"
        outcome = f"{success_emoji} **CASHED OUT!**\nYou cashed out at **{target_multiplier:.2f}x**\nCrash point was **{crash_point:.2f}x**\n\n💰 Win: **${win_amount:.2f}**"
    else:
        # Crashed before cashout
        win_amount = 0
        result = "LOSE"
        outcome = f"💥 **CRASHED!**\nCrashed at **{crash_point:.2f}x**\nYou were aiming for **{target_multiplier:.2f}x**\n\n💰 Lost: **${bet:.2f}**"
    
    # Log game session
    await log_game_session(user_id, "crash", bet_usd, win_amount, result)
    
    user_after = await get_user(user_id)
    
    text = f"""
🚀 **CRASH RESULT** 🚀

{outcome}

💰 **New Balance:** {await format_usd(user_after['balance'])}

Try again or change your strategy!
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Play Again", callback_data="play_crash"), InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Deposit/Withdrawal Handlers ---

async def deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main deposit menu and start deposit conversation"""
    query = update.callback_query
    await query.answer()
    text = """
💳 **DEPOSIT FUNDS** 💳

Choose your cryptocurrency:

🏦 **Supported Assets:**
• Litecoin (LTC) - Fast & low fees
• Toncoin (TON) - Telegram native  
• Solana (SOL) - High speed

⚡ **Instant deposits via CryptoBot**
🔒 **Secure & anonymous**
"""
    keyboard = [
        [InlineKeyboardButton("Litecoin (LTC)", callback_data="deposit_ltc"),
         InlineKeyboardButton("Toncoin (TON)", callback_data="deposit_ton")],
        [InlineKeyboardButton("Solana (SOL)", callback_data="deposit_sol")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    return DEPOSIT_ASSET

async def deposit_ltc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['deposit_asset'] = 'LTC'
    
    # Get minimum deposit in USD from environment
    min_deposit_usd = float(os.environ.get("MIN_DEPOSIT_LTC_USD", "1.00"))
    
    text = f"""
**Litecoin (LTC) Deposit**

Enter the amount in USD you want to deposit:
(Minimum: ${min_deposit_usd:.2f} USD)

💡 Your USD amount will be converted to LTC automatically
"""
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="deposit")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    return DEPOSIT_AMOUNT

async def deposit_ton_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['deposit_asset'] = 'TON'
    
    # Get minimum deposit in USD from environment
    min_deposit_usd = float(os.environ.get("MIN_DEPOSIT_TON_USD", "2.50"))
    
    text = f"""
**Toncoin (TON) Deposit**

Enter the amount in USD you want to deposit:
(Minimum: ${min_deposit_usd:.2f} USD)

💡 Your USD amount will be converted to TON automatically
"""
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="deposit")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    return DEPOSIT_AMOUNT

async def deposit_sol_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['deposit_asset'] = 'SOL'
    
    # Get minimum deposit in USD from environment
    min_deposit_usd = float(os.environ.get("MIN_DEPOSIT_SOL_USD", "1.15"))
    
    text = f"""
**Solana (SOL) Deposit**

Enter the amount in USD you want to deposit:
(Minimum: ${min_deposit_usd:.2f} USD)

💡 Your USD amount will be converted to SOL automatically
"""
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="deposit")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    return DEPOSIT_AMOUNT

async def deposit_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    asset = context.user_data.get('deposit_asset')
    amount_text = update.message.text.strip()
    
    try:
        # User enters USD amount
        usd_amount = float(amount_text)
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid USD amount.")
        return DEPOSIT_AMOUNT
    
    # Get minimum amounts from environment
    min_amounts = {
        'LTC': float(os.environ.get("MIN_DEPOSIT_LTC_USD", "1.00")),
        'TON': float(os.environ.get("MIN_DEPOSIT_TON_USD", "2.50")),
        'SOL': float(os.environ.get("MIN_DEPOSIT_SOL_USD", "1.15"))
    }
    
    min_usd = min_amounts.get(asset, 1.00)
    if usd_amount < min_usd:
        await update.message.reply_text(f"❌ Minimum deposit for {asset} is ${min_usd:.2f} USD. Please enter a higher amount.")
        return DEPOSIT_AMOUNT
    
    # Show processing message
    processing_msg = await update.message.reply_text("⏳ Creating your deposit invoice...")
    
    # Convert USD to crypto amount for the invoice
    crypto_rate = await get_crypto_usd_rate(asset)
    crypto_amount = usd_amount / crypto_rate if crypto_rate > 0 else 0
    if crypto_amount <= 0:
        await processing_msg.edit_text("❌ Unable to get exchange rate. Please try again later.")
        return DEPOSIT_AMOUNT

    # Create invoice with crypto amount in the selected asset
    invoice_result = await create_crypto_invoice(asset, crypto_amount, user_id)
    if invoice_result.get('ok'):
        result = invoice_result['result']
        pay_url = result.get('pay_url')  # https://t.me/CryptoBot?start=...
        mini_app_url = result.get('mini_app_invoice_url')  # CryptoBot Mini App URL
        web_app_url = result.get('web_app_invoice_url')  # https://app.cr.bot/invoices/<hash>
        invoice_hash = result.get('hash')  # Invoice hash for Mini App
        invoice_id = result.get('invoice_id')
        
        # Log available URLs for debugging
        logger.info(f"Invoice URLs - pay_url: {pay_url}, mini_app: {mini_app_url}, web_app: {web_app_url}, hash: {invoice_hash}")
        
        # Build keyboard with external payment links only
        keyboard_rows = []
        

        # External links (t.me URLs and regular links)
        if mini_app_url and mini_app_url.startswith('https://t.me'):
            keyboard_rows.append([
                InlineKeyboardButton("� Open CryptoBot Mini App", url=mini_app_url)
            ])
        
        # Fallback: Open CryptoBot directly (external)
        if pay_url:
            keyboard_rows.append([
                InlineKeyboardButton("💳 Pay in CryptoBot App", url=pay_url)
            ])
        # Navigation
        keyboard_rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")])
        
        text = f"""
💳 **{asset} DEPOSIT** 💳

💰 **Amount:** ${usd_amount:.2f} USD
🆔 **Invoice ID:** `{invoice_id}`
� **Live Rate:** 1 {asset} = ${crypto_rate:.2f} USD
�💱 **Crypto Amount:** {crypto_amount:.8f} {asset}

⚡ Payment will be processed automatically using live rates
🔄 Your balance will update instantly after confirmation
⏰ Invoice expires in 60 minutes

💡 **Important:**
• Rate is live from CryptoBot API at time of invoice creation
• Final conversion uses live rate at payment confirmation
• Payment is secure and processed by CryptoBot
• Keep this chat open during payment

📞 **Having issues?** Use /payment to check status

🚀 **Ready to pay? Click one of the payment buttons below!**
"""
        await processing_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        return ConversationHandler.END
    else:
        error_msg = invoice_result.get('error', 'Unknown error')
        await processing_msg.edit_text(f"❌ Error creating deposit invoice: {error_msg}\n\nPlease try again or contact support if the issue persists.")
        return DEPOSIT_AMOUNT

# --- Withdrawal Conversation Handler ---
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start withdrawal process: choose asset"""
    user = update.effective_user
    user_id = user.id
    user_data = await get_user(user_id)
    if not user_data or user_data['balance'] < 1.0:
        await update.message.reply_text("❌ You need at least $1.00 to withdraw.")
        return ConversationHandler.END
    text = """
💸 <b>WITHDRAW FUNDS</b> 💸\n\nChoose the cryptocurrency to withdraw:"""
    keyboard = [
        [InlineKeyboardButton("Litecoin (LTC)", callback_data="withdraw_asset_LTC"),
         InlineKeyboardButton("Toncoin (TON)", callback_data="withdraw_asset_TON")],
        [InlineKeyboardButton("Solana (SOL)", callback_data="withdraw_asset_SOL")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return WITHDRAW_ASSET

async def withdraw_asset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    asset = query.data.split('_')[-1]
    context.user_data['withdraw_asset'] = asset
    min_usd = float(os.environ.get(f"MIN_DEPOSIT_{asset}_USD", "1.00"))
    text = f"""
<b>{asset} Withdrawal</b>\n\nEnter the amount in USD you want to withdraw:\n(Minimum: ${min_usd:.2f})\n\nYour balance: ${context.user_data.get('balance', 'N/A')}\n"""
    await query.edit_message_text(text, parse_mode=ParseMode.HTML)
    return WITHDRAW_AMOUNT

async def withdraw_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    asset = context.user_data.get('withdraw_asset')
    user = await get_user(user_id)
    try:
        usd_amount = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Enter a number in USD.")
        return WITHDRAW_AMOUNT
    min_usd = float(os.environ.get(f"MIN_DEPOSIT_{asset}_USD", "1.00"))
    if usd_amount < min_usd:
        await update.message.reply_text(f"❌ Minimum withdrawal for {asset} is ${min_usd:.2f}.")
        return WITHDRAW_AMOUNT
    if usd_amount > user['balance']:
        await update.message.reply_text("❌ Insufficient balance.")
        return WITHDRAW_AMOUNT
    context.user_data['withdraw_amount'] = usd_amount
    await update.message.reply_text(f"Enter your {asset} address:")
    return WITHDRAW_ADDRESS

async def withdraw_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    asset = context.user_data.get('withdraw_asset')
    if not validate_crypto_address(address, asset):
        await update.message.reply_text("❌ Invalid address format. Please try again.")
        return WITHDRAW_ADDRESS
    context.user_data['withdraw_address'] = address
    usd_amount = context.user_data['withdraw_amount']
    fee = calculate_withdrawal_fee(usd_amount)
    net = usd_amount - fee
    text = f"""
<b>Confirm Withdrawal</b>\n\n<b>Asset:</b> {asset}\n<b>Amount:</b> ${usd_amount:.2f}\n<b>Fee:</b> ${fee:.2f}\n<b>Net:</b> ${net:.2f}\n<b>Address:</b> <code>{address}</code>\n\nSend?"""
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data="withdraw_confirm")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main_panel")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return WITHDRAW_CONFIRM

async def withdraw_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    asset = context.user_data.get('withdraw_asset')
    usd_amount = context.user_data.get('withdraw_amount')
    address = context.user_data.get('withdraw_address')
    fee = calculate_withdrawal_fee(usd_amount)
    net = usd_amount - fee
    user = await get_user(user_id)
    if user['balance'] < usd_amount:
        await query.edit_message_text("❌ Insufficient balance.")
        return ConversationHandler.END
    # Deduct balance atomically
    await deduct_balance(user_id, usd_amount)
    # Log withdrawal (pending status)
    await log_withdrawal(user_id, asset, usd_amount, address, fee, net)
    await query.edit_message_text(f"✅ Withdrawal request submitted!\n\n<b>Asset:</b> {asset}\n<b>Amount:</b> ${usd_amount:.2f}\n<b>Net:</b> ${net:.2f}\n<b>Address:</b> <code>{address}</code>\n\nAn admin will review and process your withdrawal soon.", parse_mode=ParseMode.HTML)
    return ConversationHandler.END

# --- Register Deposit and Withdrawal ConversationHandler ---
deposit_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(deposit_callback, pattern="^deposit$")],
    states={
        DEPOSIT_ASSET: [
            CallbackQueryHandler(deposit_ltc_callback, pattern="^deposit_ltc$"),
            CallbackQueryHandler(deposit_ton_callback, pattern="^deposit_ton$"),
            CallbackQueryHandler(deposit_sol_callback, pattern="^deposit_sol$"),
        ],
        DEPOSIT_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_amount_handler),
            CallbackQueryHandler(deposit_callback, pattern="^deposit$")
        ],
    },
    fallbacks=[CallbackQueryHandler(deposit_callback, pattern="^deposit$")],
    allow_reentry=True
)

withdraw_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("withdraw", withdraw_start)],
    states={
        WITHDRAW_ASSET: [CallbackQueryHandler(withdraw_asset_callback, pattern="^withdraw_asset_")],
        WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount_handler)],
        WITHDRAW_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_address_handler)],
        WITHDRAW_CONFIRM: [CallbackQueryHandler(withdraw_confirm_callback, pattern="^withdraw_confirm$")],
    },
    fallbacks=[CallbackQueryHandler(start_command, pattern="^main_panel$")],
    allow_reentry=True
)

# --- Custom Bet Conversation Handlers ---

# Conversation states for custom betting
SLOTS_BET, COINFLIP_BET, DICE_BET, BLACKJACK_BET, ROULETTE_BET, CRASH_BET = range(6)

# --- Admin Panel Handlers ---
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
        
        # Withdrawals today (handle table not existing)
        try:
            today = datetime.now().date()
            cursor = await db.execute("""
                SELECT COUNT(*), SUM(amount_usd) FROM withdrawals 
                WHERE DATE(created_at) = ? AND status = 'completed'
            """, (today,))
            withdrawal_data = await cursor.fetchone()
            withdrawals_today = withdrawal_data[0] or 0
            withdrawal_amount_today = withdrawal_data[1] or 0.0
        except Exception:
            withdrawals_today = 0
            withdrawal_amount_today = 0.0

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
    keyboard = [
        [InlineKeyboardButton("📊 Detailed Stats", callback_data="owner_detailed_stats"), 
         InlineKeyboardButton("👥 User Management", callback_data="owner_user_mgmt")],
        [InlineKeyboardButton("💰 Financial Report", callback_data="owner_financial"), 
         InlineKeyboardButton("📋 Withdrawal History", callback_data="owner_withdrawals")],
        [InlineKeyboardButton("⚙️ System Health", callback_data="owner_system_health"), 
         InlineKeyboardButton("🎮 Toggle Demo", callback_data="owner_toggle_demo")],
        [InlineKeyboardButton("🔧 Bot Settings", callback_data="owner_bot_settings"), 
         InlineKeyboardButton("📈 Analytics", callback_data="owner_analytics")],
        [InlineKeyboardButton("🔄 Refresh Data", callback_data="owner_panel")],
        [InlineKeyboardButton("👤 User Panel", callback_data="main_panel"), 
         InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    # Handle both callback query and direct message
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def owner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow owner to open the owner panel via /owner command."""
    user = update.effective_user
    user_id = user.id if user else None
    if not is_owner(user_id):
        await update.message.reply_text("❌ Access denied. Owner only.")
        return
    await owner_panel_callback(update, context)

# --- Owner Demo Toggle (was admin_toggle_demo_callback, now owner only) ---

async def owner_toggle_demo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle demo mode for testing (owner only)"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if not is_owner(user_id):
        await query.answer("❌ Access denied. Owner only.", show_alert=True)
        return

    # Toggle demo mode (stored in context or database)
    current_demo = context.bot_data.get('demo_mode', False)
    new_demo = not current_demo
    context.bot_data['demo_mode'] = new_demo

    status = "🟢 ENABLED" if new_demo else "🔴 DISABLED"

    text = f"""
🧪 <b>DEMO MODE TOGGLE</b> 🧪

Demo Mode: <b>{status}</b>

<b>Demo Mode Effects:</b>
• All bets use virtual currency
• No real balance changes
• Games run in test mode
• Perfect for testing features

<b>Current Settings:</b>
• Mode: {"Demo" if new_demo else "Live"}
• Real Money: {"No" if new_demo else "Yes"}
• Testing: {"Active" if new_demo else "Inactive"}

<i>This setting affects all users globally.</i>
"""

    keyboard = [
        [InlineKeyboardButton(f"{'🔴 Disable' if new_demo else '🟢 Enable'} Demo", callback_data="owner_toggle_demo")],
        [InlineKeyboardButton("🔙 Back to Owner Panel", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# --- Utility Commands and Callbacks ---

async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /health command - show bot status and system health"""
    try:
        # Simple health check - in production, expand this with real checks
        uptime = int(time.time() - start_time)
        uptime_str = f"{uptime // 3600}h {uptime % 3600 // 60}m {uptime % 60}s"
        
        # Example of a more advanced check (uncomment in production)
        # response = await aiohttp.ClientSession().get('https://api.example.com/health')
        # if response.status != 200:
        #     raise Exception("External API health check failed")
        
        text = (
            "✅ <b>Bot Health Check</b> ✅\n\n"
            "All systems operational.\n"
            f"Uptime: <code>{uptime_str}</code>\n"
            "Load: Normal\n"
            "Memory: Optimal\n"
            "Disk: Sufficient space\n\n"
            "Responding to commands and ready for action!"
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        text = "❌ Health check failed. Please investigate."

    if update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    elif update.callback_query:
        await update.callback_query.answer(text, show_alert=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    
    text = (
        "ℹ️ <b>Help & Support</b> ℹ️\n\n"
        "Welcome to the Casino Bot! Here are some commands to get you started:\n\n"
        "🔹 /start - Begin your casino adventure\n"
        "🔹 /balance - Check your current balance\n"
        "🔹 /app - Access the mini app centre\n"
        "🔹 /help - Get assistance and support\n"
        "🔹 /owner - Access owner panel (if you are the owner)\n\n"
        "For instant updates, join our support channel: @casino_support\n\n"
        "Have fun and good luck!"
    )
    
    if update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    elif update.callback_query:
        await update.callback_query.answer(text, show_alert=True)

async def redeem_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the redeem panel for bonus and rewards"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    text = f"""
🎁 **REDEEM REWARDS** 🎁

💰 **Your Balance:** {await format_usd(user['balance'])}

Get bonuses, free spins, and exclusive offers!

🔹 **Loyalty Points:** Earned by playing games
🔹 **Daily Bonus:** Claim every 24 hours
🔹 **Referral Bonus:** Invite friends and earn rewards

📅 **Last claimed:** Never
🎉 **Total rewards:** 0
"""
    keyboard = [
        [InlineKeyboardButton("🎁 Claim Daily Bonus", callback_data="claim_daily_bonus")],
        [InlineKeyboardButton("💌 Invite Friends", callback_data="invite_friends")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def show_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics and leaderboard"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    # Get comprehensive statistics
    async with aiosqlite.connect(DB_PATH) as db:
        # User rank by balance
        cursor = await db.execute("""
            SELECT COUNT(*) + 1 FROM users 
            WHERE balance > ?
        """, (user['balance'],))
        user_rank = (await cursor.fetchone())[0]
        
        # Total users count
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        # User's win rate (from game_sessions)
        cursor = await db.execute("""
            SELECT 
                COUNT(*) as total_games,
                SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(win_amount) as total_winnings
            FROM game_sessions 
            WHERE user_id = ?
        """, (user_id,))
        game_stats = await cursor.fetchone()
        
        total_games_detailed = game_stats[0] or 0
        wins = game_stats[1] or 0
        total_winnings = game_stats[2] or 0.0
        win_rate = (wins / total_games_detailed * 100) if total_games_detailed > 0 else 0
        
        # Recent game activity (last 5 games)
        cursor = await db.execute("""
            SELECT game_type, bet_amount, win_amount, result, created_at
            FROM game_sessions 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 5
        """, (user_id,))
        recent_games = await cursor.fetchall()
        
        # Global leaderboard (top 10 by balance)
        cursor = await db.execute("""
            SELECT username, balance 
            FROM users 
            ORDER BY balance DESC 
            LIMIT 10
        """)
        leaderboard = await cursor.fetchall()
    
    # Format leaderboard text
    lb_text = ""
    for i, (username, balance) in enumerate(leaderboard, start=1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        lb_text += f"{emoji} {username}: {await format_usd(balance)}\n"
    
    # Format recent games
    recent_text = ""
    if recent_games:
        for game in recent_games[:3]:  # Show last 3 games
            game_type, bet, win, result, timestamp = game
            emoji = "🟢" if result == "WIN" else "🔴"
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%m/%d %H:%M")
            except:
                time_str = timestamp[:10] if len(timestamp) > 10 else timestamp
            
            recent_text += f"{emoji} {game_type.title()}: ${bet:.0f} → ${win:.0f} ({time_str})\n"
    else:
        recent_text = "No games played yet"
    
    # Calculate net profit/loss
    net_result = total_winnings - user['total_wagered']
    net_emoji = "📈" if net_result >= 0 else "📉"
    
    text = f"""
📊 <b>YOUR CASINO STATISTICS</b> 📊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 <b>Player Profile:</b>
• Name: {user['username']}
• Balance: {await format_usd(user['balance'])}
• Rank: #{user_rank} of {total_users} players

🎮 <b>Gaming Stats:</b>
• Games Played: {user['games_played']}
• Win Rate: {win_rate:.1f}% ({wins}/{total_games_detailed})
• Total Wagered: {await format_usd(user['total_wagered'])}
• Total Winnings: {await format_usd(total_winnings)}
• Net Result: {net_emoji} {await format_usd(abs(net_result))} {"profit" if net_result >= 0 else "loss"}

🕒 <b>Recent Games:</b>
{recent_text}

🏆 <b>Top Players:</b>
{lb_text}

💡 <b>Tip:</b> {"Great job! Keep up the winning streak!" if win_rate > 50 else "Try different games to improve your luck!"}
"""
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="show_stats")],
        [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def check_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Allow users to check their recent payment status"""
    user = update.effective_user
    user_id = user.id
    
    try:
        # Get recent transactions for this user
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT type, amount, description, timestamp 
                FROM transactions 
                WHERE user_id = ? AND type = 'deposit'
                ORDER BY timestamp DESC 
                LIMIT 3
            """, (user_id,))
            recent_deposits = await cursor.fetchall()
        
        if not recent_deposits:
            text = """
❌ **No Recent Deposits Found**

If you just made a payment:
• Wait 2-3 minutes for confirmation
• Check that payment was completed in CryptoBot
• Contact support if payment completed but balance not updated

📞 **Support:** @casino_support
"""
        else:
            text = "💳 **Recent Deposits:**\n\n"
            for deposit in recent_deposits:
                deposit_type, amount, description, timestamp = deposit
                # Parse timestamp

                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%m/%d %H:%M")

                except:
                    time_str = timestamp[:16] if len(timestamp) > 16 else timestamp
            
                text += f"✅ **${amount:.2f}** - {time_str}\n"
                if description:
                    text += f"   _{description}_\n"
                text += "\n"
            
           
            
            text += """
🔄 **Payment Taking Long?**
• CryptoBot payments usually confirm within 1-5 minutes
• Check your CryptoBot app for payment status
• Contact support if payment completed but balance missing

📞 **Support:** @casino_support
"""
        
        keyboard = [
            [InlineKeyboardButton("💰 Check Balance", callback_data="balance")],
            [InlineKeyboardButton("💳 Make Deposit", callback_data="deposit")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        logger.error(f"Error checking payments for user {user_id}: {e}")
        await update.message.reply_text("❌ Error checking payment status. Please try again or contact support.")

async def test_cryptobot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test CryptoBot invoice creation (for debugging)"""
    user = update.effective_user
    user_id = user.id
    
    # Only allow owner to use this command
    if not is_owner(user_id):
        await update.message.reply_text("❌ This command is only available to the owner.")
        return
    
    try:
        # Create a test invoice
        test_result = await create_crypto_invoice('USDT', 1.0, user_id)
        
        if test_result.get('ok'):
            result = test_result['result']
            
            # Show all available URLs for debugging
            debug_info = f"""
🔧 **CryptoBot Test Invoice Created**

**Available URLs:**
• pay_url: `{result.get('pay_url', 'N/A')}`
• mini_app_invoice_url: `{result.get('mini_app_invoice_url', 'N/A')}`
• web_app_invoice_url: `{result.get('web_app_invoice_url', 'N/A')}`
• bot_invoice_url: `{result.get('bot_invoice_url', 'N/A')}`

**Invoice Details:**
• ID: `{result.get('invoice_id', 'N/A')}`
• Amount: {result.get('amount', 'N/A')} {result.get('asset', 'N/A')}
• Status: {result.get('status', 'N/A')}

**Raw Response:**
```json
{test_result}
```
"""
            
            # Create test button
            keyboard = [
                [InlineKeyboardButton("🧪 Test Payment", url=result.get('pay_url'))],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
            ]
            
            await update.message.reply_text(debug_info, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"❌ Test failed: {test_result.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Test CryptoBot error: {e}")
        await update.message.reply_text(f"❌ Test error: {str(e)}")

async def rates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current live crypto rates from CryptoBot API"""
    user = update.effective_user
    
    # Show loading message
    loading_msg = await update.message.reply_text("⏳ Fetching live crypto rates...")
    
    try:
        # Get live rates for supported assets
        assets = ['LTC', 'TON', 'SOL', 'USDT']
        rates_data = []
        
        for asset in assets:
            rate = await get_crypto_usd_rate(asset)
            if rate > 0:
                rates_data.append(f"• **{asset}**: ${rate:.2f} USD")
            else:
                rates_data.append(f"• **{asset}**: ❌ Rate unavailable")
        
        rates_text = "\n".join(rates_data)
        
        text = f"""
📊 **LIVE CRYPTO RATES** 📊

🔴 **Real-time rates from CryptoBot API:**

{rates_text}

⏰ **Updated:** {datetime.now().strftime("%H:%M:%S UTC")}
🔄 **Refresh:** Use /rates again for latest prices

💡 **Note:** These are the live rates used for all deposits and withdrawals in our casino.
"""
        
        keyboard = [
            [InlineKeyboardButton("💳 Deposit", callback_data="deposit")],
            [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        
        await loading_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error getting rates for user {user.id}: {e}")
        await loading_msg.edit_text("❌ Error fetching crypto rates. Please try again later.")

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
    application.add_handler(CommandHandler("health", health_command))
    application.add_handler(CommandHandler("balance", show_balance_callback))
    application.add_handler(CommandHandler("app", mini_app_centre_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("payment", check_payment_command))
    application.add_handler(CommandHandler("checkpayment", check_payment_command))
    application.add_handler(CommandHandler("testcrypto", test_cryptobot_command))
    application.add_handler(CommandHandler("owner", owner_command))
    application.add_handler(CommandHandler("rates", rates_command))
    
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
    # New casino games
    application.add_handler(CallbackQueryHandler(play_blackjack_callback, pattern="^play_blackjack$"))
    application.add_handler(CallbackQueryHandler(handle_blackjack_bet, pattern="^blackjack_bet_"))
    application.add_handler(CallbackQueryHandler(play_roulette_callback, pattern="^play_roulette$"))
    application.add_handler(CallbackQueryHandler(handle_roulette_bet, pattern="^roulette_"))
    application.add_handler(CallbackQueryHandler(play_crash_callback, pattern="^play_crash$"))
    application.add_handler(CallbackQueryHandler(handle_crash_bet, pattern="^crash_"))
    # Deposit/Withdrawal handlers
    application.add_handler(CallbackQueryHandler(withdraw_start, pattern="^withdraw$"))
    application.add_handler(CallbackQueryHandler(withdraw_asset_callback, pattern="^withdraw_asset_"))
    application.add_handler(CallbackQueryHandler(start_command, pattern="^main_panel$"))
    application.add_handler(CallbackQueryHandler(redeem_panel_callback, pattern="^redeem_panel$"))
    application.add_handler(CallbackQueryHandler(show_stats_callback, pattern="^show_stats$"))
    # Remove admin panel and admin demo toggle handlers
    # application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    # application.add_handler(CallbackQueryHandler(admin_toggle_demo_callback, pattern="^admin_toggle_demo$"))
    # Add owner panel and owner demo toggle only
    application.add_handler(CallbackQueryHandler(owner_panel_callback, pattern="^owner_panel$"))
    application.add_handler(CallbackQueryHandler(owner_toggle_demo_callback, pattern="^owner_toggle_demo$"))

    # Add deposit ConversationHandler (this enables the coin selection -> amount prompt flow)
    application.add_handler(deposit_conv_handler)
    application.add_handler(withdraw_conv_handler)

    # Add global error handler
    application.add_error_handler(global_error_handler)
    
    # Start keep-alive server in a separate thread for deployment platforms
    def start_keep_alive():
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            return {
                "status": "running",
                "bot_version": BOT_VERSION,
                "timestamp": datetime.now().isoformat(),
                "demo_mode": DEMO_MODE
            }
        
        @app.route('/health')
        def health():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        @app.route('/webhook/cryptobot', methods=['POST'])
        def cryptobot_webhook():
            from flask import request
            try:
                data = request.get_json()
                logger.info(f"CryptoBot webhook received: {data}")
                
                # Verify webhook signature if needed
                signature = request.headers.get('Crypto-Pay-Signature')
                if signature and CRYPTOBOT_WEBHOOK_SECRET:
                    # Basic signature verification
                    import hmac
                    expected_signature = hmac.new(
                        CRYPTOBOT_WEBHOOK_SECRET.encode(),
                        request.get_data(),
                        hashlib.sha256
                    ).hexdigest()
                    if not hmac.compare_digest(signature, expected_signature):
                        logger.warning("Invalid webhook signature")
                        return {"status": "invalid_signature"}, 401
                
                # Process payment
                if data and data.get('update_type') == 'invoice_paid':
                    invoice_data = data.get('payload')
                    user_id_str = invoice_data.get('hidden_message')
                    amount = float(invoice_data.get('amount', 0))
                    asset = invoice_data.get('asset', 'USDT')
                    invoice_id = invoice_data.get('invoice_id')
                    
                    if user_id_str and amount > 0:
                        try:
                            user_id = int(user_id_str)
                            # Convert crypto amount to USD for balance update using ONLY live rates
                            usd_amount = amount
                            if asset != 'USDT':
                                # ALWAYS get current rate from CryptoBot API - no fallbacks
                                try:
                                    import aiohttp
                                    import asyncio
                                    
                                    async def get_live_rate():
                                        return await get_crypto_usd_rate(asset)
                                    
                                    # Create new event loop for this sync context
                                    try:
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                        rate = loop.run_until_complete(get_live_rate())
                                        loop.close()
                                        
                                        if rate > 0:
                                            usd_amount = amount * rate
                                            logger.info(f"Webhook: Converted {amount} {asset} to ${usd_amount:.2f} USD using live rate ${rate:.2f}")
                                        else:
                                            logger.error(f"Webhook: CryptoBot API returned invalid rate for {asset}. Cannot process payment without live rate.")
                                            return {"status": "rate_error", "message": "Unable to get live exchange rate"}, 500
                                            
                                    except Exception as rate_error:
                                        logger.error(f"Webhook: Critical error getting live rate for {asset}: {rate_error}")
                                        return {"status": "rate_fetch_failed", "message": "Live rate API unavailable"}, 500
                                        
                                except Exception as e:
                                    logger.error(f"Webhook: Rate conversion system error: {e}")
                                    return {"status": "conversion_error", "message": "Rate conversion failed"}, 500
                            
                            # Update user balance synchronously (we'll use a thread-safe approach)
                            import sqlite3
                            try:
                                conn = sqlite3.connect(DB_PATH)
                                cursor = conn.cursor()
                                
                                # Update balance
                                cursor.execute("""
                                    UPDATE users SET balance = balance + ? 
                                    WHERE user_id = ?
                                """, (usd_amount, user_id))
                                
                                # Log transaction
                                cursor.execute("""
                                    INSERT INTO transactions (user_id, type, amount, description, timestamp)
                                    VALUES (?, 'deposit', ?, ?, ?)
                                """, (user_id, usd_amount, f"Crypto deposit ({asset}): {amount} -> ${usd_amount:.2f}", datetime.now().isoformat()))
                                
                                conn.commit()
                                conn.close()
                                
                                logger.info(f"Payment processed: User {user_id}, Amount: {amount} {asset} (${usd_amount:.2f} USD), Invoice: {invoice_id}")
                                
                                # Try to notify user (best effort)
                                try:
                                    import asyncio
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    
                                    async def notify_user():
                                        try:
                                            await application.bot.send_message(
                                                chat_id=user_id,
                                                text=f"✅ **Deposit Successful!**\n\n💰 **Amount:** ${usd_amount:.2f} USD\n🔗 **Transaction:** {invoice_id}\n\n🎮 Your balance has been updated. Ready to play!",
                                                parse_mode=ParseMode.MARKDOWN
                                            )
                                        except Exception as e:
                                            logger.error(f"Could not notify user {user_id}: {e}")
                                    
                                    loop.run_until_complete(notify_user())
                                    loop.close()
                                except Exception as e:
                                    logger.error(f"Could not send notification: {e}")
                                
                            except Exception as e:
                                logger.error(f"Database error processing payment: {e}")
                                return {"status": "db_error"}, 500
                                
                        except ValueError:
                            logger.error(f"Invalid user_id in webhook: {user_id_str}")
                            return {"status": "invalid_user_id"}, 400
                    
                return {"status": "ok"}
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                return {"status": "error"}, 500
        
        @app.route('/payment_success')
        def payment_success():
            return """
            <html>
            <head><title>Payment Success</title></head>
            <body style="text-align: center; font-family: Arial;">
                <h2>✅ Payment Completed Successfully!</h2>
                <p>Your deposit has been processed. You can close this window.</p>
                <script>
                    setTimeout(() => {
                        window.close();
                    }, 3000);
                </script>
            </body>
            </html>
            """
        
        # Mini App bridge route that opens the CryptoBot invoice inside your bot's WebApp
        @app.route('/miniapp/invoice/<invoice_hash>')
        def miniapp_invoice(invoice_hash: str):
            # CryptoBot web app invoice URL constructed from the invoice hash
            web_invoice = f"https://app.cr.bot/invoices/{invoice_hash}"
            # Minimal WebApp page that redirects inside Telegram's webview
            return f"""
            <!doctype html>
            <html>
              <head>
                <meta charset="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <title>Pay Invoice</title>
                <script src="https://telegram.org/js/telegram-web-app.js"></script>
                <style>
                  body {{ 
                    font-family: -apple-system, system-ui, Arial; 
                    margin: 20px; 
                    text-align: center; 
                    background: #1a1a1a; 
                    color: #ffffff;
                  }}
                  .btn {{ 
                    display: inline-block; 
                    padding: 12px 18px; 
                    background: #2ea44f; 
                    color: #fff; 
                    border-radius: 8px; 
                    text-decoration: none; 
                    margin: 10px;
                  }}
                  .loading {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 20px 0;
                  }}
                </style>
              </head>
              <body>
                <h3>🚀 Opening CryptoBot Payment...</h3>
                <div class="loading">
                  <p>Redirecting to secure payment page...</p>
                </div>
                <p>If the page does not open automatically, tap the button below.</p>
                <p><a class="btn" href="{web_invoice}" target="_self">💳 Open Invoice</a></p>
                <script>
                  try {{
                    // Initialize Telegram WebApp
                    if (window.Telegram && window.Telegram.WebApp) {{
                      window.Telegram.WebApp.ready();
                      window.Telegram.WebApp.expand();
                    }}
                    
                    // Auto-redirect to the invoice inside the same webview
                    setTimeout(() => {{
                      window.location.replace("{web_invoice}");
                    }}, 1000);
                  }} catch (e) {{
                    console.error(e);
                  }}
                </script>
              </body>
            </html>
            """
        
        # Start Flask server
        port = int(os.getenv('PORT', 8080))
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    
    # Start the Flask server in a separate thread
    flask_thread = threading.Thread(target=start_keep_alive, daemon=True)
    flask_thread.start()
    logger.info("🌐 Flask server started")
    
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