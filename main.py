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

# CryptoBot configuration
CRYPTOBOT_API_TOKEN = os.environ.get("CRYPTOBOT_API_TOKEN")
CRYPTOBOT_USD_ASSET = os.environ.get("CRYPTOBOT_USD_ASSET", "LTC")
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

# --- Message Prioritization System ---
import uuid

def generate_request_id() -> str:
    """Generate a unique request ID for amount input prioritization"""
    return f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

async def set_pending_amount_request(context: ContextTypes.DEFAULT_TYPE, state: str, prompt_type: str) -> str:
    """Set a new pending amount request and return its ID"""
    request_id = generate_request_id()
    context.user_data['pending_amount_request'] = {
        'id': request_id,
        'state': state,
        'type': prompt_type,
        'timestamp': time.time()
    }
    logger.info(f"Set pending amount request: {request_id} for state {state}")
    return request_id

async def validate_amount_request(context: ContextTypes.DEFAULT_TYPE, expected_state: str) -> bool:
    """Check if the current amount input is for the latest request"""
    pending = context.user_data.get('pending_amount_request')
    if not pending:
        return True  # No pending request, allow
    
    if pending.get('state') != expected_state:
        # Different state - newer request has taken priority
        return False
    
    # Check if request is too old (5 minutes timeout)
    if time.time() - pending.get('timestamp', 0) > 300:
        context.user_data.pop('pending_amount_request', None)
        return False
    
    return True

async def clear_amount_request(context: ContextTypes.DEFAULT_TYPE):
    """Clear the pending amount request"""
    context.user_data.pop('pending_amount_request', None)

async def send_priority_message(update: Update, prompt_type: str) -> None:
    """Send a message when a newer request has taken priority"""
    await update.message.reply_text(
        f"⚠️ **Request Superseded**\n\n"
        f"A newer {prompt_type} request is pending.\n"
        f"Please respond to the latest prompt or use the menu buttons to navigate.",
        parse_mode=ParseMode.MARKDOWN
    )

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

# --- Supported Crypto Assets ---
# Only allow LTC, TON, SOL
SUPPORTED_CRYPTO_ASSETS = ["LTC", "TON", "SOL"]

CRYPTO_ADDRESS_PATTERNS = {
    'LTC': r'^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$|^ltc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{39,59}$',
    'TON': r'^UQ[a-zA-Z0-9_-]{46,}$',
    'SOL': r'^[1-9A-HJ-NP-Za-km-z]{32,44}$',
}



