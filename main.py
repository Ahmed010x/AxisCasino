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

# Apply nest_asyncio only if needed
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass  # nest_asyncio not available

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
            # Enhanced Users table with comprehensive tracking
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    first_name TEXT,
                    last_name TEXT,
                    balance REAL DEFAULT 0.0,
                    games_played INTEGER DEFAULT 0,
                    total_wagered REAL DEFAULT 0.0,
                    total_won REAL DEFAULT 0.0,
                    total_deposited REAL DEFAULT 0.0,
                    total_withdrawn REAL DEFAULT 0.0,
                    win_streak INTEGER DEFAULT 0,
                    max_win_streak INTEGER DEFAULT 0,
                    loss_streak INTEGER DEFAULT 0,
                    max_loss_streak INTEGER DEFAULT 0,
                    biggest_win REAL DEFAULT 0.0,
                    biggest_loss REAL DEFAULT 0.0,
                    vip_level INTEGER DEFAULT 0,
                    loyalty_points REAL DEFAULT 0.0,
                    referral_code TEXT DEFAULT NULL,
                    referred_by TEXT DEFAULT NULL,
                    referral_earnings REAL DEFAULT 0.0,
                    referral_count INTEGER DEFAULT 0,
                    last_weekly_bonus TEXT DEFAULT NULL,
                    is_banned BOOLEAN DEFAULT FALSE,
                    ban_reason TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_game_at TIMESTAMP DEFAULT NULL,
                    timezone TEXT DEFAULT 'UTC'
                )
            """)
            
            # Detailed Game sessions table with comprehensive data
            await db.execute("""
                CREATE TABLE IF NOT EXISTS game_sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    game_type TEXT NOT NULL,
                    game_variant TEXT DEFAULT NULL,
                    bet_amount REAL NOT NULL,
                    win_amount REAL DEFAULT 0.0,
                    net_result REAL DEFAULT 0.0,
                    multiplier REAL DEFAULT 0.0,
                    game_data TEXT DEFAULT NULL,  -- JSON data for game specifics
                    result TEXT,
                    is_jackpot BOOLEAN DEFAULT FALSE,
                    house_edge REAL DEFAULT 0.0,
                    rtp REAL DEFAULT 0.0,  -- Return to Player percentage
                    session_duration INTEGER DEFAULT 0,  -- in seconds
                    ip_address TEXT DEFAULT NULL,
                    user_agent TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Enhanced Transactions table for all financial activities
            await db.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,  -- deposit, withdrawal, bet, win, bonus, refund, etc.
                    subtype TEXT DEFAULT NULL,  -- crypto_deposit, bank_deposit, game_win, referral_bonus, etc.
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    crypto_asset TEXT DEFAULT NULL,
                    crypto_amount REAL DEFAULT NULL,
                    exchange_rate REAL DEFAULT NULL,
                    fee_amount REAL DEFAULT 0.0,
                    net_amount REAL DEFAULT NULL,
                    balance_before REAL DEFAULT 0.0,
                    balance_after REAL DEFAULT 0.0,
                    reference_id TEXT DEFAULT NULL,  -- external transaction ID
                    game_session_id INTEGER DEFAULT NULL,
                    status TEXT DEFAULT 'completed',  -- pending, completed, failed, cancelled
                    payment_method TEXT DEFAULT NULL,
                    payment_address TEXT DEFAULT NULL,
                    confirmation_blocks INTEGER DEFAULT NULL,
                    description TEXT,
                    metadata TEXT DEFAULT NULL,  -- JSON for additional data
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TIMESTAMP DEFAULT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (game_session_id) REFERENCES game_sessions (session_id)
                )
            """)
            
            # Enhanced Withdrawals table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS withdrawals (
                    withdrawal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    asset TEXT NOT NULL,
                    amount REAL NOT NULL,
                    amount_usd REAL NOT NULL,
                    address TEXT NOT NULL,
                    fee REAL NOT NULL,
                    fee_usd REAL NOT NULL,
                    net_amount REAL NOT NULL,
                    net_amount_usd REAL NOT NULL,
                    rate_usd REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    transaction_hash TEXT DEFAULT '',
                    confirmation_blocks INTEGER DEFAULT 0,
                    required_confirmations INTEGER DEFAULT 6,
                    error_msg TEXT DEFAULT '',
                    admin_notes TEXT DEFAULT '',
                    processed_by INTEGER DEFAULT NULL,  -- admin user_id
                    priority INTEGER DEFAULT 0,  -- 0=normal, 1=high, 2=urgent
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP DEFAULT NULL,
                    confirmed_at TIMESTAMP DEFAULT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Deposits table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS deposits (
                    deposit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    asset TEXT NOT NULL,
                    amount REAL NOT NULL,
                    amount_usd REAL NOT NULL,
                    rate_usd REAL NOT NULL,
                    payment_method TEXT NOT NULL,  -- crypto, bank_transfer, etc.
                    payment_address TEXT DEFAULT NULL,
                    invoice_id TEXT DEFAULT NULL,
                    transaction_hash TEXT DEFAULT NULL,
                    confirmation_blocks INTEGER DEFAULT 0,
                    required_confirmations INTEGER DEFAULT 6,
                    status TEXT DEFAULT 'pending',  -- pending, confirming, completed, failed, expired
                    expires_at TIMESTAMP DEFAULT NULL,
                    bonus_applied REAL DEFAULT 0.0,
                    bonus_type TEXT DEFAULT NULL,
                    metadata TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TIMESTAMP DEFAULT NULL,
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
                    total_fees_collected REAL DEFAULT 0.0,
                    total_bonuses_paid REAL DEFAULT 0.0,
                    games_played_today INTEGER DEFAULT 0,
                    revenue_today REAL DEFAULT 0.0,
                    profit_today REAL DEFAULT 0.0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_daily_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User achievements table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    achievement_id TEXT NOT NULL,
                    achievement_name TEXT NOT NULL,
                    description TEXT DEFAULT NULL,
                    reward_amount REAL DEFAULT 0.0,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    progress_data TEXT DEFAULT NULL,  -- JSON for tracking progress
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, achievement_id)
                )
            """)
            
            # Referrals table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referee_id INTEGER NOT NULL,
                    referral_code TEXT NOT NULL,
                    bonus_paid_referrer REAL DEFAULT 0.0,
                    bonus_paid_referee REAL DEFAULT 0.0,
                    total_referee_wagered REAL DEFAULT 0.0,
                    commission_earned REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'pending',  -- pending, active, inactive
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    activated_at TIMESTAMP DEFAULT NULL,
                    FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                    FOREIGN KEY (referee_id) REFERENCES users (user_id),
                    UNIQUE(referee_id)
                )
            """)
            
            # Admin actions log
            await db.execute("""
                CREATE TABLE IF NOT EXISTS admin_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_user_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,  -- ban_user, adjust_balance, approve_withdrawal, etc.
                    target_user_id INTEGER DEFAULT NULL,
                    amount REAL DEFAULT NULL,
                    old_value TEXT DEFAULT NULL,
                    new_value TEXT DEFAULT NULL,
                    reason TEXT DEFAULT NULL,
                    ip_address TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_user_id) REFERENCES users (user_id),
                    FOREIGN KEY (target_user_id) REFERENCES users (user_id)
                )
            """)
            
            # System configuration table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    data_type TEXT DEFAULT 'string',  -- string, number, boolean, json
                    description TEXT DEFAULT NULL,
                    updated_by INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (updated_by) REFERENCES users (user_id)
                )
            """)
            
            # User sessions table for tracking logins and activity
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT DEFAULT NULL,
                    ip_address TEXT DEFAULT NULL,
                    user_agent TEXT DEFAULT NULL,
                    platform TEXT DEFAULT NULL,  -- telegram, web, mobile
                    country TEXT DEFAULT NULL,
                    city TEXT DEFAULT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP DEFAULT NULL,
                    session_duration INTEGER DEFAULT 0,  -- in seconds
                    actions_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Game statistics table for analytics
            await db.execute("""
                CREATE TABLE IF NOT EXISTS game_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_type TEXT NOT NULL,
                    date DATE NOT NULL,
                    total_sessions INTEGER DEFAULT 0,
                    total_players INTEGER DEFAULT 0,
                    total_wagered REAL DEFAULT 0.0,
                    total_won REAL DEFAULT 0.0,
                    house_profit REAL DEFAULT 0.0,
                    rtp REAL DEFAULT 0.0,
                    avg_bet REAL DEFAULT 0.0,
                    max_win REAL DEFAULT 0.0,
                    jackpots_hit INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(game_type, date)
                )
            """)
            
            # Bonus campaigns table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bonus_campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,  -- deposit_bonus, free_spins, cashback, etc.
                    amount REAL DEFAULT 0.0,
                    percentage REAL DEFAULT 0.0,
                    min_deposit REAL DEFAULT 0.0,
                    max_bonus REAL DEFAULT 0.0,
                    wagering_requirement REAL DEFAULT 0.0,
                    valid_games TEXT DEFAULT NULL,  -- JSON array of game types
                    is_active BOOLEAN DEFAULT TRUE,
                    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_date TIMESTAMP DEFAULT NULL,
                    usage_limit INTEGER DEFAULT NULL,
                    usage_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User bonus claims table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_bonus_claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    campaign_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    wagering_requirement REAL DEFAULT 0.0,
                    wagered_amount REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'active',  -- active, completed, expired, cancelled
                    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP DEFAULT NULL,
                    expires_at TIMESTAMP DEFAULT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (campaign_id) REFERENCES bonus_campaigns (id)
                )
            """)
            
            # Create indexes for better performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_game_sessions_user_id ON game_sessions(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_game_sessions_game_type ON game_sessions(game_type)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_game_sessions_created_at ON game_sessions(created_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_withdrawals_user_id ON withdrawals(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_deposits_user_id ON deposits(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_deposits_status ON deposits(status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referee_id ON referrals(referee_id)")
            
            # Initialize house balance if it doesn't exist
            await db.execute("""
                INSERT OR IGNORE INTO house_balance (id, balance) VALUES (1, 10000.0)
            """)
            
            # Initialize default system configuration
            system_configs = [
                ('maintenance_mode', 'false', 'boolean', 'Enable/disable maintenance mode'),
                ('min_bet_amount', '1.0', 'number', 'Minimum bet amount in USD'),
                ('max_bet_amount', '1000.0', 'number', 'Maximum bet amount in USD'),
                ('house_edge_slots', '3.5', 'number', 'House edge for slots games (%)'),
                ('house_edge_blackjack', '1.5', 'number', 'House edge for blackjack (%)'),
                ('house_edge_roulette', '2.7', 'number', 'House edge for roulette (%)'),
                ('welcome_bonus_amount', '10.0', 'number', 'Welcome bonus amount in USD'),
                ('daily_bonus_amount', '5.0', 'number', 'Daily bonus amount in USD'),
                ('referral_bonus_amount', '25.0', 'number', 'Referral bonus amount in USD'),
                ('max_withdrawal_daily', '10000.0', 'number', 'Maximum daily withdrawal in USD'),
                ('kyc_required_amount', '1000.0', 'number', 'Amount requiring KYC verification'),
                ('support_email', 'support@casino.com', 'string', 'Support email address'),
                ('bot_version', '2.1.0', 'string', 'Current bot version')
            ]
            
            for config in system_configs:
                await db.execute("""
                    INSERT OR IGNORE INTO system_config (key, value, data_type, description)
                    VALUES (?, ?, ?, ?)
                """, config)
            
            await db.commit()
            logger.info("✅ Enhanced database initialized successfully with comprehensive schema")
            
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
    fee = amount * WITHDRAWAL_FEE_PERCENT  # WITHDRAWAL_FEE_PERCENT is already a decimal (0.02 = 2%)
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
        
        total_in = house_data.get('total_deposits', 0.0) + house_data.get('total_player_losses', 0.0)
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

# --- Enhanced House Balance Management ---

async def get_house_balance_summary() -> dict:
    """Get detailed house balance summary with analytics"""
    try:
        house_data = await get_house_balance()
        
        # Calculate derived metrics
        total_volume = house_data.get('total_deposits', 0.0) + house_data.get('total_player_losses', 0.0)
        total_payouts = house_data.get('total_withdrawals', 0.0) + house_data.get('total_player_wins', 0.0)
        net_profit = total_volume - total_payouts
        
        # Calculate house edge percentage
        total_wagered = house_data.get('total_player_losses', 0.0) + house_data.get('total_player_wins', 0.0)
        house_edge = (house_data.get('total_player_losses', 0.0) / total_wagered * 100) if total_wagered > 0 else 0
        
        # Calculate profit margin
        profit_margin = (net_profit / total_volume * 100) if total_volume > 0 else 0
        
        return {
            'current_balance': house_data.get('balance', 0.0),
            'total_volume': total_volume,
            'total_payouts': total_payouts,
            'net_profit': net_profit,
            'house_edge_percent': house_edge,
            'profit_margin_percent': profit_margin,
            'total_deposits': house_data.get('total_deposits', 0.0),
            'total_withdrawals': house_data.get('total_withdrawals', 0.0),
            'total_player_wins': house_data.get('total_player_wins', 0.0),
            'total_player_losses': house_data.get('total_player_losses', 0.0),
            'last_updated': house_data.get('last_updated', datetime.now().isoformat())
        }
        
    except Exception as e:
        logger.error(f"Error getting house balance summary: {e}")
        return {}

async def reset_daily_house_stats() -> bool:
    """Reset daily house statistics (called by scheduler)"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE house_balance 
                SET games_played_today = 0,
                    revenue_today = 0.0,
                    profit_today = 0.0,
                    last_daily_reset = ?
                WHERE id = 1
            """, (datetime.now().isoformat(),))
            await db.commit()
            logger.info("✅ Daily house statistics reset")
            return True
            
    except Exception as e:
        logger.error(f"Error resetting daily house stats: {e}")
        return False

async def update_daily_house_stats(bet_amount: float, win_amount: float) -> bool:
    """Update daily house statistics"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            house_profit = bet_amount - win_amount
            
            await db.execute("""
                UPDATE house_balance 
                SET games_played_today = games_played_today + 1,
                    revenue_today = revenue_today + ?,
                    profit_today = profit_today + ?
                WHERE id = 1
            """, (bet_amount, house_profit))
            await db.commit()
            return True
            
    except Exception as e:
        logger.error(f"Error updating daily house stats: {e}")
        return False

