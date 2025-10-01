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
import json
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

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

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

# --- Enhanced House Balance Management System ---

class HouseBalanceManager:
    """Comprehensive house balance management system"""
    
    def __init__(self):
        self.daily_stats_cache = {}
        self.last_cache_update = None
    
    async def initialize_house_balance(self):
        """Initialize house balance with default values"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("""
                    INSERT OR IGNORE INTO house_balance 
                    (id, balance, total_player_losses, total_player_wins, 
                     total_deposits, total_withdrawals, total_fees_collected,
                     total_bonuses_paid, games_played_today, revenue_today, 
                     profit_today, last_updated, last_daily_reset)
                    VALUES (1, 10000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, ?, ?)
                """, (datetime.now().isoformat(), datetime.now().isoformat()))
                await db.commit()
                logger.info("House balance initialized with $10,000")
        except Exception as e:
            logger.error(f"Error initializing house balance: {e}")
    
    async def get_house_balance_detailed(self) -> dict:
        """Get detailed house balance information"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM house_balance WHERE id = 1")
                result = await cursor.fetchone()
                
                if result:
                    return dict(result)
                else:
                    await self.initialize_house_balance()
                    return await self.get_house_balance_detailed()
                    
        except Exception as e:
            logger.error(f"Error getting house balance: {e}")
            return self._get_default_house_balance()
    
    def _get_default_house_balance(self) -> dict:
        """Get default house balance structure"""
        return {
            'id': 1,
            'balance': 10000.0,
            'total_player_losses': 0.0,
            'total_player_wins': 0.0,
            'total_deposits': 0.0,
            'total_withdrawals': 0.0,
            'total_fees_collected': 0.0,
            'total_bonuses_paid': 0.0,
            'games_played_today': 0,
            'revenue_today': 0.0,
            'profit_today': 0.0,
            'last_updated': datetime.now().isoformat(),
            'last_daily_reset': datetime.now().isoformat()
        }
    
    async def process_game_outcome(self, user_id: int, game_type: str, bet_amount: float, 
                                 win_amount: float, house_edge: float = 0.0) -> bool:
        """Process game outcome and update house balance"""
        try:
            house_profit = bet_amount - win_amount
            
            async with aiosqlite.connect(DB_PATH) as db:
                # Update house balance
                await db.execute("""
                    UPDATE house_balance 
                    SET balance = balance + ?,
                        total_player_losses = total_player_losses + ?,
                        total_player_wins = total_player_wins + ?,
                        games_played_today = games_played_today + 1,
                        revenue_today = revenue_today + ?,
                        profit_today = profit_today + ?,
                        last_updated = ?
                    WHERE id = 1
                """, (house_profit, bet_amount, win_amount, bet_amount, house_profit, 
                      datetime.now().isoformat()))
                
                # Log transaction for house
                await self._log_house_transaction(
                    'game_profit' if house_profit > 0 else 'game_loss',
                    abs(house_profit),
                    f"{game_type} game - User {user_id}",
                    {'user_id': user_id, 'game_type': game_type, 'bet': bet_amount, 'win': win_amount}
                )
                
                await db.commit()
                logger.debug(f"House balance updated: {house_profit:+.2f} from {game_type} game")
                return True
                
        except Exception as e:
            logger.error(f"Error processing game outcome for house balance: {e}")
            return False
    
    async def process_deposit(self, user_id: int, amount: float, asset: str = 'USD',
                            fee: float = 0.0) -> bool:
        """Process user deposit and update house balance"""
        try:
            net_house_gain = amount - fee  # House gains deposit minus any fees paid
            
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("""
                    UPDATE house_balance 
                    SET balance = balance + ?,
                        total_deposits = total_deposits + ?,
                        total_fees_collected = total_fees_collected + ?,
                        last_updated = ?
                    WHERE id = 1
                """, (net_house_gain, amount, fee, datetime.now().isoformat()))
                
                await self._log_house_transaction(
                    'deposit_received',
                    amount,
                    f"Deposit from user {user_id}",
                    {'user_id': user_id, 'asset': asset, 'fee': fee}
                )
                
                await db.commit()
                logger.debug(f"House balance increased by deposit: +{net_house_gain:.2f}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing deposit for house balance: {e}")
            return False
    
    async def process_withdrawal(self, user_id: int, amount: float, fee: float = 0.0) -> bool:
        """Process user withdrawal and update house balance"""
        try:
            house_loss = amount - fee  # House loses withdrawal amount but keeps fee
            
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("""
                    UPDATE house_balance 
                    SET balance = balance - ?,
                        total_withdrawals = total_withdrawals + ?,
                        total_fees_collected = total_fees_collected + ?,
                        last_updated = ?
                    WHERE id = 1
                """, (house_loss, amount, fee, datetime.now().isoformat()))
                
                await self._log_house_transaction(
                    'withdrawal_paid',
                    amount,
                    f"Withdrawal to user {user_id}",
                    {'user_id': user_id, 'fee': fee}
                )
                
                await db.commit()
                logger.debug(f"House balance decreased by withdrawal: -{house_loss:.2f}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing withdrawal for house balance: {e}")
            return False
    
    async def process_bonus_payment(self, user_id: int, amount: float, bonus_type: str) -> bool:
        """Process bonus payment and update house balance"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("""
                    UPDATE house_balance 
                    SET balance = balance - ?,
                        total_bonuses_paid = total_bonuses_paid + ?,
                        last_updated = ?
                    WHERE id = 1
                """, (amount, amount, datetime.now().isoformat()))
                
                await self._log_house_transaction(
                    'bonus_paid',
                    amount,
                    f"{bonus_type} bonus to user {user_id}",
                    {'user_id': user_id, 'bonus_type': bonus_type}
                )
                
                await db.commit()
                logger.debug(f"House balance decreased by bonus: -{amount:.2f}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing bonus payment for house balance: {e}")
            return False
    
    async def _log_house_transaction(self, transaction_type: str, amount: float, 
                                   description: str, metadata: dict = None):
        """Log house balance transaction"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                metadata_json = json.dumps(metadata) if metadata else None
                await db.execute("""
                    INSERT INTO transactions 
                    (user_id, type, subtype, amount, description, metadata, created_at)
                    VALUES (0, 'house_operation', ?, ?, ?, ?, ?)
                """, (transaction_type, amount, description, metadata_json, datetime.now().isoformat()))
                await db.commit()
        except Exception as e:
            logger.error(f"Error logging house transaction: {e}")
    
    async def reset_daily_stats(self):
        """Reset daily statistics (call daily)"""
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
                logger.info("Daily house balance stats reset")
        except Exception as e:
            logger.error(f"Error resetting daily stats: {e}")
    
    async def get_house_analytics(self, days: int = 30) -> dict:
        """Get comprehensive house analytics"""
        try:
            house_data = await self.get_house_balance_detailed()
            
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                
                # Get daily trends
                cursor = await db.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        SUM(CASE WHEN type = 'deposit' THEN amount ELSE 0 END) as daily_deposits,
                        SUM(CASE WHEN type = 'withdrawal' THEN amount ELSE 0 END) as daily_withdrawals,
                        SUM(CASE WHEN type = 'bet' THEN amount ELSE 0 END) as daily_bets,
                        SUM(CASE WHEN type = 'win' THEN amount ELSE 0 END) as daily_wins,
                        COUNT(CASE WHEN type = 'bet' THEN 1 END) as daily_games
                    FROM transactions 
                    WHERE created_at >= datetime('now', '-{} days')
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """.format(days))
                daily_trends = [dict(row) for row in await cursor.fetchall()]
                
                # Get game profitability
                cursor = await db.execute("""
                    SELECT 
                        gs.game_type,
                        COUNT(*) as sessions,
                        SUM(gs.bet_amount) as total_wagered,
                        SUM(gs.win_amount) as total_paid,
                        SUM(gs.bet_amount - gs.win_amount) as house_profit,
                        AVG(gs.bet_amount) as avg_bet,
                        MAX(gs.win_amount) as max_win
                    FROM game_sessions gs
                    WHERE gs.created_at >= datetime('now', '-{} days')
                    GROUP BY gs.game_type
                    ORDER BY house_profit DESC
                """.format(days))
                game_profitability = [dict(row) for row in await cursor.fetchall()]
                
                # Calculate key metrics
                total_in = house_data['total_deposits']
                total_out = house_data['total_withdrawals'] + house_data['total_player_wins'] + house_data['total_bonuses_paid']
                net_profit = house_data['total_player_losses'] + total_in - total_out
                
                rtp = (house_data['total_player_wins'] / house_data['total_player_losses'] * 100) if house_data['total_player_losses'] > 0 else 0
                house_edge = 100 - rtp
                
                return {
                    'current_balance': house_data['balance'],
                    'net_profit': net_profit,
                    'total_revenue': house_data['total_player_losses'] + house_data['total_deposits'],
                    'total_expenses': house_data['total_player_wins'] + house_data['total_withdrawals'] + house_data['total_bonuses_paid'],
                    'house_edge_percent': house_edge,
                    'rtp_percent': rtp,
                    'daily_trends': daily_trends,
                    'game_profitability': game_profitability,
                    'fees_collected': house_data['total_fees_collected'],
                    'bonuses_paid': house_data['total_bonuses_paid'],
                    'today_stats': {
                        'games_played': house_data['games_played_today'],
                        'revenue': house_data['revenue_today'],
                        'profit': house_data['profit_today']
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting house analytics: {e}")
            return {}
    
    async def check_house_balance_health(self) -> dict:
        """Check house balance health and return warnings"""
        try:
            house_data = await self.get_house_balance_detailed()
            warnings = []
            status = "healthy"
            
            # Check if balance is too low
            if house_data['balance'] < 1000:
                warnings.append("House balance is critically low")
                status = "critical"
            elif house_data['balance'] < 5000:
                warnings.append("House balance is low")
                status = "warning"
            
            # Check if too much is being paid out
            if house_data['total_player_wins'] > 0:
                payout_ratio = house_data['total_player_wins'] / house_data['total_player_losses']
                if payout_ratio > 0.98:  # More than 98% payout
                    warnings.append("Payout ratio is very high")
                    status = "warning"
            
            # Check daily performance
            if house_data['profit_today'] < -1000:
                warnings.append("Significant daily losses")
                status = "warning"
            
            return {
                'status': status,
                'warnings': warnings,
                'balance': house_data['balance'],
                'daily_profit': house_data['profit_today']
            }
            
        except Exception as e:
            logger.error(f"Error checking house balance health: {e}")
            return {'status': 'error', 'warnings': ['Unable to check balance health']}
    
    async def get_formatted_house_display(self) -> str:
        """Get formatted house balance display for admin panel"""
        try:
            analytics = await self.get_house_analytics()
            health = await self.check_house_balance_health()
            
            status_emoji = {
                'healthy': '🟢',
                'warning': '🟡', 
                'critical': '🔴',
                'error': '⚫'
            }
            
            balance_str = await format_usd(analytics.get('current_balance', 0))
            net_profit_str = await format_usd(analytics.get('net_profit', 0))
            revenue_str = await format_usd(analytics.get('total_revenue', 0))
            expenses_str = await format_usd(analytics.get('total_expenses', 0))
            
            today_profit_str = await format_usd(analytics.get('today_stats', {}).get('profit', 0))
            today_revenue_str = await format_usd(analytics.get('today_stats', {}).get('revenue', 0))
            
            house_edge = analytics.get('house_edge_percent', 0)
            rtp = analytics.get('rtp_percent', 0)
            
            profit_emoji = "📈" if analytics.get('net_profit', 0) >= 0 else "📉"
            
            display = f"""
{status_emoji.get(health['status'], '⚫')} <b>HOUSE BALANCE SYSTEM</b> {status_emoji.get(health['status'], '⚫')}