async def create_crypto_invoice(asset: str, amount: float, user_id: int, payload: dict = None) -> dict:
    """Create a crypto invoice using CryptoBot API for native mini app experience."""
    if not CRYPTOBOT_API_TOKEN:
        return {"ok": False, "error": "CryptoBot API token not configured"}
    
    try:
        headers = {
            'Crypto-Pay-API-Token': CRYPTOBOT_API_TOKEN,
            'Content-Type': 'application/json'
        }
        
        # Get USD amount for description
        usd_rate = await get_crypto_usd_rate(asset)
        usd_amount = amount * usd_rate if usd_rate > 0 else amount
        
        # createPayment API data structure (different from createInvoice)
        data = {
            'asset': asset,
            'amount': f"{amount:.8f}",
            'description': f'Casino deposit - ${usd_amount:.2f} USD',
            'hidden_message': str(user_id),  # Used to identify user in webhook
            'expires_in': 3600,  # 1 hour expiration
            'allow_comments': False,
            'allow_anonymous': False,
        }
        
        if payload:
            data.update(payload)
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post('https://pay.crypt.bot/api/createInvoice', 
                                  headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('ok'):
                        logger.info(f"CryptoBot invoice created successfully: {result.get('result', {}).get('invoice_id')}")
                        return result
                    else:
                        logger.error(f"CryptoBot API returned error: {result}")
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

async def get_bot_username() -> str:
    """Get bot username, cached for performance."""
    # This would normally be cached, but for simplicity:
    return "AxisCasinoBot"

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
    # Check if API token is configured
    if not CRYPTOBOT_API_TOKEN:
        logger.error("CRYPTOBOT_API_TOKEN not configured - unable to fetch live rates")
        return 0.0
    
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
                                        logger.info(f"CryptoBot API: {asset}/USD rate = ${price:.6f}")
                                        return price
                            logger.warning(f"CryptoBot API: No rate found for {asset}/USD in response")
                            rate_pairs = [f"{r.get('source')}/{r.get('target')}" for r in rates]
                            logger.debug(f"Available rates: {rate_pairs}")
                        else:
                            error_msg = data.get("error", {}).get("name", "Unknown API error")
                            logger.error(f"CryptoBot API error: {error_msg} (attempt {attempt + 1}/{max_retries})")
                    elif resp.status == 401:
                        logger.error(f"CryptoBot API: Invalid API token (HTTP 401)")
                        return 0.0  # Don't retry on auth errors
                    elif resp.status == 403:
                        logger.error(f"CryptoBot API: Access forbidden (HTTP 403)")
                        return 0.0  # Don't retry on permission errors
                    else:
                        logger.error(f"CryptoBot API error: HTTP {resp.status} (attempt {attempt + 1}/{max_retries})")
                        
        except asyncio.TimeoutError:
            logger.error(f"CryptoBot API timeout (attempt {attempt + 1}/{max_retries})")
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching CryptoBot rate for {asset} (attempt {attempt + 1}/{max_retries}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching CryptoBot rate for {asset} (attempt {attempt + 1}/{max_retries}): {e}")
            
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
            
            # House balance table (casino funds tracking)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS house_balance (
                    id INTEGER PRIMARY KEY,
                    balance REAL DEFAULT 10000.0,
                    total_player_losses REAL DEFAULT 0.0,
                    total_player_wins REAL DEFAULT 0.0,
                    total_deposits REAL DEFAULT 0.0,
                    total_withdrawals REAL DEFAULT 0.0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Initialize house balance if it doesn't exist
            await db.execute("""
                INSERT OR IGNORE INTO house_balance (id, balance) VALUES (1, 10000.0)
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

# --- House Balance System ---

async def get_house_balance() -> dict:
    """Get current house balance data"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM house_balance WHERE id = 1
            """)
            result = await cursor.fetchone()
            
            if result:
                return dict(result)
            else:
                # Initialize if not exists
                await db.execute("""
                    INSERT INTO house_balance (id, balance) VALUES (1, 10000.0)
                """)
                await db.commit()
                return {
                    'id': 1,
                    'balance': 10000.0,
                    'total_player_losses': 0.0,
                    'total_player_wins': 0.0,
                    'total_deposits': 0.0,
                    'total_withdrawals': 0.0,
                    'last_updated': datetime.now().isoformat()
                }
                
    except Exception as e:
        logger.error(f"Error getting house balance: {e}")
        return {
            'balance': 10000.0,
            'total_player_losses': 0.0,
            'total_player_wins': 0.0,
            'total_deposits': 0.0,
            'total_withdrawals': 0.0
        }

async def update_house_balance_on_game(bet_amount: float, win_amount: float) -> bool:
    """Update house balance based on game outcome"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Calculate house profit/loss
            house_change = bet_amount - win_amount  # Positive = house wins, Negative = house loses
            
            await db.execute("""
                UPDATE house_balance 
                SET balance = balance + ?,
                    total_player_losses = total_player_losses + ?,
                    total_player_wins = total_player_wins + ?,
                    last_updated = ?
                WHERE id = 1
            """, (house_change, bet_amount, win_amount, datetime.now().isoformat()))
            
            await db.commit()
            logger.debug(f"House balance updated: {house_change:+.2f} (bet: {bet_amount}, win: {win_amount})")
            return True
            
    except Exception as e:
        logger.error(f"Error updating house balance on game: {e}")
        return False

async def update_house_balance_on_deposit(amount: float) -> bool:
    """Update house balance when user deposits (house gains funds)"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE house_balance 
                SET balance = balance + ?,
                    total_deposits = total_deposits + ?,
                    last_updated = ?
                WHERE id = 1
            """, (amount, amount, datetime.now().isoformat()))
            
            await db.commit()
            logger.debug(f"House balance increased by deposit: +{amount:.2f}")
            return True
            
    except Exception as e:
        logger.error(f"Error updating house balance on deposit: {e}")
        return False

async def update_house_balance_on_withdrawal(amount: float) -> bool:
    """Update house balance when user withdraws (house loses funds)"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE house_balance 
                SET balance = balance - ?,
                    total_withdrawals = total_withdrawals + ?,
                    last_updated = ?
                WHERE id = 1
            """, (amount, amount, datetime.now().isoformat()))
            
            await db.commit()
            logger.debug(f"House balance decreased by withdrawal: -{amount:.2f}")
            return True
            
    except Exception as e:
        logger.error(f"Error updating house balance on withdrawal: {e}")
        return False

async def get_house_profit_loss() -> dict:
    """Calculate house profit/loss statistics"""
    try:
        house_data = await get_house_balance()
        
        total_in = house_data.get('total_deposits', 0.0)
        total_out = house_data.get('total_withdrawals', 0.0) + house_data.get('total_player_wins', 0.0)
        total_received = house_data.get('total_player_losses', 0.0)
        
        net_profit = total_received + total_in - total_out
        house_edge = (total_received / (total_received + house_data.get('total_player_wins', 0.001))) * 100 if (total_received + house_data.get('total_player_wins', 0)) > 0 else 0
        
        return {
            'current_balance': house_data.get('balance', 0.0),
            'total_deposits': total_in,
            'total_withdrawals': house_data.get('total_withdrawals', 0.0),
            'total_player_losses': total_received,
            'total_player_wins': house_data.get('total_player_wins', 0.0),
            'net_profit': net_profit,
            'house_edge_percent': house_edge
        }
        
    except Exception as e:
        logger.error(f"Error calculating house profit/loss: {e}")
        return {
            'current_balance': 0.0,
            'total_deposits': 0.0,
            'total_withdrawals': 0.0,
            'total_player_losses': 0.0,
            'total_player_wins': 0.0,
            'net_profit': 0.0,
            'house_edge_percent': 0.0
        }

async def update_balance_with_house(user_id: int, bet_amount: float, win_amount: float) -> bool:
    """Update user balance and house balance for game outcomes"""
    try:
        # Update user balance with net result
        net_result = win_amount - bet_amount
        user_updated = await update_balance(user_id, net_result)
        
        # Update house balance
        house_updated = await update_house_balance_on_game(bet_amount, win_amount)
        
        return user_updated and house_updated
        
    except Exception as e:
        logger.error(f"Error updating balances for game: {e}")
        return False

async def deduct_balance_with_house(user_id: int, bet_amount: float) -> bool:
    """Deduct balance for game bet and update house balance"""
    try:
        # Deduct from user
        user_updated = await deduct_balance(user_id, bet_amount)
        
        if user_updated:
            # Update house balance (house gains the bet amount, user wins 0)
            house_updated = await update_house_balance_on_game(bet_amount, 0.0)
            return house_updated
        
        return False
        
    except Exception as e:
        logger.error(f"Error deducting balance with house update: {e}")
        return False

# --- Deposit/Withdrawal House Balance Integration ---

async def process_deposit_with_house_balance(user_id: int, amount: float) -> bool:
    """Process a user deposit and update house balance"""
    try:
        # Update user balance
        user_updated = await update_balance(user_id, amount)
        
        if user_updated:
            # Update house balance (house gains funds from deposit)
            house_updated = await update_house_balance_on_deposit(amount)
            return house_updated
        
        return False
        
    except Exception as e:
        logger.error(f"Error processing deposit with house balance: {e}")
        return False

async def process_withdrawal_with_house_balance(user_id: int, amount: float) -> bool:
    """Process a user withdrawal and update house balance"""
    try:
        # Deduct from user balance
        user_updated = await deduct_balance(user_id, amount)
        
        if user_updated:
            # Update house balance (house loses funds from withdrawal)
            house_updated = await update_house_balance_on_withdrawal(amount)
            return house_updated
        
        return False
        
    except Exception as e:
        logger.error(f"Error processing withdrawal with house balance: {e}")
        return False

# --- House Balance Display Helper ---

async def get_house_balance_display() -> str:
    """Get formatted house balance information for owner panel"""
    try:
        house_stats = await get_house_profit_loss()
        
        balance_str = await format_usd(house_stats['current_balance'])
        deposits_str = await format_usd(house_stats['total_deposits'])
        withdrawals_str = await format_usd(house_stats['total_withdrawals'])
        player_losses_str = await format_usd(house_stats['total_player_losses'])
        player_wins_str = await format_usd(house_stats['total_player_wins'])
        net_profit_str = await format_usd(house_stats['net_profit'])
        house_edge = house_stats['house_edge_percent']
        
        profit_emoji = "📈" if house_stats['net_profit'] >= 0 else "📉"
        
        return f"""
🏦 <b>HOUSE BALANCE</b> 🏦

💰 <b>Current Balance:</b> {balance_str}
{profit_emoji} <b>Net Profit:</b> {net_profit_str}
🎯 <b>House Edge:</b> {house_edge:.2f}%

💳 <b>Deposits:</b> {deposits_str}
🏦 <b>Withdrawals:</b> {withdrawals_str}
📉 <b>Paid to Players:</b> {player_wins_str}
📈 <b>From Players:</b> {player_losses_str}

<i>Real-time casino financial tracking</i>
"""
        
    except Exception as e:
        logger.error(f"Error getting house balance display: {e}")
        return "❌ <b>House Balance:</b> Unable to load data"

# --- Weekly Bonus Helpers ---
WEEKLY_BONUS_AMOUNT = float(os.environ.get("WEEKLY_BONUS_AMOUNT", "5.0"))
WEEKLY_BONUS_INTERVAL = 7  # days

# --- Referral System Configuration ---
REFERRAL_BONUS_REFERRER = float(os.environ.get("REFERRAL_BONUS_REFERRER", "10.0"))  # Bonus for person who refers
REFERRAL_BONUS_REFEREE = float(os.environ.get("REFERRAL_BONUS_REFERRER", "5.0"))    # Bonus for new user
REFERRAL_MIN_DEPOSIT = float(os.environ.get("REFERRAL_MIN_DEPOSIT", "10.0"))       # Min deposit to activate referral
MAX_REFERRALS_PER_USER = int(os.environ.get("MAX_REFERRALS_PER_USER", "50"))       # Max referrals per user

async def ensure_weekly_bonus_column():
    """Ensure weekly bonus column exists in users table"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("ALTER TABLE users ADD COLUMN last_weekly_bonus TEXT DEFAULT NULL")
            await db.commit()
    except Exception:
        pass  # Column already exists

async def ensure_referral_columns():
    """Ensure referral system columns exist"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Add referral columns to users table
            await db.execute("ALTER TABLE users ADD COLUMN referral_code TEXT DEFAULT NULL")
            await db.execute("ALTER TABLE users ADD COLUMN referred_by TEXT DEFAULT NULL")
            await db.execute("ALTER TABLE users ADD COLUMN referral_earnings REAL DEFAULT 0.0")
            await db.execute("ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0")
            
            # Create referrals table if it doesn't exist
            await db.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referee_id INTEGER NOT NULL,
                    referral_code TEXT NOT NULL,
                    bonus_paid REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    activated_at TIMESTAMP DEFAULT NULL,
                    FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                    FOREIGN KEY (referee_id) REFERENCES users (user_id)
                )
            """)
            await db.commit()
    except Exception as e:
        logger.error(f"Error ensuring referral columns: {e}")

async def can_claim_weekly_bonus(user_id: int) -> Tuple[bool, Optional[int]]:
    """Check if user can claim weekly bonus. Returns (can_claim, seconds_remaining)."""
    user = await get_user(user_id)
    if not user:
        return False, None
    
    last_claim = user.get('last_weekly_bonus')
    if not last_claim:
        return True, None
    
    last_dt = datetime.fromisoformat(last_claim)
    now = datetime.now()
    delta = now - last_dt
    if delta.days >= WEEKLY_BONUS_INTERVAL:
        return True, None
    
    seconds_remaining = (WEEKLY_BONUS_INTERVAL * 86400) - int(delta.total_seconds())
    return False, seconds_remaining

async def claim_weekly_bonus(user_id: int) -> bool:
    """Grant the weekly bonus and update last_weekly_bonus."""
    try:
        success = await update_balance(user_id, WEEKLY_BONUS_AMOUNT)
        if success:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("""
                    UPDATE users SET last_weekly_bonus = ? WHERE user_id = ?
                """, (datetime.now().isoformat(), user_id))
                await db.commit()
        return success
    except Exception as e:
        logger.error(f"Error claiming weekly bonus: {e}")
        return False

# --- Referral System Helpers ---

def generate_referral_code(user_id: int) -> str:
    """Generate a unique referral code for a user."""
    import time
    import random
    import hashlib
    
    # Create a base from user_id and current timestamp
    base = f"{user_id}_{int(time.time())}_{random.randint(1000, 9999)}"
    hash_obj = hashlib.md5(base.encode())
    
    # Take first 8 characters and make it alphanumeric
    code = hash_obj.hexdigest()[:6].upper()
    return f"REF{code}"

async def get_or_create_referral_code(user_id: int) -> str:
    """Get existing referral code or create a new one."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT referral_code FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0]
            
            # Create new code
            code = generate_referral_code(user_id)
            await db.execute("UPDATE users SET referral_code = ? WHERE user_id = ?", (code, user_id))
            await db.commit()
            return code
    except Exception as e:
        logger.error(f"Error getting/creating referral code: {e}")
        return generate_referral_code(user_id)