async def get_house_risk_metrics() -> dict:
    """Calculate house risk metrics and alerts"""
    try:
        house_data = await get_house_balance()
        current_balance = house_data.get('balance', 0.0)
        
        # Risk thresholds
        LOW_BALANCE_THRESHOLD = 1000.0  # Alert when house balance is low
        CRITICAL_BALANCE_THRESHOLD = 500.0  # Critical alert
        
        # Calculate risk level
        if current_balance <= CRITICAL_BALANCE_THRESHOLD:
            risk_level = "CRITICAL"
            risk_color = "🔴"
        elif current_balance <= LOW_BALANCE_THRESHOLD:
            risk_level = "HIGH"
            risk_color = "🟡"
        else:
            risk_level = "LOW"
            risk_color = "🟢"
        
        # Calculate recommended actions
        recommendations = []
        if current_balance <= CRITICAL_BALANCE_THRESHOLD:
            recommendations.append("🚨 URGENT: Replenish house balance immediately")
            recommendations.append("⏸️ Consider temporarily suspending high-limit games")
        elif current_balance <= LOW_BALANCE_THRESHOLD:
            recommendations.append("⚠️ Monitor withdrawals closely")
            recommendations.append("💰 Consider adding funds to house balance")
        
        return {
            'risk_level': risk_level,
            'risk_color': risk_color,
            'current_balance': current_balance,
            'low_threshold': LOW_BALANCE_THRESHOLD,
            'critical_threshold': CRITICAL_BALANCE_THRESHOLD,
            'recommendations': recommendations,
            'is_healthy': current_balance > LOW_BALANCE_THRESHOLD
        }
        
    except Exception as e:
        logger.error(f"Error calculating house risk metrics: {e}")
        return {'risk_level': 'UNKNOWN', 'risk_color': '❓', 'is_healthy': False, 'recommendations': []}

