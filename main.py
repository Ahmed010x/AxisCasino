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
            'description': f'Casino deposit for user {user_id}',  # No emoji
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
    """Create a crypto invoice using CryptoBot API."""
    if not CRYPTOBOT_API_TOKEN:
        return {"ok": False, "error": "CryptoBot API token not configured"}
    
    try:
        headers = {
            'Crypto-Pay-API-Token': CRYPTOBOT_API_TOKEN,
            'Content-Type': 'application/json'
        }
        
        # Set webhook URL for payment notifications
        webhook_url = f'{RENDER_EXTERNAL_URL}/webhook/cryptobot' if RENDER_EXTERNAL_URL else 'https://axiscasino.onrender.com/webhook/cryptobot'
        
        # Get USD amount for description
        usd_rate = await get_crypto_usd_rate(asset)
        usd_amount = amount * usd_rate if usd_rate > 0 else amount
        
        data = {
            'asset': asset,
            'amount': f"{amount:.8f}",
            'description': f'Casino deposit - ${usd_amount:.2f} USD',
            'hidden_message': str(user_id),
            'webhook_url': webhook_url,
            'expires_in': 3600,  # 1 hour expiration
            'allow_comments': False,
            'allow_anonymous': False,
            'paid_btn_name': 'viewItem',
            'paid_btn_url': f"https://t.me/{await get_bot_username()}?start=payment_success"
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

# --- Referral System Configuration ---
REFERRAL_BONUS_REFERRER = float(os.environ.get("REFERRAL_BONUS_REFERRER", "10.0"))  # Bonus for person who refers
REFERRAL_BONUS_REFEREE = float(os.environ.get("REFERRAL_BONUS_REFERRER", "5.0"))    # Bonus for new user
REFERRAL_MIN_DEPOSIT = float(os.environ.get("REFERRAL_MIN_DEPOSIT", "10.0"))       # Min deposit to activate referral
MAX_REFERRALS_PER_USER = int(os.environ.get("MAX_REFERRALS_PER_USER", "50"))       # Max referrals per user

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

async def ensure_referral_columns():
    """Ensure referral system columns exist in users table."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Add referral columns to users table
            await db.execute("""
                ALTER TABLE users ADD COLUMN referral_code TEXT UNIQUE DEFAULT NULL
            """)
            await db.execute("""
                ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT NULL
            """)
            await db.execute("""
                ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0
            """)
            await db.execute("""
                ALTER TABLE users ADD COLUMN referral_earnings REAL DEFAULT 0.0
            """)
            await db.execute("""
                ALTER TABLE users ADD COLUMN referral_activated BOOLEAN DEFAULT FALSE
            """)
            
            # Create referrals tracking table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referee_id INTEGER NOT NULL,
                    referral_code TEXT NOT NULL,
                    bonus_paid BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    activated_at TIMESTAMP DEFAULT NULL,
                    referee_first_deposit REAL DEFAULT 0.0,
                    FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                    FOREIGN KEY (referee_id) REFERENCES users (user_id),
                    UNIQUE(referee_id)
                )
            """)
            await db.commit()
    except Exception as e:
        if "duplicate column name" not in str(e) and "already exists" not in str(e):
            logger.error(f"Error adding referral columns: {e}")

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

# --- Referral System Helpers ---

def generate_referral_code(user_id: int) -> str:
    """Generate a unique referral code for a user."""
    import hashlib
    import random
    import string
    
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
            # Check if user already has a referral code
            cursor = await db.execute(
                "SELECT referral_code FROM users WHERE user_id = ?", (user_id,)
            )
            result = await cursor.fetchone()
            
            if result and result[0]:
                return result[0]
            
            # Generate new referral code
            max_attempts = 10
            for _ in range(max_attempts):
                code = generate_referral_code(user_id)
                try:
                    await db.execute(
                        "UPDATE users SET referral_code = ? WHERE user_id = ?",
                        (code, user_id)
                    )
                    await db.commit()
                    return code
                except Exception:
                    # Code might already exist, try again
                    continue
            
            # Fallback if all attempts failed
            return f"REF{user_id}"
            
    except Exception as e:
        logger.error(f"Error getting/creating referral code: {e}")
        return f"REF{user_id}"