async def get_referral_stats(user_id: int) -> dict:
    """Get referral statistics for a user."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Get user's referral data
            cursor = await db.execute("""
                SELECT referral_earnings, referral_count FROM users WHERE user_id = ?
            """, (user_id,))
            row = await cursor.fetchone()
            earnings = row[0] if row else 0.0
            count = row[1] if row else 0
            
            # Get recent referrals
            cursor = await db.execute("""
                SELECT r.referee_id, u.username, r.created_at, r.bonus_paid
                FROM referrals r
                JOIN users u ON r.referee_id = u.user_id
                WHERE r.referrer_id = ?
                ORDER BY r.created_at DESC
                LIMIT 10
            """, (user_id,))
            recent_refs = await cursor.fetchall()
            
            return {
                'earnings': earnings,
                'count': count,
                'recent': [{'user_id': r[0], 'username': r[1], 'date': r[2], 'bonus': r[3]} for r in recent_refs]
            }
    except Exception as e:
        logger.error(f"Error getting referral stats: {e}")
        return {'earnings': 0.0, 'count': 0, 'recent': []}

async def process_referral(referee_id: int, referral_code: str) -> bool:
    """Process a new referral when user registers with a code."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Find referrer by code
            cursor = await db.execute("SELECT user_id FROM users WHERE referral_code = ?", (referral_code,))
            row = await cursor.fetchone()
            if not row:
                return False
            
            referrer_id = row[0]
            if referrer_id == referee_id:
                return False  # Can't refer yourself
            
            # Check if referee was already referred
            cursor = await db.execute("SELECT referred_by FROM users WHERE user_id = ?", (referee_id,))
            row = await cursor.fetchone()
            if row and row[0]:
                return False  # Already referred
            
            # Update referee with referrer info
            await db.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referral_code, referee_id))
            
            # Create referral record
            await db.execute("""
                INSERT INTO referrals (referrer_id, referee_id, referral_code, status)
                VALUES (?, ?, ?, 'active')
            """, (referrer_id, referee_id, referral_code))
            
            # Give bonuses
            await update_balance(referee_id, REFERRAL_BONUS_REFERRER)
            await update_balance(referrer_id, REFERRAL_BONUS_REFERRER)
            
            # Update referrer stats
            await db.execute("""
                UPDATE users 
                SET referral_count = referral_count + 1,
                    referral_earnings = referral_earnings + ?
                WHERE user_id = ?
            """, (REFERRAL_BONUS_REFERRER, referrer_id))
            
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Error processing referral: {e}")
        return False