async def adjust_house_balance(admin_user_id: int, amount: float, reason: str) -> bool:
    """Manually adjust house balance (admin only)"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Get current balance
            cursor = await db.execute("SELECT balance FROM house_balance WHERE id = 1")
            current_balance = (await cursor.fetchone())[0]
            
            # Update balance
            new_balance = current_balance + amount
            await db.execute("""
                UPDATE house_balance 
                SET balance = ?,
                    last_updated = ?
                WHERE id = 1
            """, (new_balance, datetime.now().isoformat()))
            
            # Log the adjustment
            await db.execute("""
                INSERT INTO admin_actions 
                (admin_user_id, action_type, amount, old_value, new_value, reason, created_at)
                VALUES (?, 'house_balance_adjustment', ?, ?, ?, ?, ?)
            """, (admin_user_id, amount, str(current_balance), str(new_balance), reason, datetime.now().isoformat()))
            
            await db.commit()
            
            logger.info(f"House balance adjusted by admin {admin_user_id}: {amount:+.2f} (reason: {reason})")
            return True
            
    except Exception as e:
        logger.error(f"Error adjusting house balance: {e}")
        return False

async def get_house_performance_report(days: int = 7) -> dict:
    """Get house performance report for the last N days"""
    try:
        start_date = (datetime.now() - timedelta(days=days)).date()
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Get game statistics for the period
            cursor = await db.execute("""
                SELECT 
                    SUM(bet_amount) as total_wagered,
                    SUM(win_amount) as total_paid,
                    COUNT(*) as total_games,
                    COUNT(DISTINCT user_id) as unique_players,
                    AVG(bet_amount) as avg_bet,
                    MAX(win_amount) as biggest_win
                FROM game_sessions 
                WHERE DATE(created_at) >= ?
            """, (start_date,))
            
            game_stats = await cursor.fetchone()
            
            # Get deposit/withdrawal stats
            cursor = await db.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN type = 'deposit' THEN amount ELSE 0 END), 0) as deposits,
                    COALESCE(SUM(CASE WHEN type = 'withdrawal' THEN amount ELSE 0 END), 0) as withdrawals
                FROM transactions 
                WHERE DATE(created_at) >= ?
            """, (start_date,))
            
            financial_stats = await cursor.fetchone()
            
            # Calculate metrics
            total_wagered = game_stats[0] or 0.0
            total_paid = game_stats[1] or 0.0
            total_games = game_stats[2] or 0
            unique_players = game_stats[3] or 0
            avg_bet = game_stats[4] or 0.0
            biggest_win = game_stats[5] or 0.0
            
            deposits = financial_stats[0] or 0.0
            withdrawals = financial_stats[1] or 0.0
            
            house_profit = total_wagered - total_paid
            house_edge = (house_profit / total_wagered * 100) if total_wagered > 0 else 0
            net_cash_flow = deposits - withdrawals
            
            return {
                'period_days': days,
                'start_date': start_date.isoformat(),
                'total_wagered': total_wagered,
                'total_paid': total_paid,
                'house_profit': house_profit,
                'house_edge_percent': house_edge,
                'total_games': total_games,
                'unique_players': unique_players,
                'avg_bet': avg_bet,
                'biggest_win': biggest_win,
                'deposits': deposits,
                'withdrawals': withdrawals,
                'net_cash_flow': net_cash_flow,
                'profit_margin': (house_profit / (total_wagered + deposits) * 100) if (total_wagered + deposits) > 0 else 0
            }
            
    except Exception as e:
        logger.error(f"Error generating house performance report: {e}")
        return {}