💰 <b>Current Balance:</b> {balance_str}
{profit_emoji} <b>Net Profit:</b> {net_profit_str}
📊 <b>House Edge:</b> {house_edge:.2f}% | <b>RTP:</b> {rtp:.2f}%

📈 <b>Total Revenue:</b> {revenue_str}
📉 <b>Total Expenses:</b> {expenses_str}

🔥 <b>Today's Performance:</b>
💵 Revenue: {today_revenue_str}
💎 Profit: {today_profit_str}
🎮 Games: {analytics.get('today_stats', {}).get('games_played', 0)}

💳 <b>Fees Collected:</b> {await format_usd(analytics.get('fees_collected', 0))}
🎁 <b>Bonuses Paid:</b> {await format_usd(analytics.get('bonuses_paid', 0))}
"""
            
            if health['warnings']:
                display += f"\n⚠️ <b>Warnings:</b>\n"
                for warning in health['warnings']:
                    display += f"• {warning}\n"
            
            display += f"\n<i>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
            
            return display
            
        except Exception as e:
            logger.error(f"Error formatting house display: {e}")
            return "❌ <b>House Balance:</b> Unable to load data"

# Initialize global house balance manager
house_balance_manager = HouseBalanceManager()

# --- Message Handlers ---

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    # Register or update user in the database
    await create_user(user_id, username)
    
    # Send welcome message with main menu
    await update.message.reply_text(
        "Welcome to the Enhanced Telegram Casino Bot! 🎉\n\n"
        "Use the menu below to navigate the casino, play games, or manage your account.\n\n"
        "For assistance, contact our support team.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Now", callback_data="mini_app_centre")],
            [InlineKeyboardButton("💰 Deposit", callback_data="deposit")],
            [InlineKeyboardButton("🏦 Withdraw", callback_data="withdraw")],
            [InlineKeyboardButton("📊 My Stats", callback_data="user_stats")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
            [InlineKeyboardButton("🆘 Support", url="https://t.me/casino_support")]
        ])
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command"""
    await update.message.reply_text(
        "Need assistance? Contact our support team:\n"
        "Telegram: @casino_support\n"
        "Email: support@casino.com\n\n"
        "For instant answers, visit our FAQ section in the mini app.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📖 FAQ", callback_data="faq")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ])
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo the received message (for testing)"""
    await update.message.reply_text(f"🔄 You said: {update.message.text}")

# --- Owner/Admin Commands ---

async def owner_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command to check house balance"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Unauthorized access.")
        return
    
    balance = await house_balance_manager.get_formatted_house_display()
    await update.message.reply_text(f"🏦 House Balance System:\n{balance}", parse_mode=ParseMode.HTML)

async def owner_set_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command to set house balance"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Unauthorized access.")
        return
    
    try:
        amount = float(context.args[0])
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE house_balance 
                SET balance = ?, last_updated = ?
                WHERE id = 1
            """, (amount, datetime.now().isoformat()))
            await db.commit()
        
        await update.message.reply_text(f"✅ House balance updated to {amount:.2f} USD.")
    except Exception as e:
        await update.message.reply_text(f"Error updating balance: {e}")