# --- Main Bot Handlers ---

# Global utility functions for conversation handlers
async def global_fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any unexpected messages during conversation"""
    # Clear any stale conversation state
    context.user_data.clear()
    
    # If it's a callback query, answer it
    if update.callback_query:
        await update.callback_query.answer()
        
    # Return to main menu
    if update.callback_query:
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]]
        await update.callback_query.edit_message_text(
            "🔄 Returning to main menu...",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.message:
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]]
        await update.message.reply_text(
            "🔄 Returning to main menu...",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    return ConversationHandler.END

async def cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current game and return to games menu"""
    context.user_data.clear()  # Clear all states
    if update.callback_query:
        await update.callback_query.answer()
        keyboard = [[InlineKeyboardButton("🎮 Games", callback_data="mini_app_centre")]]
        await update.callback_query.edit_message_text(
            "🎮 Game cancelled. Choose another game:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    return ConversationHandler.END

async def handle_text_input_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text input for deposit/withdrawal states only - ignore game states to prevent interference."""
    # Only handle specific deposit/withdrawal states, not game states
    if 'awaiting_deposit_amount' in context.user_data:
        await handle_deposit_amount_input(update, context)
    elif 'awaiting_withdraw_amount' in context.user_data:
        await handle_withdraw_amount_input(update, context)
    elif 'awaiting_withdraw_address' in context.user_data:
        await handle_withdraw_address_input(update, context)
    else:
        # Ignore text messages that don't match any expected state
        # This prevents interference with conversation handlers for games
        # Log ignored input for debugging
        logger.debug(f"Ignored text input from user {update.effective_user.id}: {update.message.text}")

# --- Deposit/Withdrawal Handlers ---

async def deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle deposit button - show deposit options."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Clear any previous states to prevent interference
    context.user_data.clear()
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text(
            "❌ User not found. Please use /start to register first.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Start", callback_data="main_panel")]])
        )
        return
    
    balance_str = await format_usd(user['balance'])
    
    text = f"""
💳 <b>DEPOSIT FUNDS</b> 💳

💰 <b>Current Balance:</b> {balance_str}

🔒 <b>Secure Payment Methods:</b>
We accept Litecoin (LTC) deposits for fast and secure transactions.

• <b>Cryptocurrency:</b> Instant deposits with low fees
• <b>Minimum:</b> $1.00 USD equivalent
• <b>Processing:</b> Usually within minutes

💡 <b>Why choose Litecoin?</b>
✅ Fast processing times
✅ Lower transaction fees
✅ Enhanced privacy
✅ 24/7 availability
"""
    
    keyboard = [
        [InlineKeyboardButton("🪙 Deposit Litecoin (LTC)", callback_data="deposit_LTC")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def deposit_crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle specific crypto deposit selection."""
    query = update.callback_query
    await query.answer()
    
    # Extract crypto type from callback data
    crypto_type = query.data.split("_")[1]  # deposit_LTC -> LTC
    user_id = query.from_user.id
    
    # Clear previous states and set the crypto type in context for the conversation
    context.user_data.clear()
    context.user_data['deposit_crypto'] = crypto_type
    
    # Get current rate
    rate = await get_crypto_usd_rate(crypto_type)
    rate_text = f"${rate:.4f}" if rate > 0 else "Rate unavailable"
    
    text = f"""
💰 <b>DEPOSIT {crypto_type}</b> 💰

📊 <b>Current Rate:</b> 1 {crypto_type} = {rate_text} USD

💵 <b>Enter Deposit Amount</b>
Please type the amount you want to deposit in USD.

<b>Deposit Limits:</b>
• Minimum: $1.00 USD
• Maximum: $10,000.00 USD per transaction

💡 <i>Simply type your amount in USD (e.g., type "50" for $50.00)</i>

⌨️ <b>Waiting for your input...</b>
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Deposit", callback_data="deposit")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    # Set state for text input
    context.user_data['awaiting_deposit_amount'] = crypto_type

async def handle_deposit_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input for deposit amount."""
    if 'awaiting_deposit_amount' not in context.user_data:
        return
    
    crypto_type = context.user_data['awaiting_deposit_amount']
    
    try:
        amount_usd = float(update.message.text.replace('$', '').replace(',', ''))
        
        if amount_usd < 1.0:
            await update.message.reply_text("❌ Minimum deposit is $1.00 USD. Please enter a higher amount.")
            return
        
        if amount_usd > 10000.0:
            await update.message.reply_text("❌ Maximum deposit is $10,000.00 USD per transaction. Please enter a lower amount.")
            return
        
        # Clear the state
        del context.user_data['awaiting_deposit_amount']
        
        await process_deposit_payment(update, context, crypto_type, amount_usd)
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number (e.g., 50 for $50).")

async def process_deposit_payment(update, context, crypto_type: str, amount_usd: float):
    """Process deposit payment and create CryptoBot invoice"""
    query = getattr(update, 'callback_query', None)
    
    try:
        # Get current crypto rate
        rate = await get_crypto_usd_rate(crypto_type)
        if rate <= 0:
            error_text = "❌ Unable to get current exchange rate. Please try again later."
            if query:
                await query.edit_message_text(error_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="deposit")]]))
            else:
                await update.message.reply_text(error_text)
            return
        
        # Calculate crypto amount needed
        crypto_amount = amount_usd / rate
        user_id = query.from_user.id if query else update.message.from_user.id
        
        # Create invoice using CryptoBot
        invoice_data = await create_crypto_invoice(crypto_type, crypto_amount, user_id)
        
        if not invoice_data.get('ok'):
            error_text = f"❌ Unable to create payment invoice: {invoice_data.get('error', 'Unknown error')}"
            if query:
                await query.edit_message_text(error_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="deposit")]]))
            else:
                await update.message.reply_text(error_text)
            return
        
        invoice = invoice_data['result']
        # Use mini_app_invoice_url for native mini app integration within Telegram
        payment_url = invoice.get('mini_app_invoice_url') or invoice.get('web_app_invoice_url') or invoice.get('bot_invoice_url')
        
        text = f"""
💰 <b>CRYPTO PAY INVOICE READY</b> 💰

📊 <b>Payment Details:</b>
• Amount: <b>${amount_usd:.2f} USD</b>
• Crypto: <b>{crypto_amount:.8f} {crypto_type}</b>
• Rate: <b>${rate:.4f}</b> per {crypto_type}
• Invoice ID: <code>{invoice['invoice_id']}</code>

💳 <b>Pay with CryptoBot Mini App:</b>
Click the button below to open the secure payment interface directly within this bot.

⏰ <b>Expires in 1 hour</b>
🔔 <i>You'll be notified instantly when payment is confirmed!</i>
"""
        
        keyboard = [
            [InlineKeyboardButton("💳 Pay with CryptoBot", url=payment_url)],
            [InlineKeyboardButton("🔄 Check Payment Status", callback_data=f"check_payment_{invoice['invoice_id']}")],
            [InlineKeyboardButton("🔙 Back to Deposit", callback_data="deposit")]
        ]
        
        if query:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
            
    except Exception as e:
        logger.error(f"Error processing deposit payment: {e}")
        error_text = "❌ An error occurred while creating the payment. Please try again."
        if query:
            await query.edit_message_text(error_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="deposit")]]))
        else:
            await update.message.reply_text(error_text)