async def get_enhanced_house_balance_display() -> str:
    """Get enhanced house balance display with risk metrics and performance"""
    try:
        summary = await get_house_balance_summary()
        risk_metrics = await get_house_risk_metrics()
        performance = await get_house_performance_report(7)  # Last 7 days
        
        # Format values
        balance_str = await format_usd(summary.get('current_balance', 0.0))
        profit_str = await format_usd(summary.get('net_profit', 0.0))
        volume_str = await format_usd(summary.get('total_volume', 0.0))
        
        # Performance metrics
        weekly_profit_str = await format_usd(performance.get('house_profit', 0.0))
        monthly_profit_str = await format_usd(performance.get('house_profit', 0.0))
        
        # Risk status
        risk_status = f"{risk_metrics.get('risk_color', '❓')} {risk_metrics.get('risk_level', 'UNKNOWN')}"
        
        text = f"""
🏦 <b>ENHANCED HOUSE BALANCE</b> 🏦

💰 <b>Current Balance:</b> {balance_str}
📊 <b>Risk Status:</b> {risk_status}
📈 <b>All-Time Profit:</b> {profit_str}
🎯 <b>House Edge:</b> {summary.get('house_edge_percent', 0):.2f}%
🔄 <b>Total Volume:</b> {volume_str}

⏱️ <b>Performance Summary:</b>
📅 <b>Last 7 Days:</b> {weekly_profit_str}
📅 <b>Last 30 Days:</b> {monthly_profit_str}
🎮 <b>Games (7d):</b> {performance.get('total_games', 0):,}

🚨 <b>Risk Metrics:</b>
🔥 <b>Risk Score:</b> {risk_metrics.get('risk_score', 0):.1f}/10
⚖️ <b>Balance Ratio:</b> {risk_metrics.get('balance_ratio', 0):.2f}
💹 <b>Volatility:</b> {risk_metrics.get('volatility', 'N/A')}

💳 <b>Cash Flow:</b>
📥 <b>Deposits:</b> {await format_usd(summary.get('total_deposits', 0.0))}
📤 <b>Withdrawals:</b> {await format_usd(summary.get('total_withdrawals', 0.0))}
🏆 <b>Player Wins:</b> {await format_usd(summary.get('total_player_wins', 0.0))}
💸 <b>Player Losses:</b> {await format_usd(summary.get('total_player_losses', 0.0))}

<i>Real-time casino financial analytics</i>
"""
        
        # Add risk recommendations if any
        recommendations = risk_metrics.get('recommendations', [])
        if recommendations:
            text += "\n\n🚨 <b>Recommendations:</b>\n"
            for rec in recommendations[:3]:  # Limit to 3 recommendations
                text += f"• {rec}\n"
        
        return text
        
    except Exception as e:
        logger.error(f"Error getting enhanced house balance display: {e}")
        return "❌ <b>Enhanced House Balance:</b> Unable to load data"