async def owner_daily_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command to reset daily stats"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Unauthorized access.")
        return
    
    await house_balance_manager.reset_daily_stats()
    await update.message.reply_text("✅ Daily stats reset.")

async def owner_set_edge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command to set house edge"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Unauthorized access.")
        return
    
    try:
        game_type = context.args[0]
        edge = float(context.args[1])
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(f"""
                UPDATE system_config 
                SET value = ? 
                WHERE key = 'house_edge_{game_type}'
            """, (edge,))
            await db.commit()
        
        await update.message.reply_text(f"✅ House edge for {game_type} set to {edge:.2f}%.")
    except Exception as e:
        await update.message.reply_text(f"Error setting house edge: {e}")

# --- Owner House Balance Management Commands ---

async def owner_house_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command to view detailed house analytics"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Unauthorized access.")
        return
    
    try:
        analytics = await house_balance_manager.get_house_analytics(30)
        health = await house_balance_manager.check_house_balance_health()
        
        status_text = {
            'healthy': '🟢 Healthy',
            'warning': '🟡 Warning', 
            'critical': '🔴 Critical',
            'error': '⚫ Error'
        }
        
        text = f"""
📊 <b>HOUSE ANALYTICS (30 Days)</b>

🏥 <b>Status:</b> {status_text.get(health['status'], 'Unknown')}
💰 <b>Current Balance:</b> {await format_usd(analytics.get('current_balance', 0))}
📈 <b>Net Profit:</b> {await format_usd(analytics.get('net_profit', 0))}

📊 <b>Financial Overview:</b>
💵 Total Revenue: {await format_usd(analytics.get('total_revenue', 0))}
💸 Total Expenses: {await format_usd(analytics.get('total_expenses', 0))}
🎯 House Edge: {analytics.get('house_edge_percent', 0):.2f}%
🔄 RTP: {analytics.get('rtp_percent', 0):.2f}%

🔥 <b>Today's Performance:</b>
🎮 Games Played: {analytics.get('today_stats', {}).get('games_played', 0)}
💵 Revenue: {await format_usd(analytics.get('today_stats', {}).get('revenue', 0))}
💎 Profit: {await format_usd(analytics.get('today_stats', {}).get('profit', 0))}

💳 <b>Fees & Bonuses:</b>
💰 Fees Collected: {await format_usd(analytics.get('fees_collected', 0))}
🎁 Bonuses Paid: {await format_usd(analytics.get('bonuses_paid', 0))}
"""
        
        if health['warnings']:
            text += f"\n⚠️ <b>Warnings:</b>\n"
            for warning in health['warnings']:
                text += f"• {warning}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await update.message.reply_text(f"Error getting analytics: {e}")

