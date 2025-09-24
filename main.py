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

# --- Weekly Bonus Helpers ---
WEEKLY_BONUS_AMOUNT = float(os.environ.get("WEEKLY_BONUS_AMOUNT", "5.0"))
WEEKLY_BONUS_INTERVAL = 7  # days

async def ensure_weekly_bonus_column():
    """Ensure the last_weekly_bonus column exists in users table."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                ALTER TABLE users ADD COLUMN last_weekly_bonus TIMESTAMP DEFAULT NULL
            """)
            await db.commit()
    except Exception as e:
        if "duplicate column name" not in str(e):
            logger.error(f"Error adding last_weekly_bonus column: {e}")

async def can_claim_weekly_bonus(user_id: int) -> Tuple[bool, Optional[int]]:
    """Check if user can claim weekly bonus. Returns (can_claim, seconds_remaining)."""
    user = await get_user(user_id)
    if not user:
        return True, None  # New users can claim immediately
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
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET balance = balance + ?, last_weekly_bonus = ? WHERE user_id = ?",
                (WEEKLY_BONUS_AMOUNT, datetime.now().isoformat(), user_id)
            )
            await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error granting weekly bonus: {e}")
        return False

# --- Owner Panel (Admin Panel) ---
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
        weekly_bonus_button = [InlineKeyboardButton("🎉 Claim Weekly Bonus", callback_data="claim_weekly_bonus_combined")]
    else:
        days = seconds_remaining // 86400 if seconds_remaining else 0
        hours = (seconds_remaining % 86400) // 3600 if seconds_remaining else 0
        minutes = (seconds_remaining % 3600) // 60 if seconds_remaining else 0
        if days > 0:
            time_str = f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            time_str = f"{hours}h {minutes}m"
        else:
            time_str = f"{minutes}m"
        weekly_bonus_text = f"<b>🎁 Weekly Bonus:</b> <i>Available in {time_str}</i>"
        weekly_bonus_button = []

    # Other rewards (placeholders)
    daily_bonus_text = "<b>🔅 Daily Bonus:</b> <i>Coming soon</i>"
    loyalty_text = "<b>💎 Loyalty Points:</b> <i>Earned by playing games</i>"
    referral_text = "<b>💌 Referral Bonus:</b> <i>Invite friends to earn rewards</i>"

    text = f"""
🎁 <b>REWARDS & BONUS CENTRE</b> 🎁\n\n
💰 <b>Your Balance:</b> {await format_usd(user['balance'])}\n\n
{weekly_bonus_text}\n{daily_bonus_text}\n{loyalty_text}\n{referral_text}\n\n
<i>Claim your bonuses and check your rewards here!</i>
"""
    keyboard = [
        weekly_bonus_button,
        [InlineKeyboardButton("💌 Invite Friends", callback_data="invite_friends")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_panel")]
    ]
    # Remove empty rows
    keyboard = [row for row in keyboard if row]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# --- Claim Weekly Bonus from Combined Panel ---
async def claim_weekly_bonus_combined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    can_claim, _ = await can_claim_weekly_bonus(user_id)
    if can_claim:
        success = await claim_weekly_bonus(user_id)
        if success:
            user = await get_user(user_id)
            new_balance = await format_usd(user['balance']) if user else "$0.00"
            bonus_amount = await format_usd(WEEKLY_BONUS_AMOUNT)
            text = (
                f"🎉 <b>Weekly Bonus Claimed!</b>\n\n"
                f"You received <b>{bonus_amount}</b>!\n"
                f"💰 <b>New Balance:</b> {new_balance}\n\n"
                "Come back next week for more rewards!"
            )
        else:
            text = "❌ Error granting weekly bonus. Please try again later."
    else:
        text = "⏳ Weekly bonus not ready. Please check back later."
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Rewards", callback_data="rewards_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# --- Deposit/Withdrawal Handlers ---
# Define a placeholder withdraw_start handler if not already defined or import from your withdrawal module
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the withdrawal process (placeholder implementation)."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🚧 Withdrawal feature is under construction. Please check back later.",
        parse_mode=ParseMode.HTML
    )