async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the withdrawal process."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Clear any previous states to prevent interference
    context.user_data.clear()
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text(
            "❌ User not found. Please use /start to register first.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Start", callback_data="main_panel")]])
        )
        return
    
    balance = user['balance']
    if balance < MIN_WITHDRAWAL_USD:
        await query.edit_message_text(
            f"❌ Insufficient balance for withdrawal.\n\n"
            f"💰 <b>Your Balance:</b> {await format_usd(balance)}\n"
            f"💵 <b>Minimum Withdrawal:</b> {await format_usd(MIN_WITHDRAWAL_USD)}\n\n"
            f"💡 <i>Make a deposit or play games to increase your balance!</i>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Deposit", callback_data="deposit")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
            ]),
            parse_mode=ParseMode.HTML
        )
        return
    
    fee_amount = calculate_withdrawal_fee(balance)
    max_withdrawal = min(balance - fee_amount, MAX_WITHDRAWAL_USD)
    
    text = f"""
🏦 <b>WITHDRAW FUNDS</b> 🏦

💰 <b>Current Balance:</b> {await format_usd(balance)}
💸 <b>Available to Withdraw:</b> {await format_usd(max_withdrawal)}

📋 <b>Withdrawal Limits:</b>
• Minimum: {await format_usd(MIN_WITHDRAWAL_USD)}
• Maximum: {await format_usd(MAX_WITHDRAWAL_USD)} per transaction
• Daily Limit: {await format_usd(MAX_WITHDRAWAL_USD_DAILY)}
• Fee: {WITHDRAWAL_FEE_PERCENT}% (min ${MIN_WITHDRAWAL_FEE:.2f})

🔒 <b>Supported Cryptocurrency:</b>
We support Litecoin (LTC) withdrawals for fast and secure transactions.

⏰ <b>Processing Time:</b> Usually within 24 hours
"""
    
    keyboard = [
        [InlineKeyboardButton("🪙 Withdraw Litecoin (LTC)", callback_data="withdraw_LTC")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def withdraw_crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle crypto withdrawal selection."""
    query = update.callback_query
    await query.answer()
    
    crypto_type = query.data.split("_")[1]  # withdraw_LTC -> LTC
    user_id = query.from_user.id
    
    user = await get_user(user_id)
    balance = user['balance']
    
    # Calculate available amount after fees
    fee_amount = calculate_withdrawal_fee(balance)
    max_withdrawal = min(balance - fee_amount, MAX_WITHDRAWAL_USD)
    
    # Get current rate
    rate = await get_crypto_usd_rate(crypto_type)
    rate_text = f"${rate:.4f}" if rate > 0 else "Rate unavailable"
    
    context.user_data['withdraw_crypto'] = crypto_type
    
    text = f"""
🏦 <b>WITHDRAW {crypto_type}</b> 🏦

💰 <b>Your Balance:</b> {await format_usd(balance)}
💸 <b>Available:</b> {await format_usd(max_withdrawal)}
📊 <b>Current Rate:</b> 1 {crypto_type} = {rate_text} USD

💵 <b>Enter Withdrawal Amount</b>
Please enter the amount you want to withdraw in USD.

<b>Important:</b>
• Fee: {WITHDRAWAL_FEE_PERCENT}% (minimum ${MIN_WITHDRAWAL_FEE:.2f})
• Minimum: {await format_usd(MIN_WITHDRAWAL_USD)}
• Maximum: {await format_usd(max_withdrawal)}

💡 <i>Enter amount in USD (e.g., 50 for $50)</i>
"""
    
    keyboard = [
        [InlineKeyboardButton("💸 Quick: $10", callback_data=f"withdraw_amount_{crypto_type}_10")],
        [InlineKeyboardButton("💸 Quick: $25", callback_data=f"withdraw_amount_{crypto_type}_25"),
         InlineKeyboardButton("💸 Quick: $50", callback_data=f"withdraw_amount_{crypto_type}_50")],
        [InlineKeyboardButton("💸 Quick: $100", callback_data=f"withdraw_amount_{crypto_type}_100")],
        [InlineKeyboardButton(f"💸 Max: {await format_usd(max_withdrawal)}", callback_data=f"withdraw_amount_{crypto_type}_{max_withdrawal}")],
        [InlineKeyboardButton("🔙 Back to Withdraw", callback_data="withdraw")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    # Set state for text input
    context.user_data['awaiting_withdraw_amount'] = crypto_type

async def handle_withdraw_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text input for withdrawal amount."""
    if 'awaiting_withdraw_amount' not in context.user_data:
        return
    
    crypto_type = context.user_data['awaiting_withdraw_amount']
    user_id = update.effective_user.id
    
    try:
        amount_usd = float(update.message.text.replace('$', '').replace(',', ''))
        
        user = await get_user(user_id)
        balance = user['balance']
        
        if amount_usd < MIN_WITHDRAWAL_USD:
            await update.message.reply_text(f"❌ Minimum withdrawal is {await format_usd(MIN_WITHDRAWAL_USD)}. Please enter a higher amount.")
            return
        
        fee_amount = calculate_withdrawal_fee(amount_usd)
        total_needed = amount_usd + fee_amount
        
        if total_needed > balance:
            await update.message.reply_text(
                f"❌ Insufficient balance.\n\n"
                f"💰 Your Balance: {await format_usd(balance)}\n"
                f"💸 Withdrawal Amount: {await format_usd(amount_usd)}\n"
                f"💵 Fee: {await format_usd(fee_amount)}\n"
                f"🏦 Total Needed: {await format_usd(total_needed)}"
            )
            return
        
        if amount_usd > MAX_WITHDRAWAL_USD:
            await update.message.reply_text(f"❌ Maximum withdrawal is {await format_usd(MAX_WITHDRAWAL_USD)} per transaction.")
            return
        
        # Clear the state and set amount
        del context.user_data['awaiting_withdraw_amount']
        context.user_data['withdraw_amount'] = amount_usd
        
        # Ask for address
        text = f"""
🏦 <b>WITHDRAWAL ADDRESS</b> 🏦

💰 <b>Amount:</b> {await format_usd(amount_usd)}
💵 <b>Fee:</b> {await format_usd(fee_amount)}
🏦 <b>You'll Receive:</b> {await format_usd(amount_usd)}
🪙 <b>Asset:</b> {crypto_type}

📝 <b>Enter {crypto_type} Address</b>
Please enter your {crypto_type} wallet address.

⚠️ <b>Important:</b> Double-check your address!
"""
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        
        # Set state for address input
        context.user_data['awaiting_withdraw_address'] = crypto_type
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number (e.g., 50 for $50).")

async def handle_withdraw_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text input for withdrawal address."""
    if 'awaiting_withdraw_address' not in context.user_data:
        return
    
    crypto_type = context.user_data['awaiting_withdraw_address']
    amount_usd = context.user_data.get('withdraw_amount', 0)
    address = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Validate address format
    if not validate_crypto_address(address, crypto_type):
        await update.message.reply_text(
            f"❌ Invalid {crypto_type} address format. Please check and try again."
        )
        return
    
    # Calculate amounts
    fee_amount = calculate_withdrawal_fee(amount_usd)
    rate = await get_crypto_usd_rate(crypto_type)
    crypto_amount = amount_usd / rate if rate > 0 else 0
    
    # Show confirmation
    text = f"""
🏦 <b>CONFIRM WITHDRAWAL</b> 🏦

💰 <b>Amount:</b> {await format_usd(amount_usd)}
💵 <b>Fee:</b> {await format_usd(fee_amount)}
🏦 <b>Total Deducted:</b> {await format_usd(amount_usd + fee_amount)}

🪙 <b>You'll Receive:</b> {crypto_amount:.8f} {crypto_type}
📊 <b>Rate:</b> ${rate:.4f} per {crypto_type}

📍 <b>Address:</b>
<code>{address}</code>

⚠️ <b>Warning:</b> This action cannot be undone!
Please verify all details are correct.

⏰ <b>Processing:</b> Usually completed within 24 hours
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm Withdrawal", callback_data="confirm_withdrawal")],
        [InlineKeyboardButton("❌ Cancel", callback_data="withdraw")]
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    # Store all data for confirmation
    context.user_data['withdraw_address'] = address
    context.user_data['withdraw_crypto'] = crypto_type
    context.user_data['withdraw_fee'] = fee_amount
    context.user_data['withdraw_crypto_amount'] = crypto_amount
    
    # Clear the awaiting state
    del context.user_data['awaiting_withdraw_address']

async def confirm_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process the confirmed withdrawal."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Get withdrawal data
    crypto_type = context.user_data.get('withdraw_crypto')
    amount_usd = context.user_data.get('withdraw_amount')
    address = context.user_data.get('withdraw_address')
    fee_amount = context.user_data.get('withdraw_fee')
    crypto_amount = context.user_data.get('withdraw_crypto_amount')
    
    if not all([crypto_type, amount_usd, address, fee_amount]):
        await query.edit_message_text(
            "❌ Missing withdrawal data. Please start over.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏦 Withdraw", callback_data="withdraw")]])
        )
        return
    
    try:
        # Check balance again
        user = await get_user(user_id)
        total_needed = amount_usd + fee_amount
        
        if user['balance'] < total_needed:
            await query.edit_message_text(
                f"❌ Insufficient balance. Your balance may have changed.\n\n"
                f"💰 Current Balance: {await format_usd(user['balance'])}\n"
                f"🏦 Required: {await format_usd(total_needed)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏦 Withdraw", callback_data="withdraw")]]),
                parse_mode=ParseMode.HTML
            )
            return
        
        # Process withdrawal with house balance tracking
        success = await process_withdrawal_with_house_balance(user_id, total_needed)
        if not success:
            await query.edit_message_text(
                "❌ Failed to process withdrawal. Please try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏦 Withdraw", callback_data="withdraw")]])
            )
            return
        
        # Log withdrawal
        withdrawal_id = await log_withdrawal(user_id, crypto_type, amount_usd, address, fee_amount, amount_usd)
        
        # In demo mode or if sending fails, mark as completed for testing
        if DEMO_MODE:
            await update_withdrawal_status(withdrawal_id, "completed", f"DEMO_{withdrawal_id}", "")
            status_text = "✅ <b>Demo withdrawal completed!</b>"
        else:
            # Try to send crypto
            send_result = await send_crypto(address, crypto_amount, f"Withdrawal from casino", crypto_type)
            
            if send_result.get('ok'):
                tx_hash = send_result.get('result', {}).get('transaction_hash', 'pending')
                await update_withdrawal_status(withdrawal_id, "completed", tx_hash, "")
                status_text = "✅ <b>Withdrawal sent successfully!</b>"
            else:
                error_msg = send_result.get('error', 'Unknown error')
                await update_withdrawal_status(withdrawal_id, "failed", "", error_msg)
                status_text = f"❌ <b>Withdrawal failed:</b> {error_msg}"
        
        # Update user withdrawal limits
        if not DEMO_MODE:
            await update_withdrawal_limits(user_id, amount_usd)
        
        # Clear context data
        for key in ['withdraw_crypto', 'withdraw_amount', 'withdraw_address', 'withdraw_fee', 'withdraw_crypto_amount']:
            context.user_data.pop(key, None)
        
        # Get updated balance
        updated_user = await get_user(user_id)
        new_balance = await format_usd(updated_user['balance'])
        
        text = f"""
🏦 <b>WITHDRAWAL PROCESSED</b> 🏦

{status_text}

💰 <b>Amount:</b> {await format_usd(amount_usd)}
🪙 <b>Crypto:</b> {crypto_amount:.8f} {crypto_type}
💵 <b>Fee:</b> {await format_usd(fee_amount)}
📍 <b>Address:</b> <code>{address}</code>

💰 <b>New Balance:</b> {new_balance}
🆔 <b>Transaction ID:</b> #{withdrawal_id}

⏰ <b>Processing Time:</b> Usually within 24 hours
💌 You'll receive updates on the transaction status.
"""
        
        keyboard = [
            [InlineKeyboardButton("💰 Balance", callback_data="show_balance")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error processing withdrawal: {e}")
        await query.edit_message_text(
            "❌ An error occurred while processing your withdrawal. Please contact support.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🆘 Support", callback_data="support")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
            ])
        )