async def owner_reset_daily_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command to reset daily statistics"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Unauthorized access.")
        return
    
    try:
        await house_balance_manager.reset_daily_stats()
        await update.message.reply_text("✅ Daily statistics have been reset.")
    except Exception as e:
        await update.message.reply_text(f"Error resetting daily stats: {e}")

async def owner_game_profitability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command to view game profitability"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Unauthorized access.")
        return
    
    try:
        analytics = await house_balance_manager.get_house_analytics(30)
        games = analytics.get('game_profitability', [])
        
        if not games:
            await update.message.reply_text("No game data available.")
            return
        
        text = "🎮 <b>GAME PROFITABILITY (30 Days)</b>\n\n"
        
        for game in games[:10]:  # Top 10 games
            game_type = game.get('game_type', 'Unknown')
            sessions = game.get('sessions', 0)
            profit = game.get('house_profit', 0)
            wagered = game.get('total_wagered', 0)
            
            profit_emoji = "📈" if profit >= 0 else "📉"
            
            text += f"{profit_emoji} <b>{game_type.title()}</b>\n"
            text += f"Sessions: {sessions} | Profit: {await format_usd(profit)}\n"
            text += f"Wagered: {await format_usd(wagered)}\n\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await update.message.reply_text(f"Error getting game profitability: {e}")