# --- Admin Commands for House Balance Management ---

async def admin_house_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to view detailed house balance"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id) and not is_owner(user_id):
        await update.message.reply_text("❌ Access denied. Admin privileges required.")
        return
    
    log_admin_action(user_id, "Viewed house balance")
    
    display_text = await get_enhanced_house_balance_display()
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Risk Analysis", callback_data="admin_house_risk"),
            InlineKeyboardButton("📈 Performance", callback_data="admin_house_performance")
        ],
        [
            InlineKeyboardButton("💰 Adjust Balance", callback_data="admin_adjust_house_balance"),
            InlineKeyboardButton("📋 Daily Report", callback_data="admin_house_daily")
        ],
        [InlineKeyboardButton("🔧 Admin Panel", callback_data="admin_panel")]
    ]
    
    await update.message.reply_text(
        display_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def owner_house_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Owner command to view comprehensive house balance with all analytics"""
    user_id = update.effective_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text("❌ Access denied. Owner privileges required.")
        return
    
    log_admin_action(user_id, "Viewed owner house balance dashboard")
    
    # Get comprehensive data
    summary = await get_house_balance_summary()
    risk_metrics = await get_house_risk_metrics()
    performance_7d = await get_house_performance_report(7)
    performance_30d = await get_house_performance_report(30)
    
    # Format display
    balance_str = await format_usd(summary.get('current_balance', 0.0))
    profit_str = await format_usd(summary.get('net_profit', 0.0))
    volume_str = await format_usd(summary.get('total_volume', 0.0))
    
    risk_color = risk_metrics.get('risk_color', '❓')
    risk_level = risk_metrics.get('risk_level', 'UNKNOWN')
    
    weekly_profit_str = await format_usd(performance_7d.get('house_profit', 0.0))
    monthly_profit_str = await format_usd(performance_30d.get('house_profit', 0.0))
    
    text = f"""
🏦 <b>OWNER HOUSE BALANCE DASHBOARD</b> 🏦

💰 <b>Current Balance:</b> {balance_str}
📊 <b>Risk Status:</b> {risk_color} {risk_level}
📈 <b>All-Time Profit:</b> {profit_str}
🎯 <b>House Edge:</b> {summary.get('house_edge_percent', 0):.2f}%
🔄 <b>Total Volume:</b> {volume_str}

⏱️ <b>Performance Summary:</b>
📅 <b>Last 7 Days:</b> {weekly_profit_str}
📅 <b>Last 30 Days:</b> {monthly_profit_str}
🎮 <b>Games (7d):</b> {performance_7d.get('total_games', 0):,}

🚨 <b>Risk Metrics:</b>
🔥 <b>Risk Score:</b> {risk_metrics.get('risk_score', 0):.1f}/10
⚖️ <b>Balance Ratio:</b> {risk_metrics.get('balance_ratio', 0):.2f}
💹 <b>Volatility:</b> {risk_metrics.get('volatility', 'N/A')}

💳 <b>Cash Flow:</b>
📥 <b>Deposits:</b> {await format_usd(summary.get('total_deposits', 0.0))}
📤 <b>Withdrawals:</b> {await format_usd(summary.get('total_withdrawals', 0.0))}
🏆 <b>Player Wins:</b> {await format_usd(summary.get('total_player_wins', 0.0))}
💸 <b>Player Losses:</b> {await format_usd(summary.get('total_player_losses', 0.0))}

<i>Real-time casino financial monitoring</i>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Full Analytics", callback_data="owner_house_analytics"),
            InlineKeyboardButton("💰 Manual Adjustment", callback_data="owner_adjust_balance")
        ],
        [
            InlineKeyboardButton("📈 Detailed Reports", callback_data="owner_house_reports"),
            InlineKeyboardButton("⚙️ Risk Settings", callback_data="owner_risk_settings")
        ],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def admin_house_balance_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin house balance callback queries"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_admin(user_id) and not is_owner(user_id):
        await query.edit_message_text("❌ Access denied. Admin privileges required.")
        return
    
    if query.data == "admin_house_risk":
        # Show detailed risk analysis
        risk_metrics = await get_house_risk_metrics()
        
        text = f"""
🚨 <b>HOUSE BALANCE RISK ANALYSIS</b> 🚨

📊 <b>Current Risk Level:</b> {risk_metrics.get('risk_color', '❓')} {risk_metrics.get('risk_level', 'UNKNOWN')}
💰 <b>Current Balance:</b> {await format_usd(risk_metrics.get('current_balance', 0.0))}

⚠️ <b>Risk Thresholds:</b>
🟡 <b>Low Risk:</b> > {await format_usd(risk_metrics.get('low_threshold', 1000.0))}
🔴 <b>Critical:</b> < {await format_usd(risk_metrics.get('critical_threshold', 500.0))}

🎯 <b>Health Status:</b> {'✅ Healthy' if risk_metrics.get('is_healthy', False) else '⚠️ Requires Attention'}

📋 <b>Recommendations:</b>
"""
        
        recommendations = risk_metrics.get('recommendations', [])
        if recommendations:
            for rec in recommendations:
                text += f"\n{rec}"
        else:
            text += "\n✅ No immediate actions required"
        
        keyboard = [
            [InlineKeyboardButton("💰 Adjust Balance", callback_data="admin_adjust_house_balance")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_house_balance")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif query.data == "admin_house_performance":
        # Show performance metrics
        performance_7d = await get_house_performance_report(7)
        performance_30d = await get_house_performance_report(30)
        
        text = f"""
📈 <b>HOUSE PERFORMANCE REPORT</b> 📈

🗓️ <b>Last 7 Days:</b>
💰 <b>Profit:</b> {await format_usd(performance_7d.get('house_profit', 0.0))}
🎮 <b>Games:</b> {performance_7d.get('total_games', 0):,}
👥 <b>Players:</b> {performance_7d.get('unique_players', 0):,}
💵 <b>Avg Bet:</b> {await format_usd(performance_7d.get('avg_bet', 0.0))}
🎯 <b>House Edge:</b> {performance_7d.get('house_edge_percent', 0):.2f}%

🗓️ <b>Last 30 Days:</b>
💰 <b>Profit:</b> {await format_usd(performance_30d.get('house_profit', 0.0))}
🎮 <b>Games:</b> {performance_30d.get('total_games', 0):,}
👥 <b>Players:</b> {performance_30d.get('unique_players', 0):,}
💵 <b>Avg Bet:</b> {await format_usd(performance_30d.get('avg_bet', 0.0))}
🎯 <b>House Edge:</b> {performance_30d.get('house_edge_percent', 0):.2f}%

💸 <b>Cash Flow (30d):</b>
📥 <b>Deposits:</b> {await format_usd(performance_30d.get('deposits', 0.0))}
📤 <b>Withdrawals:</b> {await format_usd(performance_30d.get('withdrawals', 0.0))}
📊 <b>Net Flow:</b> {await format_usd(performance_30d.get('net_cash_flow', 0.0))}
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 Risk Analysis", callback_data="admin_house_risk")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_house_balance")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif query.data == "admin_adjust_house_balance":
        # Prompt for balance adjustment
        text = """
💰 <b>ADJUST HOUSE BALANCE</b> 💰

Please enter the adjustment amount in USD.
Use positive numbers to add funds, negative to deduct.

Examples:
• <code>+1000</code> - Add $1000
• <code>-500</code> - Deduct $500
• <code>2500</code> - Add $2500

⚠️ <b>Warning:</b> This will directly modify the house balance.
"""
        
        keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_house_balance")]]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        
        # Set state for amount input
        context.user_data['awaiting_house_adjustment'] = True
    
    elif query.data == "admin_house_daily":
        # Show today's statistics
        house_data = await get_house_balance()
        
        text = f"""
📅 <b>TODAY'S HOUSE STATISTICS</b> 📅

🎮 <b>Games Played:</b> {house_data.get('games_played_today', 0):,}
💰 <b>Revenue Today:</b> {await format_usd(house_data.get('revenue_today', 0.0))}
📈 <b>Profit Today:</b> {await format_usd(house_data.get('profit_today', 0.0))}

🕐 <b>Last Reset:</b> {house_data.get('last_daily_reset', 'Never')[:10]}
🕐 <b>Last Updated:</b> {house_data.get('last_updated', 'Never')[:16]}

🔄 <b>Operations:</b>
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Reset Daily Stats", callback_data="admin_reset_daily_stats")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_house_balance")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif query.data == "admin_reset_daily_stats":
        # Reset daily statistics
        success = await reset_daily_house_stats()
        
        if success:
            await query.edit_message_text(
                "✅ <b>Daily statistics reset successfully!</b>\n\n"
                "All daily counters have been reset to zero.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Daily Stats", callback_data="admin_house_daily")]
                ]),
                parse_mode=ParseMode.HTML            )
            log_admin_action(user_id, "Reset daily house statistics")
        else:
            await query.edit_message_text(
                "❌ <b>Error resetting daily statistics</b>\n\n"
                "Please try again or contact support.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_house_daily")]
                ]),
                parse_mode=ParseMode.HTML
            )