# --- Main Bot Setup and Entry Point ---

async def async_main():
    """Async main function to properly start the bot."""
    logger.info("🚀 Starting Telegram Casino Bot...")

    # Initialize database first
    await init_db()
    logger.info("✅ Database initialized")
    
    # Ensure weekly bonus column exists AFTER database is initialized
    await ensure_weekly_bonus_column()
    
    # Ensure referral system columns exist
    await ensure_referral_columns()
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Define handler functions
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command and main panel callback."""
        user = update.effective_user
        user_id = user.id if user else None
        username = user.username or (user.first_name if user else "Guest")
        
        # Clear any previous states to prevent interference
        context.user_data.clear()
        
        # Check for referral code in start parameter
        referral_code = None
        if context.args and len(context.args) > 0:
            arg = context.args[0]
            if arg.startswith("ref_"):
                referral_code = arg[4:]  # Remove "ref_" prefix
        
        # Ensure user exists in DB
        user_data = await get_user(user_id)
        is_new_user = user_data is None
        
        if not user_data:
            await create_user(user_id, username)
            user_data = await get_user(user_id)
            
        # Process referral if this is a new user with a referral code
        referral_message = ""
        if is_new_user and referral_code and update.message:
            success = await process_referral(user_id, referral_code)
            if success:
                referral_message = f"\n\n🎉 <b>Welcome bonus received!</b>\n💰 You got <b>${REFERRAL_BONUS_REFERRER:.2f}</b> for joining through a referral!"
        
        # Get user's current balance for display
        balance_str = await format_usd(user_data['balance']) if user_data else "$0.00"
        
        # Check if user can claim weekly bonus
        can_claim_bonus, _ = await can_claim_weekly_bonus(user_id) if user_id else (False, None)
        bonus_emoji = "🎁✨" if can_claim_bonus else "🎁"
        
        # Create an engaging welcome message
        text = (
            f"🎰 <b>Welcome to Axis Casino, {username}!</b> 🎰\n\n"
            f"💰 <b>Balance:</b> {balance_str}\n"
            f"🏆 Ready to win big? Let's get started!\n\n"
            f"🎮 <b>Play Games</b> • 💳 <b>Manage Funds</b> • {bonus_emoji} <b>Rewards</b>"
            f"{referral_message}"
        )
        
        # Organized keyboard layout with logical grouping
        keyboard = [
            # Main Game Access (Top Priority)
            [InlineKeyboardButton("🎮 🎯 Mini App Centre", callback_data="mini_app_centre")],
            
            # Quick Actions Row
            [
                InlineKeyboardButton("💰 Balance", callback_data="show_balance"),
                InlineKeyboardButton("📊 Stats", callback_data="show_stats")
            ],
            
            # Financial Operations
            [
                InlineKeyboardButton("💳 Deposit", callback_data="deposit"),
                InlineKeyboardButton("🏦 Withdraw", callback_data="withdraw")
            ],
            
            # Rewards & Bonuses
            [
                InlineKeyboardButton(f"{bonus_emoji} Rewards & Bonus", callback_data="rewards_panel")
            ],
            # Support row
            [InlineKeyboardButton("🆘 Support", callback_data="support")]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def show_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the user's current balance with enhanced information."""
        user = update.effective_user
        user_id = user.id if user else None
        if not user_id:
            if update.message:
                await update.message.reply_text("❌ Unable to identify user.")
            elif update.callback_query:
                await update.callback_query.answer("❌ Unable to identify user.", show_alert=True)
            return
    
        user_data = await get_user(user_id)
        if not user_data:
            if update.message:
                await update.message.reply_text("❌ User not found. Please /start first.")
            elif update.callback_query:
                await update.callback_query.answer("❌ User not found. Please /start first.", show_alert=True)
            return
    
        balance_str = await format_usd(user_data['balance'])
        username = user.username or user.first_name or "Player"
        
        # Enhanced balance display with quick actions
        text = (
            f"💰 <b>{username}'s Wallet</b> 💰\n\n"
            f"💵 <b>Current Balance:</b> {balance_str}\n\n"
            f"💡 <i>Ready to grow your balance?</i>\n"
            f"🎮 Play games to win more\n"
            f"💳 Deposit to add funds\n"
            f"🎁 Check for available bonuses"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre"),
                InlineKeyboardButton("💰 Balance", callback_data="show_balance")
            ],
            [
                InlineKeyboardButton("🎁 Rewards", callback_data="rewards_panel"),
                InlineKeyboardButton("💳 Deposit", callback_data="deposit")
            ],
            [InlineKeyboardButton("🏠 ← Back to Menu", callback_data="main_panel")]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def mini_app_centre_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the mini app centre with available games and features."""
        query = update.callback_query
        await query.answer()
        
        # Clear any previous states to prevent interference
        context.user_data.clear()
        
        # Get user data for personalized experience
        user = update.effective_user
        user_id = user.id if user else None
        user_data = await get_user(user_id) if user_id else None
        balance_str = await format_usd(user_data['balance']) if user_data else "$0.00"
        
        # Organized game selection with categories
        keyboard = [
            # Featured/Popular Games (Top Row)
            [
                InlineKeyboardButton("🎰 Slots", callback_data="slots"),
                InlineKeyboardButton("🃏 Blackjack", callback_data="blackjack")
            ],
            
            # Quick Games
            [
                InlineKeyboardButton("🪙 Coin Flip", callback_data="coinflip"),
                InlineKeyboardButton("🎲 Dice Roll", callback_data="dice")
            ],
            
            # Advanced Games
            [
                InlineKeyboardButton("🎡 Roulette", callback_data="roulette"),
                InlineKeyboardButton("🚀 Crash Game", callback_data="crash")
            ],
            
            # Navigation
            [InlineKeyboardButton("🏠 ← Back to Main Menu", callback_data="main_panel")]
        ]
        
        text = (
            "🎮 <b>Welcome to the Game Centre!</b> 🎯\n\n"
            f"💰 <b>Your Balance:</b> {balance_str}\n\n"
            "🎰 <b>Featured Games:</b> Classic casino favorites\n"
            "⚡ <b>Quick Games:</b> Fast-paced instant wins\n"
            "🎪 <b>Advanced Games:</b> Strategic gameplay\n\n"
            "🍀 <i>Good luck and play responsibly!</i>"
        )
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle support/help callback query."""
        query = getattr(update, "callback_query", None)
        if query is not None:
            await query.answer()
            text = (
                "🆘 <b>Support & Help</b> 🆘\n\n"
                "Need assistance? We're here to help!\n\n"
                f"<b>Support Channel:</b> <a href='{SUPPORT_CHANNEL}'>{SUPPORT_CHANNEL}</a>\n"
                "<b>Contact:</b> @casino_support_admin\n\n"
                "• For FAQs, updates, and community help, join our support channel.\n"
                "• For urgent issues, message our support admin.\n\n"
                "<i>We aim to respond as quickly as possible!</i>"
            )
            keyboard = [
                [InlineKeyboardButton("📢 Support Channel", url=SUPPORT_CHANNEL)],
                [InlineKeyboardButton("👤 Contact Admin", url="https://t.me/casino_support_admin")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        else:
            # Handle as a message or send a fallback response
            await update.message.reply_text(
                "Support is available via the main menu or by clicking a button.\n\n" 
                f"<b>Support Channel:</b> <a href='{SUPPORT_CHANNEL}'>{SUPPORT_CHANNEL}</a>\n"
                "<b>Contact:</b> @casino_support_admin",
                parse_mode=ParseMode.HTML
            )

    async def rewards_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the combined rewards and weekly bonus panel."""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = await get_user(user_id)
        if not user:
            await query.edit_message_text(
                "❌ User not found. Please use /start to register first.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Start", callback_data="main_panel")]])
            )
            return

        # Weekly bonus status
        can_claim, seconds_remaining = await can_claim_weekly_bonus(user_id)
        bonus_amount = await format_usd(WEEKLY_BONUS_AMOUNT)
        if can_claim:
            weekly_bonus_text = f"<b>🎁 Weekly Bonus:</b> <i>Available!</i> <b>{bonus_amount}</b>"
            weekly_bonus_button = [InlineKeyboardButton("🎉 Claim Weekly Bonus", callback_data="claim_weekly_bonus")]
        else:
            days = seconds_remaining // 86400 if seconds_remaining else 0
            hours = (seconds_remaining % 86400) // 3600 if seconds_remaining else 0
            minutes = (seconds_remaining % 3600) // 60 if seconds_remaining else 0
            if days > 0:
                time_str = f"{days}d {hours}h"
            elif hours > 0:
                time_str = f"{hours}h {minutes}m"
            else:
                time_str = f"{minutes}m"
            weekly_bonus_text = f"<b>🎁 Weekly Bonus:</b> <i>Available in {time_str}</i>"
            weekly_bonus_button = []

        text = f"""
🎁 <b>REWARDS & BONUS CENTRE</b> 🎁

💰 <b>Your Balance:</b> {await format_usd(user['balance'])}

{weekly_bonus_text}

<b>🎮 Other Rewards:</b>
• Daily Login Bonuses
• Referral System
• VIP Loyalty Program

<i>Check back regularly for new bonuses!</i>
"""
        keyboard = [
            weekly_bonus_button,
            [InlineKeyboardButton("👥 Referral System", callback_data="referral_system")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_panel")]
        ]
        # Remove empty rows
        keyboard = [row for row in keyboard if row]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def claim_weekly_bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle weekly bonus claim."""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        can_claim, _ = await can_claim_weekly_bonus(user_id)
        if can_claim:
            success = await claim_weekly_bonus(user_id)
            if success:
                text = f"🎉 <b>Weekly Bonus Claimed!</b>\n\n💰 You received {await format_usd(WEEKLY_BONUS_AMOUNT)}!\n\n<i>Come back next week for another bonus!</i>"
            else:
                text = "❌ Error claiming bonus. Please try again later."
        else:
            text = "⏳ Weekly bonus not ready. Please check back later."
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Rewards", callback_data="rewards_panel")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def referral_system_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the referral system dashboard."""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = await get_user(user_id)
        
        if not user:
            await query.edit_message_text(
                "❌ User not found. Please use /start to register first.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Start", callback_data="main_panel")]])
            )
            return
        
        # Get or create referral code
        referral_code = await get_or_create_referral_code(user_id)
        stats = await get_referral_stats(user_id)
        
        # Create referral link
        bot_username = "AxisCasinoBot"  # Replace with actual bot username
        referral_link = f"https://t.me/{bot_username}?start=ref_{referral_code}"
        
        text = f"""
👥 <b>REFERRAL SYSTEM</b> 👥

💰 <b>Your Earnings:</b> {await format_usd(stats['earnings'])}
📊 <b>Total Referrals:</b> {stats['count']}/{MAX_REFERRALS_PER_USER}

🎁 <b>Rewards:</b>
• New users get: <b>${REFERRAL_BONUS_REFERRER:.2f}</b> signup bonus
• You get: <b>${REFERRAL_BONUS_REFERRER:.2f}</b> per referral
• Minimum deposit: <b>${REFERRAL_MIN_DEPOSIT:.2f}</b> to activate

🔗 <b>Your Referral Code:</b> <code>{referral_code}</code>

📱 <b>Share Your Link:</b>
<code>{referral_link}</code>

<i>💡 Share your link and earn rewards when friends join!</i>
"""
        
        keyboard = [
            [InlineKeyboardButton("📋 Share Link", url=f"https://t.me/share/url?url={referral_link}")],
            [InlineKeyboardButton("🔙 Back to Rewards", callback_data="rewards_panel")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    # Placeholder game handler
    async def game_placeholder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Placeholder for games - shows coming soon message."""
        query = update.callback_query
        await query.answer()
        
        # Clear any previous states to prevent interference
        context.user_data.clear()
        
        await query.edit_message_text(
            "🎮 This game is coming soon! Stay tuned for updates.\n\n"
            "🚧 <i>We're working hard to bring you the best gaming experience!</i>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Other Games", callback_data="mini_app_centre")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
            ])
        )

    # Add all handlers
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("balance", show_balance_callback))
    application.add_handler(CommandHandler("help", support_callback))
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(start_command, pattern="^main_panel$"))
    application.add_handler(CallbackQueryHandler(mini_app_centre_callback, pattern="^mini_app_centre$"))
    application.add_handler(CallbackQueryHandler(show_balance_callback, pattern="^show_balance$"))
    application.add_handler(CallbackQueryHandler(support_callback, pattern="^support$"))
    application.add_handler(CallbackQueryHandler(rewards_panel_callback, pattern="^rewards_panel$"))
    application.add_handler(CallbackQueryHandler(claim_weekly_bonus_callback, pattern="^claim_weekly_bonus$"))
    application.add_handler(CallbackQueryHandler(referral_system_callback, pattern="^referral_system$"))
    
    # Deposit/Withdrawal handlers
    application.add_handler(CallbackQueryHandler(deposit_callback, pattern="^deposit$"))
    application.add_handler(CallbackQueryHandler(deposit_crypto_callback, pattern="^deposit_LTC$"))
    application.add_handler(CallbackQueryHandler(withdraw_start, pattern="^withdraw$"))
    application.add_handler(CallbackQueryHandler(withdraw_crypto_callback, pattern="^withdraw_LTC$"))
    application.add_handler(CallbackQueryHandler(confirm_withdrawal_callback, pattern="^confirm_withdrawal$"))
    
    # Game handlers (placeholders)
    game_patterns = ["^slots$", "^blackjack$", "^coinflip$", "^dice$", "^roulette$", "^crash$"]
    for pattern in game_patterns:
        application.add_handler(CallbackQueryHandler(game_placeholder, pattern=pattern))
    
    # Text input handler (only for deposit/withdrawal, not games)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input_main))
    
    # Start the bot
    logger.info("🎰 Casino Bot is starting up...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("✅ Casino Bot is running!")
    
    # Keep the bot running
    try:
        # Run forever
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Stopping bot...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    # Enable nested event loops for compatibility
    nest_asyncio.apply()
    
    # Run the bot
    asyncio.run(async_main())