# Add these commands to the bot handlers
async def register_owner_commands(application: Application):
    """Register owner-only commands"""
    application.add_handler(CommandHandler("house_balance", owner_balance))
    application.add_handler(CommandHandler("house_analytics", owner_house_analytics))
    application.add_handler(CommandHandler("reset_daily", owner_reset_daily_stats))
    application.add_handler(CommandHandler("game_profits", owner_game_profitability))
    application.add_handler(CommandHandler("set_balance", owner_set_balance))

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

async def handle_deposit_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text input for deposit amount."""
    if 'awaiting_deposit_amount' not in context.user_data:
        return
    crypto_type = context.user_data['awaiting_deposit_amount']
    try:
        amount_usd = float(update.message.text.replace('$', '').replace(',', ''))
        if amount_usd < 1.0:
            await update.message.reply_text("❌ Minimum deposit is $1.00 USD.")
            return
        if amount_usd > 10000.0:
            await update.message.reply_text("❌ Maximum deposit is $10,000.00 USD per transaction.")
            return
        del context.user_data['awaiting_deposit_amount']
        await process_deposit_payment(update, context, crypto_type, amount_usd)
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number (e.g., 50 for $50).")

async def process_deposit_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, crypto_type: str, amount_usd: float) -> None:
    """Process deposit payment and create CryptoBot invoice"""
    query = getattr(update, 'callback_query', None)
    try:
        rate = await get_crypto_usd_rate(crypto_type)
        if rate <= 0:
            await update.message.reply_text("❌ Unable to fetch crypto rate. Please try again later.")
            return
        crypto_amount = amount_usd / rate
        user_id = query.from_user.id if query else update.message.from_user.id
        invoice_data = await create_crypto_invoice(crypto_type, crypto_amount, user_id)
        if not invoice_data.get('ok'):
            await update.message.reply_text(f"❌ Error creating invoice: {invoice_data.get('error', 'Unknown error')}")
            return
        invoice = invoice_data['result']
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
        await update.message.reply_text("❌ Error processing deposit. Please try again later.")

async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the withdrawal process."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
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
            f"❌ Minimum withdrawal is {await format_usd(MIN_WITHDRAWAL_USD)}.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]])
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
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found.")
        return
    balance = user['balance']
    fee_amount = calculate_withdrawal_fee(balance)
    max_withdrawal = min(balance - fee_amount, MAX_WITHDRAWAL_USD)
    text = f"""
🪙 <b>WITHDRAW LITECOIN (LTC)</b> 🪙

💸 <b>Available to Withdraw:</b> {await format_usd(max_withdrawal)}