async def handle_house_balance_adjustment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle house balance adjustment amount input"""
    if 'awaiting_house_adjustment' not in context.user_data:
        return
    
    user_id = update.effective_user.id
    if not is_admin(user_id) and not is_owner(user_id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    try:
        amount_str = update.message.text.strip()
        # Remove any + prefix
        if amount_str.startswith('+'):
            amount_str = amount_str[1:]
        
        amount = float(amount_str)
        
        if abs(amount) > 100000:  # Prevent huge adjustments
            await update.message.reply_text("❌ Amount too large. Maximum adjustment is ±$100,000.")
            return
        
        # Clear state
        del context.user_data['awaiting_house_adjustment']
        
        # Prompt for reason
        context.user_data['house_adjustment_amount'] = amount
        
        keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_house_balance")]]
        
        await update.message.reply_text(
            f"💰 <b>Confirm House Balance Adjustment</b>\n\n"
            f"Amount: <b>{amount:+.2f} USD</b>\n\n"
            f"Please provide a reason for this adjustment:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        
        # Set state for reason input
        context.user_data['awaiting_adjustment_reason'] = True
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number (e.g., 1000 or -500)")

async def handle_house_adjustment_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle house balance adjustment reason input"""
    if 'awaiting_adjustment_reason' not in context.user_data:
        return
    
    user_id = update.effective_user.id
    if not is_admin(user_id) and not is_owner(user_id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    amount = context.user_data.get('house_adjustment_amount', 0.0)
    reason = update.message.text.strip()
    
    if len(reason) < 5:
        await update.message.reply_text("❌ Please provide a more detailed reason (minimum 5 characters).")
        return
    
    # Clear states
    del context.user_data['awaiting_adjustment_reason']
    del context.user_data['house_adjustment_amount']
    
    # Apply adjustment
    success = await adjust_house_balance(user_id, amount, reason)
    
    if success:
        keyboard = [[InlineKeyboardButton("🏦 View House Balance", callback_data="admin_house_balance")]]
        
        await update.message.reply_text(
            f"✅ <b>House Balance Adjusted Successfully</b>\n\n"
            f"Amount: <b>{amount:+.2f} USD</b>\n"
            f"Reason: <i>{reason}</i>\n\n"
            f"The adjustment has been logged for audit purposes.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        
        log_admin_action(user_id, f"Adjusted house balance by {amount:+.2f} USD: {reason}")
    else:
        await update.message.reply_text(
            "❌ <b>Error adjusting house balance</b>\n\n"
            "Please try again or contact support."
        )

# --- Enhanced Text Input Handler ---

async def handle_text_input_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all text input for various states"""
    user_id = update.effective_user.id
    
    # House balance adjustment flows (admin only)
    if is_admin(user_id) or is_owner(user_id):
        if 'awaiting_house_adjustment' in context.user_data:
            await handle_house_balance_adjustment(update, context)
            return
        elif 'awaiting_adjustment_reason' in context.user_data:
            await handle_house_adjustment_reason(update, context)
            return
    
    # Deposit/withdrawal flows
    if 'awaiting_deposit_amount' in context.user_data:
        await handle_deposit_amount_input(update, context)
        return
    elif 'awaiting_withdraw_amount' in context.user_data:
        await handle_withdraw_amount_input(update, context)
        return
    elif 'awaiting_withdraw_address' in context.user_data:
        await handle_withdraw_address_input(update, context)
        return
    
    # Default: ignore unrecognized text to prevent interference with games
    logger.debug(f"Ignored text input from user {user_id}: {update.message.text}")

# --- Missing Deposit/Withdrawal Handlers (Stubs) ---
# These should be implemented based on your crypto payment system

async def handle_deposit_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle deposit amount input - implement based on your crypto system"""
    await update.message.reply_text("🚧 Deposit system integration needed")

async def handle_withdraw_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal amount input - implement based on your crypto system"""
    await update.message.reply_text("🚧 Withdrawal system integration needed")

async def handle_withdraw_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal address input - implement based on your crypto system"""
    await update.message.reply_text("🚧 Withdrawal system integration needed")

# --- Import Required Modules ---
import os
import re
import time
import uuid
import random
import hashlib
import asyncio
import logging
import aiohttp
import aiosqlite
import nest_asyncio
from typing import Dict, List, Optional, Tuple

# --- Missing Database Helper Functions ---

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

# --- Application Setup ---

async def main():
    """Main function to run the bot"""
    try:
        # Initialize database
        await init_db()
        
        # Ensure required columns exist
        await ensure_weekly_bonus_column()
        await ensure_referral_columns()
        
        # Build application
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("housebalance", admin_house_balance_command))
        application.add_handler(CommandHandler("owner_house", owner_house_balance_command))
        
        # Add callback query handlers
        application.add_handler(CallbackQueryHandler(admin_house_balance_callbacks, pattern="^admin_house_"))
        application.add_handler(CallbackQueryHandler(admin_house_balance_callbacks, pattern="^admin_reset_daily_stats$"))
        application.add_handler(CallbackQueryHandler(admin_house_balance_callbacks, pattern="^admin_adjust_house_balance$"))
        
        # Add text message handler
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input_main))
        
        # Add other handlers here (start, games, etc.)
        # application.add_handler(CommandHandler("start", start_command))
        # application.add_handler(CallbackQueryHandler(callback_handler))
        
        logger.info("🚀 Casino Bot started successfully!")
        logger.info(f"🏦 House Balance System: ✅ Active")
        logger.info(f"🔧 Admin Commands: ✅ Ready")
        logger.info(f"📊 Analytics: ✅ Enhanced")
        
        # Start polling
        await application.run_polling()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())