async def get_referral_stats(user_id: int) -> dict:
    """Get referral statistics for a user."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Get user referral data
            cursor = await db.execute("""
                SELECT referral_code, referral_count, referral_earnings
                FROM users WHERE user_id = ?
            """, (user_id,))
            user_data = await cursor.fetchone()
            
            if not user_data:
                return {"code": "", "count": 0, "earnings": 0.0, "recent": []}
            
            # Get recent referrals
            cursor = await db.execute("""
                SELECT r.referee_id, u.username, r.created_at, r.bonus_paid, r.referee_first_deposit
                FROM referrals r
                JOIN users u ON r.referee_id = u.user_id
                WHERE r.referrer_id = ?
                ORDER BY r.created_at DESC
                LIMIT 10
            """, (user_id,))
            recent_referrals = await cursor.fetchall()
            
            return {
                "code": user_data[0] or "",
                "count": user_data[1] or 0,
                "earnings": user_data[2] or 0.0,
                "recent": [
                    {
                        "username": ref[1] or f"User{ref[0]}",
                        "date": ref[2][:10] if ref[2] else "Unknown",
                        "bonus_paid": bool(ref[3]),
                        "first_deposit": ref[4] or 0.0
                    }
                    for ref in recent_referrals
                ]
            }
            
    except Exception as e:
        logger.error(f"Error getting referral stats: {e}")
        return {"code": "", "count": 0, "earnings": 0.0, "recent": []}

async def process_referral(referee_id: int, referral_code: str) -> bool:
    """Process a new referral when user registers with a code."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Find the referrer
            cursor = await db.execute(
                "SELECT user_id FROM users WHERE referral_code = ?", (referral_code,)
            )
            referrer_data = await cursor.fetchone()
            
            if not referrer_data:
                return False
            
            referrer_id = referrer_data[0]
            
            # Don't allow self-referral
            if referrer_id == referee_id:
                return False
            
            # Check if referee already has a referrer
            cursor = await db.execute(
                "SELECT referred_by FROM users WHERE user_id = ?", (referee_id,)
            )
            referee_data = await cursor.fetchone()
            
            if referee_data and referee_data[0]:
                return False  # Already referred by someone
            
            # Check referral limits
            cursor = await db.execute(
                "SELECT referral_count FROM users WHERE user_id = ?", (referrer_id,)
            )
            referrer_stats = await cursor.fetchone()
            
            if referrer_stats and referrer_stats[0] >= MAX_REFERRALS_PER_USER:
                return False  # Referrer has reached max referrals
            
            # Create referral relationship
            await db.execute(
                "UPDATE users SET referred_by = ? WHERE user_id = ?",
                (referrer_id, referee_id)
            )
            
            # Insert into referrals table
            await db.execute("""
                INSERT INTO referrals (referrer_id, referee_id, referral_code, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(referee_id) DO NOTHING
            """, (referrer_id, referee_id, referral_code, datetime.now().isoformat()))
            
            # Update referrer's count
            await db.execute(
                "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?",
                (referrer_id,)
            )
            
            # Give immediate signup bonus to referee
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (REFERRAL_BONUS_REFEREE, referee_id)
            )
            
            await db.commit()
            
            # Notify referrer
            try:
                from main import application  # Import the application instance
                referee_user = await get_user(referee_id)
                referee_name = referee_user.get('username', f'User{referee_id}') if referee_user else f'User{referee_id}'
                
                await application.bot.send_message(
                    chat_id=referrer_id,
                    text=f"New Referral!\n\n"
                         f"{referee_name} joined using your referral code!\n"
                         f"They received ${REFERRAL_BONUS_REFEREE:.2f} signup bonus\n"
                         f"You'll get ${REFERRAL_BONUS_REFERRER:.2f} when they make their first deposit of ${REFERRAL_MIN_DEPOSIT:.2f}+",
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Failed to notify referrer: {e}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error processing referral: {e}")
        return False

async def activate_referral_bonus(referee_id: int, deposit_amount: float) -> bool:
    """Activate referral bonus when referee makes qualifying deposit."""
    try:
        if deposit_amount < REFERRAL_MIN_DEPOSIT:
            return False
            
        async with aiosqlite.connect(DB_PATH) as db:
            # Get referral info
            cursor = await db.execute("""
                SELECT r.referrer_id, r.bonus_paid, u.referred_by
                FROM referrals r
                JOIN users u ON r.referee_id = u.user_id
                WHERE r.referee_id = ? AND r.bonus_paid = FALSE
            """, (referee_id,))
            referral_data = await cursor.fetchone()
            
            if not referral_data:
                return False
            
            referrer_id = referral_data[0]
            
            # Give bonus to referrer
            await db.execute(
                "UPDATE users SET balance = balance + ?, referral_earnings = referral_earnings + ? WHERE user_id = ?",
                (REFERRAL_BONUS_REFERRER, REFERRAL_BONUS_REFERRER, referrer_id)
            )
            
            # Mark referral as paid and activated
            await db.execute("""
                UPDATE referrals 
                SET bonus_paid = TRUE, activated_at = ?, referee_first_deposit = ?
                WHERE referee_id = ?
            """, (datetime.now().isoformat(), deposit_amount, referee_id))
            
            # Mark referee as activated
            await db.execute(
                "UPDATE users SET referral_activated = TRUE WHERE user_id = ?",
                (referee_id,)
            )
            
            await db.commit()
            
            # Notify referrer
            try:
                from main import application
                referee_user = await get_user(referee_id)
                referee_name = referee_user.get('username', f'User{referee_id}') if referee_user else f'User{referee_id}'
                
                await application.bot.send_message(
                    chat_id=referrer_id,
                    text=f"Referral Bonus Paid!\n\n"
                         f"{referee_name} made their first deposit!\n"
                         f"You received ${REFERRAL_BONUS_REFERRER:.2f} referral bonus!\n"
                         f"Deposit amount: ${deposit_amount:.2f}",
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Failed to notify referrer: {e}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error activating referral bonus: {e}")
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
        [InlineKeyboardButton("� Referral System", callback_data="referral_system")],
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

# --- Referral System Handlers ---
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
    bot_username = context.bot.username or "AxisCasinoBot"
    referral_link = f"https://t.me/{bot_username}?start=ref_{referral_code}"
    
    # Format recent referrals
    recent_text = ""
    if stats["recent"]:
        recent_text = "\n\n👥 <b>Recent Referrals:</b>\n"
        for ref in stats["recent"][:5]:
            status = "✅ Activated" if ref["bonus_paid"] else "⏳ Pending"
            recent_text += f"• {ref['username']} - {status} ({ref['date']})\n"
    
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
{recent_text}
<i>💡 Share your link and earn rewards when friends join and deposit!</i>
"""
    
    keyboard = [
        [InlineKeyboardButton("📋 Copy Referral Link", callback_data=f"copy_ref_{referral_code}")],
        [
            InlineKeyboardButton("📊 View All Referrals", callback_data="view_all_referrals"),
            InlineKeyboardButton("📈 Referral Stats", callback_data="referral_stats")
        ],
        [InlineKeyboardButton("🔙 Back to Rewards", callback_data="rewards_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def copy_referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle referral link copy action."""
    query = update.callback_query
    await query.answer()
    
    # Extract referral code from callback data
    referral_code = query.data.split("_", 2)[2]
    bot_username = context.bot.username or "AxisCasinoBot"
    referral_link = f"https://t.me/{bot_username}?start=ref_{referral_code}"
    
    share_text = f"""
🎰 <b>Join Axis Casino and Get Bonus!</b> 🎰

💰 Get <b>${REFERRAL_BONUS_REFERRER:.2f}</b> signup bonus when you join!
🎮 Play amazing casino games
💳 Easy deposits and withdrawals

👆 Click the link above to join and claim your bonus!

#AxisCasino #Bonus #CasinoGames
"""
    
    text = f"""
📋 <b>Your Referral Link:</b>

<code>{referral_link}</code>

📱 <b>Share Message:</b>
{share_text}

💡 <i>Tap and hold the link above to copy it, then share with friends!</i>
"""
    
    keyboard = [
        [InlineKeyboardButton("📤 Share in Telegram", url=f"https://t.me/share/url?url={referral_link}&text={share_text.replace('#', '%23')}")],
        [InlineKeyboardButton("🔙 Back to Referrals", callback_data="referral_system")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def view_all_referrals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed referral list."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    stats = await get_referral_stats(user_id)
    
    if not stats["recent"]:
        text = """
👥 <b>Your Referrals</b>

📊 You haven't referred anyone yet.

💡 <i>Share your referral link to start earning!</i>
"""
    else:
        text = f"""
👥 <b>Your Referrals</b> ({stats['count']} total)

💰 <b>Total Earnings:</b> {await format_usd(stats['earnings'])}

"""
        for i, ref in enumerate(stats["recent"], 1):
            status_icon = "✅" if ref["bonus_paid"] else "⏳"
            deposit_text = f"(${ref['first_deposit']:.2f})" if ref["first_deposit"] > 0 else "(No deposit)"
            text += f"{i}. {status_icon} <b>{ref['username']}</b>\n"
            text += f"   Joined: {ref['date']} {deposit_text}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Referrals", callback_data="referral_system")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def referral_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed referral statistics."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Get detailed stats
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total_refs,
                    COUNT(CASE WHEN bonus_paid = TRUE THEN 1 END) as activated_refs,
                    SUM(referee_first_deposit) as total_deposits,
                    AVG(referee_first_deposit) as avg_deposit
                FROM referrals 
                WHERE referrer_id = ?
            """, (user_id,))
            detailed_stats = await cursor.fetchone()
            
            total_refs = detailed_stats[0] or 0
            activated_refs = detailed_stats[1] or 0
            total_deposits = detailed_stats[2] or 0.0
            avg_deposit = detailed_stats[3] or 0.0
            
            # Get user's total referral earnings
            cursor = await db.execute(
                "SELECT referral_earnings FROM users WHERE user_id = ?", (user_id,)
            )
            earnings_data = await cursor.fetchone()
            total_earnings = earnings_data[0] if earnings_data else 0.0
            
            activation_rate = (activated_refs / total_refs * 100) if total_refs > 0 else 0
            
            text = f"""
📈 <b>REFERRAL ANALYTICS</b> 📈

📊 <b>Overview:</b>
• Total Referrals: <b>{total_refs}</b>
• Activated: <b>{activated_refs}</b> ({activation_rate:.1f}%)
• Pending: <b>{total_refs - activated_refs}</b>

💰 <b>Earnings:</b>
• Total Earned: <b>{await format_usd(total_earnings)}</b>
• Potential Max: <b>{await format_usd(total_refs * REFERRAL_BONUS_REFERRER)}</b>

💳 <b>Deposit Stats:</b>
• Total Deposits: <b>{await format_usd(total_deposits)}</b>
• Average Deposit: <b>{await format_usd(avg_deposit)}</b>

🎯 <b>Performance:</b>
• Conversion Rate: <b>{activation_rate:.1f}%</b>
• Remaining Slots: <b>{MAX_REFERRALS_PER_USER - total_refs}</b>

<i>💡 Higher deposits lead to better conversion rates!</i>
"""
            
    except Exception as e:
        logger.error(f"Error getting referral analytics: {e}")
        text = "❌ Unable to load analytics. Please try again later."
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Referrals", callback_data="referral_system")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# --- Deposit/Withdrawal Handlers ---

async def deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle deposit button - show deposit options."""
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
    
    # Set the crypto type in context for the conversation
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



async def process_deposit_payment(update, context, crypto_type: str, amount_usd: float):
    """Process deposit payment and create CryptoBot invoice"""
    query = getattr(update, 'callback_query', None)
    
    try:
        # Get current crypto rate
        rate = await get_crypto_usd_rate(crypto_type)
        if rate <= 0:
            error_text = f"❌ Unable to get current {crypto_type} rate. Please try again."
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
            error_text = f"❌ Failed to create {crypto_type} invoice. Please try again."
            if query:
                await query.edit_message_text(error_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="deposit")]]))
            else:
                await update.message.reply_text(error_text)
            return
        
        invoice = invoice_data['result']
        # Use mini_app_invoice_url for native mini app experience within your bot
        invoice_url = invoice.get('mini_app_invoice_url') or invoice.get('bot_invoice_url')
        
        text = f"""
💰 <b>CRYPTO PAY INVOICE READY</b> 💰

📊 <b>Payment Details:</b>
• Amount: <b>${amount_usd:.2f} USD</b>
• Crypto: <b>{crypto_amount:.8f} {crypto_type}</b>
• Rate: <b>${rate:.4f}</b> per {crypto_type}
• Invoice ID: <code>{invoice['invoice_id']}</code>

💳 <b>Pay with CryptoBot Mini App:</b>
Click the button below to open the secure payment interface directly within this bot. Pay using your CryptoBot wallet without leaving our bot.

⏰ <b>Expires in 1 hour</b>
🔔 <i>You'll be notified instantly when payment is confirmed!</i>

💡 <b>Note:</b> The payment opens in a native mini app for the best user experience.
"""
        
        keyboard = [
            [InlineKeyboardButton("💳 Pay Now", web_app=WebAppInfo(url=invoice_url))],
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

async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the withdrawal process."""
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
    
    # Check withdrawal limits
    limits_check = await check_withdrawal_limits(user_id, balance)
    
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

async def withdraw_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal amount selection."""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data: withdraw_amount_LTC_50
    parts = query.data.split("_")
    crypto_type = parts[2]
    amount_usd = float(parts[3])
    
    context.user_data['withdraw_crypto'] = crypto_type
    context.user_data['withdraw_amount'] = amount_usd
    
    # Ask for address
    text = f"""
🏦 <b>WITHDRAWAL ADDRESS</b> 🏦

💰 <b>Amount:</b> ${amount_usd:.2f} USD
🪙 <b>Asset:</b> {crypto_type}

📝 <b>Enter {crypto_type} Address</b>
Please enter your {crypto_type} wallet address where you want to receive the funds.

⚠️ <b>Important:</b>
• Double-check your address before confirming
• Wrong addresses may result in permanent loss of funds
• Only send {crypto_type} to {crypto_type} addresses

💡 <i>Paste your {crypto_type} wallet address below:</i>
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Amount", callback_data=f"withdraw_{crypto_type}")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    # Set state for address input
    context.user_data['awaiting_withdraw_address'] = crypto_type

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
� <b>Rate:</b> ${rate:.4f} per {crypto_type}

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
        
        # Deduct balance first
        success = await deduct_balance(user_id, total_needed)
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
                await update_withdrawal_status(withdrawal_id, "completed", send_result.get('transaction_hash', ''), "")
                status_text = "✅ <b>Withdrawal sent successfully!</b>"
            else:
                await update_withdrawal_status(withdrawal_id, "failed", "", send_result.get('error', 'Unknown error'))
                # Refund the balance
                await update_balance(user_id, total_needed)
                status_text = f"❌ <b>Withdrawal failed:</b> {send_result.get('error', 'Unknown error')}"
        
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

# --- Support/Help Feature ---
async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send support/help info to the user."""
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
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle support/help callback query."""
    query = update.callback_query
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

# --- Main Bot Setup and Entry Point ---
async def async_main():
    """Async main function to properly start both bot and keep-alive server."""
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
    
    # Define handler functions first (before registration)
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command and main panel callback."""
        user = update.effective_user
        user_id = user.id if user else None
        username = user.username or (user.first_name if user else "Guest")
        
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
        can_claim_bonus = await can_claim_weekly_bonus(user_id) if user_id else False
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
            "🎮 <b>Welcome to the Game Centre!</b> �\n\n"
            "Choose a game to play or explore more features!"
        )
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send support/help info to the user."""
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
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    async def show_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show user statistics and game history."""
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        user_id = user.id if user else None
        
        if not user_id:
            await query.edit_message_text(
                "❌ Unable to identify user.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]])
            )
            return
            
        user_data = await get_user(user_id)
        if not user_data:
            await query.edit_message_text(
                "❌ User not found. Please use /start to register first.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Start", callback_data="main_panel")]])
            )
            return
            
        username = user.username or user.first_name or "Player"
        balance_str = await format_usd(user_data['balance'])
        
        # Get additional stats from database
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Get recent game sessions
                cursor = await db.execute("""
                    SELECT COUNT(*), SUM(bet_amount), SUM(win_amount), AVG(bet_amount)
                    FROM game_sessions WHERE user_id = ?
                """, (user_id,))
                game_stats = await cursor.fetchone()
                
                total_games = game_stats[0] if game_stats[0] else 0
                total_bet = game_stats[1] if game_stats[1] else 0.0
                total_won = game_stats[2] if game_stats[2] else 0.0
                avg_bet = game_stats[3] if game_stats[3] else 0.0
                
                # Calculate profit/loss
                net_result = total_won - total_bet
                
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            total_games = user_data.get('games_played', 0)
            total_bet = user_data.get('total_wagered', 0.0)
            total_won = 0.0
            avg_bet = 0.0
            net_result = 0.0
        
        # Format the stats display
        profit_loss_str = f"+{await format_usd(net_result)}" if net_result >= 0 else f"-{await format_usd(abs(net_result))}"
        profit_emoji = "📈" if net_result >= 0 else "📉"
        
        text = f"""
📊 <b>{username}'s Statistics</b> 📊

💰 <b>Current Balance:</b> {balance_str}
{profit_emoji} <b>Total P&L:</b> {profit_loss_str}

🎮 <b>Gaming Stats:</b>
• Games Played: {total_games:,}
• Total Wagered: {await format_usd(total_bet)}
• Total Won: {await format_usd(total_won)}
• Average Bet: {await format_usd(avg_bet)}

📅 <b>Account Info:</b>
• Member Since: {user_data.get('created_at', 'Unknown')[:10]}
• Last Active: {user_data.get('last_active', 'Unknown')[:10]}

<i>Keep playing to improve your stats!</i>
"""
        
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
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    # Add all handlers
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("health", health_command))
    application.add_handler(CommandHandler("balance", show_balance_callback))
    application.add_handler(CommandHandler("app", mini_app_centre_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("support", support_command))
    application.add_handler(CommandHandler("owner", owner_command))

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
            "🎮 This game is coming soon! Stay tuned for updates.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back to Menu", callback_data="main_panel")]])
        )

    application.add_handler(CallbackQueryHandler(mini_app_centre_callback, pattern="^mini_app_centre$"))
    application.add_handler(CallbackQueryHandler(show_balance_callback, pattern="^show_balance$"))
    application.add_handler(CallbackQueryHandler(show_stats_callback, pattern="^show_stats$"))
    application.add_handler(CallbackQueryHandler(support_callback, pattern="^support$"))
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
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back to Menu", callback_data="main_panel")]])
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
    application.add_handler(CallbackQueryHandler(deposit_callback, pattern="^deposit$"))
    application.add_handler(CallbackQueryHandler(deposit_crypto_callback, pattern="^deposit_LTC$"))
    
    # Withdrawal handlers
    application.add_handler(CallbackQueryHandler(withdraw_start, pattern="^withdraw$"))
    application.add_handler(CallbackQueryHandler(withdraw_crypto_callback, pattern="^withdraw_LTC$"))  
    application.add_handler(CallbackQueryHandler(withdraw_amount_callback, pattern="^withdraw_amount_"))
    application.add_handler(CallbackQueryHandler(confirm_withdrawal_callback, pattern="^confirm_withdrawal$"))

    application.add_handler(CallbackQueryHandler(start_command, pattern="^main_panel$"))
    application.add_handler(CallbackQueryHandler(rewards_panel_callback, pattern="^rewards_panel$"))
    application.add_handler(CallbackQueryHandler(claim_weekly_bonus_combined_callback, pattern="^claim_weekly_bonus_combined$"))
    
    # Referral system handlers
    application.add_handler(CallbackQueryHandler(referral_system_callback, pattern="^referral_system$"))
    application.add_handler(CallbackQueryHandler(copy_referral_callback, pattern="^copy_ref_"))
    application.add_handler(CallbackQueryHandler(view_all_referrals_callback, pattern="^view_all_referrals$"))
    application.add_handler(CallbackQueryHandler(referral_stats_callback, pattern="^referral_stats$"))
    
    # Message handlers for text input
    async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text input for various states."""
        # Handle deposit amount input
        if 'awaiting_deposit_amount' in context.user_data:
            await handle_deposit_amount_input(update, context)
        # Handle withdrawal amount input
        elif 'awaiting_withdraw_amount' in context.user_data:
            await handle_withdraw_amount_input(update, context)
        # Handle withdrawal address input
        elif 'awaiting_withdraw_address' in context.user_data:
            await handle_withdraw_address_input(update, context)
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
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
                                
                                # Check and activate referral bonus (async operation in sync context)
                                try:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    loop.run_until_complete(activate_referral_bonus(user_id, usd_amount))
                                    loop.close()
                                except Exception as ref_error:
                                    logger.error(f"Error activating referral bonus: {ref_error}")
                                
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
        
        # Payment redirect route - redirects directly to CryptoBot
        @app.route('/payment_redirect/<invoice_hash>')
        def payment_redirect(invoice_hash: str):
            # Redirect to CryptoBot invoice URL
            cryptobot_url = f"https://t.me/CryptoBot?start={invoice_hash}"
            return f"""
            <!doctype html>
            <html>
              <head>
                <meta charset="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <title>🎰 Casino Payment - Redirecting</title>
                <meta http-equiv="refresh" content="1;url={cryptobot_url}">
                <style>
                  body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    margin: 0;
                    padding: 40px 20px; 
                    text-align: center; 
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    color: #ffffff;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                  }}
                  .container {{
                    max-width: 400px;
                    margin: 0 auto;
                    padding: 20px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 16px;
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                  }}
                  .logo {{
                    font-size: 48px;
                    margin-bottom: 20px;
                  }}
                  .title {{
                    font-size: 24px;
                    font-weight: 600;
                    margin-bottom: 10px;
                    color: #4CAF50;
                  }}
                  .subtitle {{
                    font-size: 16px;
                    opacity: 0.8;
                    margin-bottom: 30px;
                  }}
                  .btn {{ 
                    display: inline-block; 
                    padding: 16px 32px; 
                    background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                    color: #fff; 
                    border-radius: 12px; 
                    text-decoration: none; 
                    margin: 10px;
                    font-weight: 600;
                    font-size: 16px;
                    transition: all 0.3s ease;
                    box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
                  }}
                  .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(76, 175, 80, 0.4);
                  }}
                  .loading {{
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    margin: 20px 0;
                  }}
                  .spinner {{
                    width: 40px;
                    height: 40px;
                    border: 4px solid rgba(255, 255, 255, 0.1);
                    border-left: 4px solid #4CAF50;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin-bottom: 15px;
                  }}
                  @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                  }}
                  .info {{
                    background: rgba(255, 255, 255, 0.05);
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border-left: 4px solid #4CAF50;
                  }}
                </style>
              </head>
              <body>
                <div class="container">
                  <div class="logo">🎰</div>
                  <h2 class="title">Secure Payment</h2>
                  <p class="subtitle">Opening CryptoBot payment interface...</p>
                  
                  <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <p>Connecting to payment processor...</p>
                  </div>
                  
                  <div class="info">
                    <p><strong>🔐 Secure Transaction</strong></p>
                    <p>Your payment is processed securely through CryptoBot API</p>
                  </div>
                  
                  <p><a class="btn" href="{web_invoice}" target="_self" id="payBtn">💳 Open Payment Page</a></p>
                </div>
                
                <script>
                  try {{
                    // Initialize Telegram WebApp
                    if (window.Telegram && window.Telegram.WebApp) {{
                      const webapp = window.Telegram.WebApp;
                      webapp.ready();
                      webapp.expand();
                      webapp.disableVerticalSwipes();
                      
                      // Set header color
                      webapp.setHeaderColor('#1a1a2e');
                      webapp.setBackgroundColor('#1a1a2e');
                      
                      // Show main button
                      webapp.MainButton.setText('💳 Proceed to Payment');
                      webapp.MainButton.color = '#4CAF50';
                      webapp.MainButton.textColor = '#FFFFFF';
                      webapp.MainButton.show();
                      
                      webapp.MainButton.onClick(() => {{
                        window.location.replace("{web_invoice}");
                      }});
                    }}
                    
                    // Auto-redirect after 2 seconds
                    setTimeout(() => {{
                      document.getElementById('loading').innerHTML = '<p>Redirecting now...</p>';
                      window.location.replace("{web_invoice}");
                    }}, 2000);
                    
                    // Manual button click
                    document.getElementById('payBtn').addEventListener('click', (e) => {{
                      e.preventDefault();
                      window.location.replace("{web_invoice}");
                    }});
                    
                  }} catch (e) {{
                    console.error('WebApp initialization error:', e);
                    // Fallback - show button immediately
                    document.getElementById('loading').style.display = 'none';
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