Please enter the amount you wish to withdraw in USD (e.g., "50" for $50.00).
"""
    keyboard = [[InlineKeyboardButton("🔙 Back to Withdraw", callback_data="withdraw")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    context.user_data['awaiting_withdraw_amount'] = 'LTC'

async def handle_withdraw_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'awaiting_withdraw_amount' not in context.user_data:
        return
    crypto_type = context.user_data['awaiting_withdraw_amount']
    user_id = update.message.from_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("❌ User not found.")
        return
    try:
        amount_usd = float(update.message.text.replace('$', '').replace(',', ''))
        if amount_usd < MIN_WITHDRAWAL_USD:
            await update.message.reply_text(f"❌ Minimum withdrawal is {await format_usd(MIN_WITHDRAWAL_USD)}.")
            return
        if amount_usd > MAX_WITHDRAWAL_USD:
            await update.message.reply_text(f"❌ Maximum withdrawal is {await format_usd(MAX_WITHDRAWAL_USD)} per transaction.")
            return
        if amount_usd > user['balance']:
            await update.message.reply_text("❌ Insufficient balance.")
            return
        del context.user_data['awaiting_withdraw_amount']
        context.user_data['pending_withdraw_amount'] = amount_usd
        await update.message.reply_text("Please enter your Litecoin (LTC) withdrawal address:")
        context.user_data['awaiting_withdraw_address'] = 'LTC'
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number (e.g., 50 for $50).")

async def handle_withdraw_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'awaiting_withdraw_address' not in context.user_data:
        return
    crypto_type = context.user_data['awaiting_withdraw_address']
    address = update.message.text.strip()
    user_id = update.message.from_user.id
    amount_usd = context.user_data.get('pending_withdraw_amount', 0.0)
    if not validate_crypto_address(address, crypto_type):
        await update.message.reply_text("❌ Invalid Litecoin address format. Please try again.")
        return
    # Check withdrawal limits
    limits = await check_withdrawal_limits(user_id, amount_usd)
    if not limits['allowed']:
        await update.message.reply_text(f"❌ {limits['reason']}")
        return
    # Calculate crypto amount
    rate = await get_crypto_usd_rate(crypto_type)
    if rate <= 0:
        await update.message.reply_text("❌ Unable to fetch crypto rate. Please try again later.")
        return
    crypto_amount = amount_usd / rate
    fee = calculate_withdrawal_fee(crypto_amount)
    net_amount = crypto_amount - fee
    # Log withdrawal
    withdrawal_id = await log_withdrawal(user_id, crypto_type, crypto_amount, address, fee, net_amount)
    if withdrawal_id:
        await update.message.reply_text(
            f"✅ Withdrawal request submitted!\nAmount: {crypto_amount:.8f} {crypto_type}\nFee: {fee:.8f} {crypto_type}\nNet: {net_amount:.8f} {crypto_type}\nAddress: {address}\nYour withdrawal will be processed soon."
        )
        # Update balances atomically
        if not await deduct_balance(user_id, amount_usd):
            await update.message.reply_text("❌ Failed to process withdrawal. Please try again.")
        else:
            # Update house balance using new system
            await house_balance_manager.process_withdrawal(user_id, amount_usd, fee)
    else:
        await update.message.reply_text("❌ Error submitting withdrawal request. Please try again later.")
    del context.user_data['awaiting_withdraw_address']
    context.user_data.pop('pending_withdraw_amount', None)

# Register handlers in main bot setup (ensure these are present in Application setup)
def register_casino_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("deposit", deposit_callback))
    application.add_handler(CommandHandler("withdraw", withdraw_start))
    application.add_handler(CallbackQueryHandler(deposit_callback, pattern=r"^deposit$"))
    application.add_handler(CallbackQueryHandler(deposit_crypto_callback, pattern=r"^deposit_LTC$"))
    application.add_handler(CallbackQueryHandler(withdraw_start, pattern=r"^withdraw$"))
    application.add_handler(CallbackQueryHandler(withdraw_crypto_callback, pattern=r"^withdraw_LTC$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input_main))
    # ...existing code...

# --- Keep-Alive Endpoint and Port Binding for Deployment ---

import os
from flask import Flask

app = Flask(__name__)

@app.route('/keepalive')
def keep_alive():
    return "OK", 200

# --- Flask and Telegram Bot Runner ---

import threading
import asyncio

def run_flask():
    port = int(os.environ.get("PORT", 8001))
    app.run(host="0.0.0.0", port=port)

async def run_telegram_bot_async():
    await init_db()  # Ensure DB is ready
    await house_balance_manager.initialize_house_balance()  # Initialize house balance system

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Minimal handlers for bot functionality
    async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Welcome to Axis Casino Bot! Use the menu to play games or manage your account.")

    application.add_handler(CommandHandler("start", start_handler))
    # Add your other handlers here, e.g.:
    # application.add_handler(CallbackQueryHandler(callback_handler))
    # application.add_handler(MessageHandler(filters.TEXT, handle_text_input_main))

    await application.run_polling()

def run_telegram_bot():
    asyncio.run(run_telegram_bot_async())

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    run_telegram_bot()