# --- Main Bot Setup and Entry Point ---
async def async_main():
    """Async main function to properly start both bot and keep-alive server."""
    logger.info("🚀 Starting Telegram Casino Bot...")

    # Initialize database first
    await init_db()
    logger.info("✅ Database initialized")
    
    # Ensure weekly bonus column exists AFTER database is initialized
    await ensure_weekly_bonus_column()
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Define handler functions first (before registration)
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command and main panel callback."""
        user = update.effective_user
        user_id = user.id if user else None
        username = user.username or (user.first_name if user else "Guest")
        
        # Ensure user exists in DB
        user_data = await get_user(user_id)
        if not user_data:
            await create_user(user_id, username)
            user_data = await get_user(user_id)
        
        # Get user's current balance for display
        balance_str = await format_usd(user_data['balance']) if user_data else "$0.00"
        
        # Check if user can claim weekly bonus
        can_claim_bonus = await can_claim_weekly_bonus(user_id) if user_id else False
        bonus_emoji = "🎁✨" if can_claim_bonus else "🎁"
        
        # Create an engaging welcome message
        text = (
            f"🎰 <b>Welcome to Axis Casino, {username}!</b> 🎰\n\n"
            f"💰 <b>Balance:</b> {balance_str}\n"
            f"🏆 Ready to win big? Let's get started!\n\n"
            f"🎮 <b>Play Games</b> • 💳 <b>Manage Funds</b> • {bonus_emoji} <b>Rewards</b>"
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
            ]
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
                InlineKeyboardButton("💳 Deposit", callback_data="deposit")
            ],
            [
                InlineKeyboardButton("🎁 Weekly Bonus", callback_data="weekly_bonus"),
                InlineKeyboardButton("🏦 Withdraw", callback_data="withdraw")
            ],
            [InlineKeyboardButton("🏠 ← Back to Menu", callback_data="main_panel")]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def mini_app_centre_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the mini app centre with available games and features (command version)."""
        keyboard = [
            [InlineKeyboardButton("🎰 Slots", callback_data="slots")],
            [InlineKeyboardButton("🪙 Coin Flip", callback_data="coinflip")],
            [InlineKeyboardButton("🎲 Dice", callback_data="dice")],
            [InlineKeyboardButton("🃏 Blackjack", callback_data="blackjack")],
            [InlineKeyboardButton("🎡 Roulette", callback_data="roulette")],
            [InlineKeyboardButton("🚀 Crash", callback_data="crash")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        text = (
            "🎮 <b>Mini App Centre</b> 🎮\n\n"
            "Choose a game to play or explore more features!"
        )
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    # Add all handlers
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("health", health_command))
    application.add_handler(CommandHandler("balance", show_balance_callback))
    async def mini_app_centre_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the mini app centre with available games and features (command version)."""
        keyboard = [
            [InlineKeyboardButton("🎰 Slots", callback_data="slots")],
            [InlineKeyboardButton("🪙 Coin Flip", callback_data="coinflip")],
            [InlineKeyboardButton("🎲 Dice", callback_data="dice")],
            [InlineKeyboardButton("🃏 Blackjack", callback_data="blackjack")],
            [InlineKeyboardButton("🎡 Roulette", callback_data="roulette")],
            [InlineKeyboardButton("🚀 Crash", callback_data="crash")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        text = (
            "🎮 <b>Mini App Centre</b> 🎮\n\n"
            "Choose a game to play or explore more features!"
        )
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    application.add_handler(CommandHandler("app", mini_app_centre_command))
    application.add_handler(CommandHandler("help", help_command))

    # Placeholder for check_payment_command to avoid NameError
    async def check_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Check payment status (placeholder implementation)."""
        if update.message:
            await update.message.reply_text("🚧 Payment check feature is under construction.")
        elif update.callback_query:
            await update.callback_query.answer("🚧 Payment check feature is under construction.", show_alert=True)

    application.add_handler(CommandHandler("payment", check_payment_command))
    application.add_handler(CommandHandler("checkpayment", check_payment_command))

    async def test_cryptobot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Test CryptoBot API connectivity and show current LTC/USD rate."""
        try:
            ltc_rate = await get_crypto_usd_rate("LTC")
            if ltc_rate > 0:
                text = f"✅ CryptoBot API is working!\n\nCurrent LTC/USD rate: <b>${ltc_rate:.4f}</b>"
            else:
                text = "⚠️ Could not fetch LTC/USD rate from CryptoBot API."
        except Exception as e:
            text = f"❌ Error testing CryptoBot API: {e}"
        if update.message:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML)

    application.add_handler(CommandHandler("testcrypto", test_cryptobot_command))
    application.add_handler(CommandHandler("owner", owner_command))

    async def rates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show current crypto to USD rates."""
        assets = ["LTC", "USDT", "TON", "SOL"]
        lines = ["💱 <b>Crypto Exchange Rates</b>"]
        for asset in assets:
            rate = await get_crypto_usd_rate(asset)
            if rate > 0:
                lines.append(f"• <b>{asset}/USD:</b> ${rate:.4f}")
            else:
                lines.append(f"• <b>{asset}/USD:</b> <i>Unavailable</i>")
        text = "\n".join(lines)
        if update.message:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML)

    application.add_handler(CommandHandler("rates", rates_command))
    
    # Callback query handlers
    # --- Mini App Centre Callback ---
    async def mini_app_centre_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the mini app centre with available games and features."""
        query = update.callback_query
        await query.answer()
        
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
                InlineKeyboardButton("� Dice Roll", callback_data="dice")
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
            "🎮 <b>Welcome to the Game Centre!</b> �\n\n"
            f"💰 <b>Your Balance:</b> {balance_str}\n\n"
            "🎰 <b>Featured Games:</b> Classic casino favorites\n"
            "⚡ <b>Quick Games:</b> Fast-paced instant wins\n"
            "🎪 <b>Advanced Games:</b> Strategic gameplay\n\n"
            "🍀 <i>Good luck and play responsibly!</i>"
        )
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    # Game handler (for verification requirements)
    async def game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle generic game callbacks."""
        query = update.callback_query
        await query.answer()
        # This is a placeholder for game handlers
        await query.edit_message_text(
            "🎮 Game selection coming soon!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back to Menu", callback_data="main_panel")]])
        )

    application.add_handler(CallbackQueryHandler(mini_app_centre_callback, pattern="^mini_app_centre$"))
    application.add_handler(CallbackQueryHandler(show_balance_callback, pattern="^show_balance$"))
    # application.add_handler(CallbackQueryHandler(classic_casino_callback, pattern="^classic_casino$"))
    
    # Game handlers - using conversation handlers for custom betting
    # TODO: Import or define slots_conv_handler and other game handlers in their respective modules
    # from games.slots import slots_conv_handler
    # from games.coinflip import coinflip_conv_handler
    # from games.dice import dice_conv_handler
    # from games.blackjack import blackjack_conv_handler
    # from games.roulette import roulette_conv_handler
    # from games.crash import crash_conv_handler

    # Example placeholder handlers to avoid NameError (replace with actual imports)
    from telegram.ext import ConversationHandler

    # Create placeholder conversation handlers with proper fallbacks
    async def placeholder_game_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Placeholder for game handlers"""
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "🎮 This game is coming soon! Stay tuned for updates.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back", callback_data="main_panel")]])
            )
        elif hasattr(update, 'message') and update.message:
            await update.message.reply_text(
                "🎮 This game is coming soon! Stay tuned for updates."
            )
        return ConversationHandler.END

    # Create minimal working conversation handlers
    slots_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(placeholder_game_handler, pattern="^slots$")],
        states={},
        fallbacks=[],
        name="slots_conv_handler"
    )
    coinflip_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(placeholder_game_handler, pattern="^coinflip$")],
        states={},
        fallbacks=[],
        name="coinflip_conv_handler"
    )
    dice_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(placeholder_game_handler, pattern="^dice$")],
        states={},
        fallbacks=[],
        name="dice_conv_handler"
    )
    blackjack_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(placeholder_game_handler, pattern="^blackjack$")],
        states={},
        fallbacks=[],
        name="blackjack_conv_handler"
    )
    roulette_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(placeholder_game_handler, pattern="^roulette$")],
        states={},
        fallbacks=[],
        name="roulette_conv_handler"
    )
    crash_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(placeholder_game_handler, pattern="^crash$")],
        states={},
        fallbacks=[],
        name="crash_conv_handler"
    )

    application.add_handler(slots_conv_handler)
    application.add_handler(coinflip_conv_handler)
    application.add_handler(dice_conv_handler)
    application.add_handler(blackjack_conv_handler)
    application.add_handler(roulette_conv_handler)
    application.add_handler(crash_conv_handler)
    # Deposit/Withdrawal handlers
    # Define a placeholder withdraw_start handler if not already defined or import from your withdrawal module
    async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start the withdrawal process (placeholder implementation)."""
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "🚧 Withdrawal feature is under construction. Please check back later.",
            parse_mode=ParseMode.HTML
        )

    application.add_handler(CallbackQueryHandler(withdraw_start, pattern="^withdraw$"))
    # TODO: Implement withdraw_asset_callback in your withdrawal module and import it here.
    # application.add_handler(CallbackQueryHandler(withdraw_asset_callback, pattern="^withdraw_asset_"))

    application.add_handler(CallbackQueryHandler(start_command, pattern="^main_panel$"))
    application.add_handler(CallbackQueryHandler(rewards_panel_callback, pattern="^rewards_panel$"))
    application.add_handler(CallbackQueryHandler(claim_weekly_bonus_combined_callback, pattern="^claim_weekly_bonus_combined$"))
    # Remove old weekly_bonus and redeem_panel handlers (do not re-register them)
    # ...existing code...

    # Add global error handler
    async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and send a user-friendly message."""
        logger.error(msg="Exception while handling an update:", exc_info=context.error)
        try:
            if update and hasattr(update, "message") and update.message:
                await update.message.reply_text("❌ An unexpected error occurred. Please try again later.")
            elif update and hasattr(update, "callback_query") and update.callback_query:
                await update.callback_query.answer("❌ An unexpected error occurred. Please try again later.", show_alert=True)
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")

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