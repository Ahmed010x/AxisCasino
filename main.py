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

# Import game modules
try:
    from bot.games.slots import handle_slots_callback
    from bot.games.dice import handle_dice_callback, handle_custom_bet_input as handle_dice_custom_bet
    from bot.games.blackjack import handle_blackjack_callback, handle_custom_bet_input as handle_blackjack_custom_bet
    from bot.games.roulette import handle_roulette_callback, handle_custom_bet_input as handle_roulette_custom_bet
    from bot.games.coinflip import handle_coinflip_callback, handle_custom_bet_input as handle_coinflip_custom_bet
    from bot.games.prediction import handle_prediction_callback, handle_custom_bet_input as handle_prediction_custom_bet
    from bot.games.basketball import handle_basketball_callback, handle_custom_bet_input as handle_basketball_custom_bet
except ImportError as e:
    logger.warning(f"Could not import game modules: {e}")
    # Define placeholder functions
    async def handle_slots_callback(update, context):
        await update.callback_query.edit_message_text("🚧 Slots game temporarily unavailable")
    async def handle_dice_callback(update, context):
        await update.callback_query.edit_message_text("🚧 Dice game temporarily unavailable")
    async def handle_prediction_callback(update, context):
        await update.callback_query.edit_message_text("🚧 Prediction games temporarily unavailable")
    async def handle_blackjack_callback(update, context):
        await update.callback_query.edit_message_text("🚧 Blackjack game temporarily unavailable")
    async def handle_roulette_callback(update, context):
        await update.callback_query.edit_message_text("🚧 Roulette game temporarily unavailable")
    async def handle_coinflip_callback(update, context):
        await update.callback_query.edit_message_text("🚧 Coin Flip game temporarily unavailable")
    async def handle_basketball_callback(update, context):
        await update.callback_query.edit_message_text("🚧 Basketball game temporarily unavailable")

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
WITHDRAWAL_FEE_PERCENT = float(os.environ.get("WITHDRAWAL_FEE_PERCENT", "0.01"))
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
                ('min_bet_amount', '0.50', 'number', 'Minimum bet amount in USD'),
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
            
            # Migration will be called separately after initial deployment
            # await migrate_database()
            
            logger.info("✅ Enhanced database initialized successfully with comprehensive schema")
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

async def migrate_database():
    """Migrate database schema to latest version"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Check if withdrawals table exists and needs updating
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='withdrawals'")
            table_exists = await cursor.fetchone()
            
            if table_exists:
                # Check each column individually to avoid duplicates
                columns_to_add = [
                    ('amount_usd', 'REAL DEFAULT 0.0'),
                    ('fee_usd', 'REAL DEFAULT 0.0'),
                    ('net_amount_usd', 'REAL DEFAULT 0.0'),
                    ('rate_usd', 'REAL DEFAULT 0.0'),
                    ('processed_at', 'TEXT DEFAULT NULL'),
                    ('confirmed_at', 'TEXT DEFAULT NULL'),
                    ('admin_notes', "TEXT DEFAULT ''"),
                    ('processed_by', 'INTEGER DEFAULT NULL'),
                    ('priority', 'INTEGER DEFAULT 0'),
                    ('confirmation_blocks', 'INTEGER DEFAULT 0'),
                    ('required_confirmations', 'INTEGER DEFAULT 6')
                ]
                
                for col_name, col_def in columns_to_add:
                    try:
                        await db.execute(f"SELECT {col_name} FROM withdrawals LIMIT 1")
                    except sqlite3.OperationalError:
                        logger.info(f"Adding column {col_name} to withdrawals table...")
                        await db.execute(f"ALTER TABLE withdrawals ADD COLUMN {col_name} {col_def}")

            # Check if transactions table exists and needs updating
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
            table_exists = await cursor.fetchone()
            
            if table_exists:
                # Check each column individually to avoid duplicates
                columns_to_add = [
                    ('crypto_asset', 'TEXT DEFAULT NULL'),
                    ('crypto_amount', 'REAL DEFAULT NULL'),
                    ('exchange_rate', 'REAL DEFAULT NULL'),
                    ('fee_amount', 'REAL DEFAULT 0.0'),
                    ('net_amount', 'REAL DEFAULT NULL'),
                    ('balance_before', 'REAL DEFAULT 0.0'),
                    ('balance_after', 'REAL DEFAULT 0.0'),
                    ('reference_id', 'TEXT DEFAULT NULL'),
                    ('game_session_id', 'INTEGER DEFAULT NULL'),
                    ('payment_method', 'TEXT DEFAULT NULL'),
                    ('payment_address', 'TEXT DEFAULT NULL'),
                    ('confirmation_blocks', 'INTEGER DEFAULT NULL'),
                    ('metadata', 'TEXT DEFAULT NULL')
                ]
                
                for col_name, col_def in columns_to_add:
                    try:
                        await db.execute(f"SELECT {col_name} FROM transactions LIMIT 1")
                    except sqlite3.OperationalError:
                        logger.info(f"Adding column {col_name} to transactions table...")
                        await db.execute(f"ALTER TABLE transactions ADD COLUMN {col_name} {col_def}")
                await db.execute("ALTER TABLE transactions ADD COLUMN updated_at TEXT DEFAULT ''")
                await db.execute("ALTER TABLE transactions ADD COLUMN confirmed_at TEXT DEFAULT NULL")

            await db.commit()
            logger.info("✅ Database migration completed successfully")
            
    except Exception as e:
        logger.error(f"Error during database migration: {e}")
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
        
        # Process referral commission if player lost
        if win_amount < bet_amount:
            loss_amount = bet_amount - win_amount
            await process_referral_commission(user_id, loss_amount)
            
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
        # Deduct balance from user
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
REFERRAL_COMMISSION_PERCENT = float(os.environ.get("REFERRAL_COMMISSION_PERCENT", "0.20"))  # 20% commission on referee losses
REFERRAL_BONUS_REFEREE = float(os.environ.get("REFERRAL_BONUS_REFEREE", "5.0"))    # Welcome bonus for new user
MAX_REFERRALS_PER_USER = int(os.environ.get("MAX_REFERRALS_PER_USER", "1000"))       # Max referrals per user

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
            
            # Give welcome bonus to referee
            await update_balance(referee_id, REFERRAL_BONUS_REFEREE)
            
            # Update referrer stats
            await db.execute("""
                UPDATE users 
                SET referral_count = referral_count + 1
                WHERE user_id = ?
            """, (referrer_id,))
            
            await db.commit()
            logger.info(f"Referral processed: {referee_id} referred by {referrer_id} using code {referral_code}")
            return True
    except Exception as e:
        logger.error(f"Error processing referral: {e}")
        return False

async def process_referral_commission(referee_id: int, loss_amount: float) -> bool:
    """Give referrer 20% commission on referee's loss."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Check if user was referred
            cursor = await db.execute("SELECT referred_by FROM users WHERE user_id = ?", (referee_id,))
            row = await cursor.fetchone()
            if not row or not row[0]:
                return False  # Not referred by anyone
            
            referral_code = row[0]
            
            # Find referrer
            cursor = await db.execute("SELECT user_id FROM users WHERE referral_code = ?", (referral_code,))
            row = await cursor.fetchone()
            if not row:
                return False
            
            referrer_id = row[0]
            
            # Calculate commission (20% of loss)
            commission = loss_amount * REFERRAL_COMMISSION_PERCENT
            
            if commission <= 0:
                return False
            
            # Give commission to referrer
            await update_balance(referrer_id, commission)
            
            # Update referrer's total earnings
            await db.execute("""
                UPDATE users 
                SET referral_earnings = referral_earnings + ?
                WHERE user_id = ?
            """, (commission, referrer_id))
            
            # Update referral record
            await db.execute("""
                UPDATE referrals 
                SET bonus_paid = bonus_paid + ?,
                    total_referee_wagered = total_referee_wagered + ?
                WHERE referee_id = ?
            """, (commission, loss_amount, referee_id))
            
            await db.commit()
            logger.info(f"Referral commission: ${commission:.2f} to user {referrer_id} from referee {referee_id}'s loss of ${loss_amount:.2f}")
            return True
            
    except Exception as e:
        logger.error(f"Error processing referral commission: {e}")
        return False

def get_referral_link(bot_username: str, referral_code: str) -> str:
    """Generate referral deep link."""
    return f"https://t.me/{bot_username}?start={referral_code}"

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
    """Handle text input for deposit/withdrawal/game custom bet states."""
    # Check for deposit/withdrawal states
    if 'awaiting_deposit_amount' in context.user_data:
        await handle_deposit_amount_input(update, context)
    elif 'awaiting_withdraw_amount' in context.user_data:
        await handle_withdraw_amount_input(update, context)
    elif 'awaiting_withdraw_address' in context.user_data:
        await handle_withdraw_address_input(update, context)
    # Check for game custom bet states
    elif 'awaiting_coinflip_custom_bet' in context.user_data:
        await handle_coinflip_custom_bet(update, context)
    elif 'awaiting_dice_custom_bet' in context.user_data:
        await handle_dice_custom_bet(update, context)
    elif 'awaiting_prediction_custom_bet' in context.user_data:
        await handle_prediction_custom_bet(update, context)
    elif 'awaiting_basketball_custom_bet' in context.user_data:
        await handle_basketball_custom_bet(update, context)
    elif 'awaiting_blackjack_bet' in context.user_data:
        await handle_blackjack_custom_bet(update, context)
    elif 'awaiting_roulette_bet' in context.user_data or 'awaiting_roulette_number_bet' in context.user_data:
        await handle_roulette_custom_bet(update, context)
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
<b>DEPOSIT FUNDS</b>

<b>Current Balance:</b> {balance_str}

<b>Payment Method:</b>
We accept Litecoin (LTC) deposits for fast transactions.

<b>Details:</b>
• Minimum: $1.00 USD
• Processing: Usually within minutes
• Low fees and enhanced privacy
"""
    
    keyboard = [
        [InlineKeyboardButton("Deposit Litecoin (LTC)", callback_data="deposit_LTC")],
        [InlineKeyboardButton("Back to Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def deposit_crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle specific crypto deposit selection."""
    query = update.callback_query
    await query.answer()
    
    # Extract crypto type from callback data
    crypto_type = query.data.split("_")[1]  # deposit_LTC -> LTC
    user_id = query.from_user.id
    
    # Clear previous states and set waiting for deposit amount
    context.user_data.clear()
    context.user_data['awaiting_deposit_amount'] = crypto_type
    
    # Get current rate
    rate = await get_crypto_usd_rate(crypto_type)
    rate_text = f"${rate:.4f}" if rate > 0 else "Rate unavailable"
    
    text = f"""
<b>DEPOSIT {crypto_type}</b>

<b>Current Rate:</b> 1 {crypto_type} = {rate_text} USD

<b>Enter Deposit Amount</b>
Please type the amount you want to deposit in USD.

<b>Limits:</b>
• Minimum: $1.00 USD
• Maximum: $10,000.00 USD per transaction

Simply type your amount in USD (e.g., type "50" for $50.00)

<b>Waiting for your input...</b>
"""
    
    keyboard = [[InlineKeyboardButton("Cancel", callback_data="main_panel")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    keyboard = [
        [InlineKeyboardButton("Back to Deposit", callback_data="deposit")]
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
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number (e.g., 10 or 25.50)")

async def process_deposit_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, crypto_type: str, amount_usd: float) -> None:
    """Process deposit payment and create CryptoBot invoice"""
    user_id = update.effective_user.id
    
    try:
        # In demo mode, just add the balance
        if DEMO_MODE:
            success = await update_balance(user_id, amount_usd)
            if success:
                keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]]
                await update.message.reply_text(
                    f"✅ Demo deposit successful! Added ${amount_usd:.2f} to your balance.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text("❌ Error processing deposit. Please try again.")
            return
        
        # Get crypto rate and calculate amount
        rate = await get_crypto_usd_rate(crypto_type)
        if rate <= 0:
            await update.message.reply_text("❌ Unable to fetch crypto rate. Please try again later.")
            return
            
        crypto_amount = amount_usd / rate
        
        # Create CryptoBot invoice
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

💳 <b>Pay with CryptoBot:</b>
Click the button below to open the secure payment interface.

⏰ <b>Expires in 1 hour</b>
🔔 <i>You'll be notified instantly when payment is confirmed!</i>
"""
        
        keyboard = [
            [InlineKeyboardButton("💳 Pay with CryptoBot", url=payment_url)],
            [InlineKeyboardButton("🔄 Check Payment Status", callback_data=f"check_payment_{invoice['invoice_id']}")],
            [InlineKeyboardButton("🔙 Back to Deposit", callback_data="deposit")]
        ]
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error processing deposit payment: {e}")
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]]
        await update.message.reply_text(
            "❌ Error processing deposit. Please try again later.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

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
<b>WITHDRAW FUNDS</b>

<b>Current Balance:</b> {await format_usd(balance)}
<b>Available to Withdraw:</b> {await format_usd(max_withdrawal)}

<b>Limits:</b>
• Minimum: {await format_usd(MIN_WITHDRAWAL_USD)}
• Maximum: {await format_usd(MAX_WITHDRAWAL_USD)} per transaction
• Daily Limit: {await format_usd(MAX_WITHDRAWAL_USD_DAILY)}
• Fee: {WITHDRAWAL_FEE_PERCENT * 100:.1f}% (min ${MIN_WITHDRAWAL_FEE:.2f})

<b>Supported:</b> Litecoin (LTC) withdrawals
<b>Processing Time:</b> Usually within 24 hours
"""
    keyboard = [
        [InlineKeyboardButton("Withdraw Litecoin (LTC)", callback_data="withdraw_LTC")],
        [InlineKeyboardButton("Back to Menu", callback_data="main_panel")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def withdraw_crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found. Please restart with /start")
        return
    
    balance_str = await format_usd(user['balance'])
    max_withdrawal = min(user['balance'], MAX_WITHDRAWAL_USD)
    
    text = f"""
<b>WITHDRAW LITECOIN (LTC)</b>

<b>Current Balance:</b> {balance_str}
<b>Available to Withdraw:</b> {await format_usd(max_withdrawal)}

Please enter the amount you wish to withdraw in USD (e.g., "50" for $50.00).
"""
    keyboard = [[InlineKeyboardButton("Back to Withdraw", callback_data="withdraw")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    context.user_data['awaiting_withdraw_amount'] = 'LTC'

async def handle_withdraw_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal amount input"""
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
        
        # Check minimum
        if amount_usd < MIN_WITHDRAWAL_USD:
            await update.message.reply_text(f"❌ Minimum withdrawal is ${MIN_WITHDRAWAL_USD:.2f} USD.")
            return
            
        # Check balance
        user_balance = user.get('balance', 0.0)
        if amount_usd > user_balance:
            balance_str = await format_usd(user_balance)
            await update.message.reply_text(
                f"❌ <b>Insufficient Balance</b>\n\n"
                f"Your balance: {balance_str}\n"
                f"Withdrawal amount: ${amount_usd:.2f} USD\n\n"
                f"You need ${amount_usd - user_balance:.2f} more to complete this withdrawal.",
                parse_mode=ParseMode.HTML
            )
            return
            
        # Check limits
        limits_check = await check_withdrawal_limits(user_id, amount_usd)
        if not limits_check['allowed']:
            await update.message.reply_text(f"❌ {limits_check['reason']}")
            return
            
        # Calculate fee
        fee = calculate_withdrawal_fee(amount_usd)
        net_amount = amount_usd - fee
        
        # Store withdrawal details and ask for address
        context.user_data['withdraw_details'] = {
            'crypto_type': crypto_type,
            'amount_usd': amount_usd,
            'fee': fee,
            'net_amount': net_amount
        }
        del context.user_data['awaiting_withdraw_amount']
        context.user_data['awaiting_withdraw_address'] = crypto_type
        
        fee_str = await format_usd(fee)
        net_str = await format_usd(net_amount)
        
        await update.message.reply_text(
            f"<b>Withdrawal Details</b>\n\n"
            f"Amount: ${amount_usd:.2f} USD\n"
            f"Fee: {fee_str}\n"
            f"You'll receive: {net_str}\n\n"
            f"Please enter your {crypto_type} address:",
            parse_mode=ParseMode.HTML
        )
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number (e.g., 10 or 25.50)")

async def handle_withdraw_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal address input"""
    if 'awaiting_withdraw_address' not in context.user_data:
        return
        
    address = update.message.text.strip()
    withdraw_details = context.user_data.get('withdraw_details', {})
    crypto_type = withdraw_details.get('crypto_type', 'LTC')
    
    # Validate address format
    if not validate_crypto_address(address, crypto_type):
        await update.message.reply_text(f"❌ Invalid {crypto_type} address format. Please check and try again.")
        return
    
    # Clear states
    del context.user_data['awaiting_withdraw_address']
    del context.user_data['withdraw_details']
    
    # Process withdrawal
    user_id = update.message.from_user.id
    amount_usd = withdraw_details['amount_usd']
    fee = withdraw_details['fee']
    net_amount = withdraw_details['net_amount']
    
    if DEMO_MODE:
        # Demo mode - simulate withdrawal
        success = await deduct_balance(user_id, amount_usd)
        if success:
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]]
            await update.message.reply_text(
               
                f"✅ Demo withdrawal successful!\n\n"
                f"Withdrawn: ${amount_usd:.2f} USD\n"
                f"Fee: ${fee:.2f} USD\n"
                f"Address: {address[:10]}...{address[-10:]}\n\n"
                f"<i>In real mode, this would process to your wallet</i>",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text("❌ Error processing withdrawal.")
    else:
        # Real mode - process actual withdrawal
        rate = await get_crypto_usd_rate(crypto_type)
        if rate <= 0:
            await update.message.reply_text("❌ Unable to fetch crypto rate. Please try again later.")
            return
            
        crypto_amount = amount_usd / rate
        net_crypto_amount = crypto_amount - (fee / rate)
        
        # Log withdrawal
        withdrawal_id = await log_withdrawal(user_id, crypto_type, crypto_amount, address, fee / rate, net_crypto_amount)
        
        if withdrawal_id:
            # Deduct balance
            success = await deduct_balance(user_id, amount_usd)
            if success:
                await update.message.reply_text(
                    f"✅ Withdrawal request submitted!\n\n"
                    f"Amount: ${amount_usd:.2f} USD\n"
                    f"Crypto: {crypto_amount:.8f} {crypto_type}\n"
                    f"Fee: {fee / rate:.8f} {crypto_type}\n"
                    f"Net: {net_crypto_amount:.8f} {crypto_type}\n"
                    f"Address: {address}\n\n"
                    f"Your withdrawal will be processed within 24 hours."
                )
                # Update house balance
                await update_house_balance_on_withdrawal(amount_usd)
            else:
                await update.message.reply_text("❌ Insufficient balance for withdrawal.")
                await update_withdrawal_status(withdrawal_id, "failed", "", "Insufficient balance")
        else:
            await update.message.reply_text("❌ Error submitting withdrawal request. Please try again later.")

# --- CryptoBot Webhook and Payment Status ---

async def check_payment_status(invoice_id: str) -> dict:
    """Check payment status of a CryptoBot invoice"""
    if not CRYPTOBOT_API_TOKEN:
        return {"ok": False, "error": "API token not configured"}
    
    try:
        headers = {
            'Crypto-Pay-API-Token': CRYPTOBOT_API_TOKEN,
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.get(f'https://pay.crypt.bot/api/getInvoices?invoice_ids={invoice_id}', 
                                 headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('ok') and result.get('result'):
                        invoices = result['result']['items']
                        if invoices:
                            return {"ok": True, "result": invoices[0]}
                    return {"ok": False, "error": "Invoice not found"}
                else:
                    error_text = await response.text()
                    logger.error(f"CryptoBot API error {response.status}: {error_text}")
                    return {"ok": False, "error": f"API error {response.status}"}
                    
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        return {"ok": False, "error": str(e)}

async def process_successful_deposit(user_id: int, amount_usd: float, crypto_amount: float, asset: str, invoice_id: str) -> bool:
    """Process a successful deposit and update user balance"""
    try:
        # Update user balance
        success = await update_balance(user_id, amount_usd)
        
        if success:
            # Log the deposit to transactions table
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("""
                    INSERT INTO transactions 
                    (user_id, type, subtype, amount, currency, crypto_asset, crypto_amount, 
                     reference_id, status, description, created_at)
                    VALUES (?, 'deposit', 'crypto_deposit', ?, 'USD', ?, ?, ?, 'completed', 
                            'CryptoBot deposit', ?)
                """, (user_id, amount_usd, asset, crypto_amount, invoice_id, datetime.now().isoformat()))
                
                # Update total deposited
                await db.execute("""
                    UPDATE users SET total_deposited = COALESCE(total_deposited, 0) + ? WHERE user_id = ?
                """, (amount_usd, user_id))
                
                await db.commit()
            
            # Update house balance
            await update_house_balance_on_deposit(amount_usd)
            
            logger.info(f"Deposit processed successfully: User {user_id}, Amount ${amount_usd}, Invoice {invoice_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error processing successful deposit: {e}")
        return False

async def handle_cryptobot_webhook(request_data: dict, signature: str) -> bool:
    """Handle CryptoBot webhook for payment notifications"""
    try:
        if not CRYPTOBOT_WEBHOOK_SECRET:
            logger.error("Webhook secret not configured")
            return False
        
        # Verify webhook signature
        computed_signature = hmac.new(
            CRYPTOBOT_WEBHOOK_SECRET.encode(),
            str(request_data).encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, computed_signature):
            logger.error("Invalid webhook signature")
            return False
        
        # Process the webhook
        update_type = request_data.get('update_type')
        payload = request_data.get('payload', {})
        
        if update_type == 'invoice_paid':
            invoice = payload
            invoice_id = invoice.get('invoice_id')
            user_id = int(invoice.get('hidden_message', 0))
            amount = float(invoice.get('amount', 0))
            asset = invoice.get('asset')
            status = invoice.get('status')
            
            if status == 'paid' and user_id > 0:
                # Calculate USD amount
                rate = await get_crypto_usd_rate(asset)
                amount_usd = amount * rate if rate > 0 else 0
                
                if amount_usd > 0:
                    success = await process_successful_deposit(user_id, amount_usd, amount, asset, invoice_id)
                    if success:
                        # Notify user (you could add bot notification here)
                        logger.info(f"User {user_id} notified of successful deposit: ${amount_usd:.2f}")
                    return success
        
        return True
        
    except Exception as e:
        logger.error(f"Error handling CryptoBot webhook: {e}")
        return False

async def check_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment status check button"""
    query = update.callback_query
    await query.answer()
    
    # Extract invoice ID from callback data
    invoice_id = query.data.split("_")[-1]  # check_payment_INVOICE_ID
    
    try:
        status_data = await check_payment_status(invoice_id)
        
        if not status_data.get('ok'):
            await query.edit_message_text(
                f"❌ Error checking payment status: {status_data.get('error', 'Unknown error')}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Deposit", callback_data="deposit")]])
            )
            return
        
        invoice = status_data['result']
        status = invoice.get('status')
        amount = float(invoice.get('amount', 0))
        asset = invoice.get('asset')
        
        if status == 'paid':
            # Process the payment
            user_id = int(invoice.get('hidden_message', 0))
            rate = await get_crypto_usd_rate(asset)
            amount_usd = amount * rate if rate > 0 else 0
            
            if amount_usd > 0:
                success = await process_successful_deposit(user_id, amount_usd, amount, asset, invoice_id)
                if success:
                    text = f"""
✅ <b>PAYMENT CONFIRMED!</b> ✅

💰 <b>Deposit Successful:</b> ${amount_usd:.2f} USD
🪙 <b>Received:</b> {amount:.8f} {asset}
📄 <b>Invoice:</b> <code>{invoice_id}</code>

Your balance has been updated!
"""
                    keyboard = [[InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre")]]
                else:
                    text = "❌ Error processing payment. Please contact support."
                    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]]
            elif status == 'active':
                text = f"""
⏳ <b>PAYMENT PENDING</b> ⏳

🪙 <b>Waiting for:</b> {amount:.8f} {asset}
📄 <b>Invoice:</b> <code>{invoice_id}</code>

Payment is still pending. Please complete the transaction in your wallet.
"""
                keyboard = [
                    [InlineKeyboardButton("🔄 Check Again", callback_data=f"check_payment_{invoice_id}")],
                    [InlineKeyboardButton("🔙 Back to Deposit", callback_data="deposit")]
                ]
            else:
                text = f"""
❌ <b>PAYMENT FAILED OR EXPIRED</b> ❌

📄 <b>Invoice:</b> <code>{invoice_id}</code>
📊 <b>Status:</b> {status}

Please create a new deposit request.
"""
                keyboard = [[InlineKeyboardButton("💳 New Deposit", callback_data="deposit")]]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        await query.edit_message_text(
            "❌ Error checking payment status. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Deposit", callback_data="deposit")]])
        )

# Register handlers in main bot setup (ensure these are present in Application setup)
# --- Keep-Alive Endpoint and Port Binding for Deployment ---

import os
from flask import Flask

app = Flask(__name__)

@app.route('/keepalive')
def keep_alive():
    return "OK", 200

@app.route('/cryptobot_webhook', methods=['POST'])
def cryptobot_webhook():
    """Handle CryptoBot webhook notifications"""
    try:
        signature = request.headers.get('Crypto-Pay-API-Signature', '')
        request_data = request.get_json()
        
        if not request_data:
            return "Invalid request", 400
        
        # Handle webhook in async context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(handle_cryptobot_webhook(request_data, signature))
        loop.close()
        
        if success:
            return "OK", 200
        else:
            return "Error processing webhook", 500
            
    except Exception as e:
        logger.error(f"Error in CryptoBot webhook: {e}")
        return "Internal error", 500

# --- Flask and Telegram Bot Runner ---

import threading
import asyncio

def run_flask():
    port = int(os.environ.get("PORT", 8001))
    app.run(host="0.0.0.0", port=port)

async def run_telegram_bot_async():
    await init_db()  # Ensure DB is ready

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Register specific deposit/withdrawal handlers first (higher priority)
    application.add_handler(CommandHandler("deposit", deposit_callback))
    application.add_handler(CommandHandler("withdraw", withdraw_start))
    application.add_handler(CallbackQueryHandler(deposit_callback, pattern=r"^deposit$"))
    application.add_handler(CallbackQueryHandler(deposit_crypto_callback, pattern=r"^deposit_LTC$"))
    application.add_handler(CallbackQueryHandler(check_payment_callback, pattern=r"^check_payment_"))
    application.add_handler(CallbackQueryHandler(withdraw_start, pattern=r"^withdraw$"))
    application.add_handler(CallbackQueryHandler(withdraw_crypto_callback, pattern=r"^withdraw_LTC$"))

    # Enhanced start handler with user panel
    async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display user panel with balance, stats, and navigation"""
        await init_db()  # Ensure database is initialized
        
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Get or create user
        user = await get_user(user_id)
        if not user:
            user = await create_user(user_id, username)
            if not user:
                await update.message.reply_text("❌ Error creating user account. Please try again.")
                return
        
        # Get user stats
        balance = user.get('balance', 0)
        games_played = user.get('games_played', 0)
        total_wagered = user.get('total_wagered', 0.0)
        total_won = user.get('total_won', 0.0)
        win_streak = user.get('win_streak', 0)
        referral_count = user.get('referral_count', 0)
        
        # Get or create referral code
        referral_code = await get_or_create_referral_code(user_id)
        
        # Format amounts
        balance_str = await format_usd(balance)
        wagered_str = await format_usd(total_wagered)
        won_str = await format_usd(total_won)
        
        # Calculate profit/loss
        net_result = total_won - total_wagered
        net_emoji = "📈" if net_result >= 0 else "📉"
        net_str = await format_usd(abs(net_result))
        
        # Build user panel message
        welcome_text = f"""
<b>AXIS CASINO</b>

Welcome, {username}!

<b>Balance:</b> {balance_str}
<b>Referral Code:</b> <code>{referral_code}</code>

<b>Choose an action:</b>
"""
        
        # Create navigation keyboard
        keyboard = [
            [
                InlineKeyboardButton("Deposit", callback_data="deposit"),
                InlineKeyboardButton("Withdraw", callback_data="withdraw")
            ],
            [
                InlineKeyboardButton("Play Games", callback_data="mini_app_centre"),
                InlineKeyboardButton("Referrals", callback_data="referral_menu"),
                InlineKeyboardButton("Bonuses", callback_data="bonus_menu")
            ],
            [
                InlineKeyboardButton("Statistics", callback_data="user_stats"),
                InlineKeyboardButton("Help", callback_data="help_menu")
            ]
        ]
        
        # Add admin panel for admins
        if is_admin(user_id) or is_owner(user_id):
            keyboard.append([InlineKeyboardButton("Admin Panel", callback_data="admin_panel")])
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

    application.add_handler(CommandHandler("start", start_handler))
    
    # Referral command handler
    async def referral_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /referral command"""
        user_id = update.effective_user.id
        referral_code = await get_or_create_referral_code(user_id)
        stats = await get_referral_stats(user_id)
        
        # Get bot username
        try:
            bot = await context.bot.get_me()
            bot_username = bot.username
        except:
            bot_username = "AxisCasinoBot"
        
        # Generate referral link
        referral_link = get_referral_link(bot_username, referral_code)
        
        earnings_str = await format_usd(stats['earnings'])
        
        text = f"""
<b>REFERRAL PROGRAM</b>

<b>Earn 20% Commission!</b>

Share your unique referral link and earn <b>20% of what your referrals lose</b> in games!

<b>Your Referral Link:</b>
<code>{referral_link}</code>

<b>Your Stats:</b>
Total Referrals: <b>{stats['count']}</b>
Total Earned: <b>{earnings_str}</b>

<b>How it works:</b>
1. Share your link with friends
2. They sign up using your link
3. They get a ${REFERRAL_BONUS_REFEREE:.2f} welcome bonus
4. You earn 20% commission every time they lose a game

<b>Example:</b>
If your referral loses $100, you earn $20!

Start sharing and earning today!
"""
        
        # Add recent referrals if any
        if stats['recent']:
            text += "\n\n<b>Recent Referrals:</b>\n"
            for ref in stats['recent'][:5]:
                username = ref['username'] or 'User'
                bonus = ref['bonus']
                text += f"• {username} - Earned: ${bonus:.2f}\n"
        
        keyboard = [
            [InlineKeyboardButton("Share Link", url=f"https://t.me/share/url?url={referral_link}&text=Join this amazing casino bot!")],
            [InlineKeyboardButton("Refresh Stats", callback_data="referral_menu")],
            [InlineKeyboardButton("Main Menu", callback_data="main_panel")]
        ]
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    application.add_handler(CommandHandler("referral", referral_command_handler))
    
    # Basic callback handlers for user panel navigation
    async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards (general fallback)"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        # Skip specific deposit/withdrawal callbacks - they have their own handlers
        if data.startswith('deposit_') or data.startswith('withdraw_') or data.startswith('check_payment_'):
            return
        
        if data == "main_panel":
            # Return to main panel (simulate /start)
            await start_panel_callback(update, context)
        elif data == "deposit":
            await deposit_callback(update, context)
        elif data == "withdraw":
            await withdraw_start(update, context)
        elif data == "mini_app_centre":
            await games_menu_callback(update, context)
        elif data == "games":
            # Alternative callback data for "Back to Games" - redirect to games menu
            await games_menu_callback(update, context)
        elif data == "referral_menu":
            await referral_menu_callback(update, context)
        elif data == "user_stats":
            await user_stats_callback(update, context)
        elif data == "help_menu":
            await help_menu_callback(update, context)
        elif data == "admin_panel" and (is_admin(user_id) or is_owner(user_id)):
            await admin_panel_callback(update, context)
        elif data == "bonus_menu":
            await bonus_menu_callback(update, context)
        # Game handlers
        elif data == "game_slots":
            await game_slots_callback(update, context)
        elif data == "game_blackjack":
            await game_blackjack_callback(update, context)
        elif data == "game_dice":
            await game_dice_callback(update, context)
        elif data == "game_prediction":
            await handle_prediction_callback(update, context)
        elif data == "game_basketball":
            await handle_basketball_callback(update, context)
        elif data == "game_coinflip":
            await handle_coinflip_callback(update, context)
        elif data == "game_roulette":
            await game_roulette_callback(update, context)
        # Game betting handlers
        elif data.startswith("slots_bet_"):
            await handle_slots_bet(update, context)
        elif data.startswith("blackjack_bet_"):
            await handle_blackjack_bet(update, context)
        elif data.startswith("dice_bet_"):
            await handle_dice_bet(update, context)
        elif data.startswith("dice_play_"):
            await handle_dice_play(update, context)
        elif data.startswith("prediction_"):
            await handle_prediction_callback(update, context)
        elif data.startswith("basketball_"):
            await handle_basketball_callback(update, context)
        elif data.startswith("coinflip_"):
            await handle_coinflip_callback(update, context)
        elif data.startswith("roulette_"):
            await handle_roulette_callback(update, context)
        elif data == "weekly_bonus":
            await weekly_bonus_callback(update, context)
        elif data == "claim_weekly_bonus":
            await claim_weekly_bonus_callback(update, context)
        else:
            await query.edit_message_text("❌ Unknown action. Returning to main menu.")
            await start_panel_callback(update, context)
    
    # Helper callback functions
    async def start_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the main user panel (same as /start but for callbacks)"""
        # Get user data
        user_id = update.callback_query.from_user.id
        username = update.callback_query.from_user.username or update.callback_query.from_user.first_name
        
        user = await get_user(user_id)
        if not user:
            user = await create_user(user_id, username)
        
        # Get user stats
        balance = user.get('balance', 0.0)
        games_played = user.get('games_played', 0)
        total_wagered = user.get('total_wagered', 0.0)
        total_won = user.get('total_won', 0.0)
        win_streak = user.get('win_streak', 0)
        referral_count = user.get('referral_count', 0)
        
        referral_code = await get_or_create_referral_code(user_id)
        
        balance_str = await format_usd(balance)
        wagered_str = await format_usd(total_wagered)
        won_str = await format_usd(total_won)
        
        net_result = total_won - total_wagered
        net_emoji = "📈" if net_result >= 0 else "📉"
        net_str = await format_usd(abs(net_result))
        
        welcome_text = f"""
<b>AXIS CASINO</b>

Welcome, {username}!

<b>Balance:</b> {balance_str}
<b>Referral Code:</b> <code>{referral_code}</code>

<b>Choose an action:</b>
"""
        
        keyboard = [
            [
                InlineKeyboardButton("Deposit", callback_data="deposit"),
                InlineKeyboardButton("Withdraw", callback_data="withdraw")
            ],
            [
                InlineKeyboardButton("Play Games", callback_data="mini_app_centre"),
                InlineKeyboardButton("Referrals", callback_data="referral_menu"),
                InlineKeyboardButton("Bonuses", callback_data="bonus_menu")
            ],
            [
                InlineKeyboardButton("Statistics", callback_data="user_stats"),
                InlineKeyboardButton("Help", callback_data="help_menu")
            ]
        ]
        
        # Add admin panel for admins
        if is_admin(user_id) or is_owner(user_id):
            keyboard.append([InlineKeyboardButton("Admin Panel", callback_data="admin_panel")])
        
        await update.callback_query.edit_message_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def games_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show games menu"""
        user_id = update.callback_query.from_user.id
        user = await get_user(user_id)
        
        if not user:
            await update.callback_query.edit_message_text(
                "❌ User not found. Please use /start to register.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_panel")]])
            )
            return
        
        balance = user['balance']
        balance_str = await format_usd(balance)
        
        # Always show games, but add warning if balance is insufficient
        if balance < 1.0:
            text = f"""
<b>CASINO GAMES</b>

<b>Your Balance:</b> {balance_str}

<b>INSUFFICIENT BALANCE TO PLAY</b>
You need at least $1.00 to play games.

<b>Get funds:</b> Deposit • Weekly Bonus • Referrals

<b>Available Games:</b>

<b>Slots</b> - Classic slot machine
<b>Blackjack</b> - Beat the dealer
<b>Dice</b> - Roll to win
<b>Coin Flip</b> - Heads or Tails
<b>Roulette</b> - European roulette
<b>Basketball</b> - Shoot hoops!
<b>Dice Predict</b> - Predict the dice
"""
        else:
            text = f"""
<b>CASINO GAMES</b>

<b>Your Balance:</b> {balance_str}

Choose your game:

<b>Slots</b> - Classic slot machine
<b>Blackjack</b> - Beat the dealer
<b>Dice 1v1</b> - Roll against the bot
<b>Coin Flip</b> - Heads or Tails
<b>Roulette</b> - European roulette
<b>Basketball 1v1</b> - Shoot hoops vs bot!
<b>Dice Predict</b> - Predict the dice (5x payout!)

Good luck!
"""
        
        # Always show all game buttons
        keyboard = [
            [
                InlineKeyboardButton("Slots", callback_data="game_slots"),
                InlineKeyboardButton("Blackjack", callback_data="game_blackjack")
            ],
            [
                InlineKeyboardButton("Dice", callback_data="game_dice"),
                InlineKeyboardButton("Coin Flip", callback_data="game_coinflip")
            ],
            [
                InlineKeyboardButton("Roulette", callback_data="game_roulette"),
                InlineKeyboardButton("Basketball", callback_data="game_basketball")
            ],
            [
                InlineKeyboardButton("Prediction", callback_data="game_prediction")
            ]
        ]
        
        # Add funding options if balance is low
        if balance < 1.0:
            keyboard.append([
                InlineKeyboardButton("� Deposit", callback_data="deposit"),
                InlineKeyboardButton("🎁 Bonus", callback_data="weekly_bonus")
            ])
        
        keyboard.append([InlineKeyboardButton("Back to Menu", callback_data="main_panel")])
        
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show withdraw menu"""
        text = """
🏦 <b>WITHDRAW FUNDS</b> 🏦

Withdraw your winnings securely:

• <b>Cryptocurrency:</b> Fast and secure
• <b>Minimum:</b> $1.00 USD equivalent
• <b>Fee:</b> 2% (minimum $1.00)
• <b>Processing:</b> Usually within 1 hour

<i>Currently supporting Litecoin (LTC) withdrawals</i>
"""
        keyboard = [
            [InlineKeyboardButton("🪙 Withdraw Litecoin (LTC)", callback_data="withdraw_LTC")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]
        ]
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def referral_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show referral menu"""
        user_id = update.callback_query.from_user.id
        referral_code = await get_or_create_referral_code(user_id)
        stats = await get_referral_stats(user_id)
        
        # Get bot username
        try:
            bot = await context.bot.get_me()
            bot_username = bot.username
        except:
            bot_username = "AxisCasinoBot"
        
        # Generate referral link
        referral_link = get_referral_link(bot_username, referral_code)
        
        earnings_str = await format_usd(stats['earnings'])
        
        text = f"""
👥 <b>REFERRAL PROGRAM</b> 👥

� <b>Earn 20% Commission!</b>

Share your unique referral link and earn <b>20% of what your referrals lose</b> in games!

�🔗 <b>Your Referral Link:</b>
<code>{referral_link}</code>

📊 <b>Your Stats:</b>
� Total Referrals: <b>{stats['count']}</b>
� Total Earned: <b>{earnings_str}</b>

<b>How it works:</b>
1. Share your link with friends
2. They sign up using your link
3. They get a ${REFERRAL_BONUS_REFEREE:.2f} welcome bonus
4. You earn 20% commission every time they lose a game

💡 <b>Example:</b>
If your referral loses $100, you earn $20!

<i>Start sharing and earning today!</i>
"""
        
        # Add recent referrals if any
        if stats['recent']:
            text += "\n\n📋 <b>Recent Referrals:</b>\n"
            for ref in stats['recent'][:5]:
                username = ref['username'] or 'User'
                bonus = ref['bonus']
                text += f"• {username} - Earned: ${bonus:.2f}\n"
        
        keyboard = [
            [InlineKeyboardButton("� Share Link", url=f"https://t.me/share/url?url={referral_link}&text=Join this amazing casino bot!")],
            [InlineKeyboardButton("🔄 Refresh Stats", callback_data="referral_menu")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]
        ]
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def user_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed user statistics"""
        user_id = update.callback_query.from_user.id
        user = await get_user(user_id)
        
        if not user:
            await update.callback_query.edit_message_text("❌ User not found.")
            return
        
        # Format all stats
        balance_str = await format_usd(user.get('balance', 0.0))
        wagered_str = await format_usd(user.get('total_wagered', 0.0))
        won_str = await format_usd(user.get('total_won', 0.0))
        deposited_str = await format_usd(user.get('total_deposited', 0.0))
        withdrawn_str = await format_usd(user.get('total_withdrawn', 0.0))
        biggest_win_str = await format_usd(user.get('biggest_win', 0.0))
        
        text = f"""
<b>YOUR STATISTICS</b>

<b>Current Balance:</b> {balance_str}
<b>Games Played:</b> {user.get('games_played', 0):,}
<b>Total Wagered:</b> {wagered_str}
<b>Total Won:</b> {won_str}
<b>Total Deposited:</b> {deposited_str}
<b>Total Withdrawn:</b> {withdrawn_str}

<b>Performance:</b>
<b>Current Win Streak:</b> {user.get('win_streak', 0)}
<b>Max Win Streak:</b> {user.get('max_win_streak', 0)}
<b>Biggest Win:</b> {biggest_win_str}
<b>VIP Level:</b> {user.get('vip_level', 0)}

<b>Member Since:</b> {user.get('created_at', '')[:10] if user.get('created_at') else 'Unknown'}
"""
        keyboard = [[InlineKeyboardButton("Back to Menu", callback_data="main_panel")]]
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def help_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help menu"""
        text = """
<b>HELP & SUPPORT</b>

<b>How to Play:</b>
• Use /start to access your panel
• Deposit funds to start playing
• Choose games and place bets
• Withdraw your winnings

<b>Deposits & Withdrawals:</b>
• Supported: Litecoin (LTC)
• Fast processing times
• Secure transactions

<b>Features:</b>
• Multiple casino games
• Referral system
• VIP rewards
• 24/7 support

<b>Need Help?</b>
Contact our support team for assistance.
"""
        keyboard = [
            [InlineKeyboardButton("Game Rules", callback_data="game_rules")],
            [InlineKeyboardButton("Support", url="https://t.me/casino_support")],
            [InlineKeyboardButton("Back to Menu", callback_data="main_panel")]
        ]
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin panel (admin only)"""
        user_id = update.callback_query.from_user.id
        if not (is_admin(user_id) or is_owner(user_id)):
            await update.callback_query.edit_message_text("❌ Access denied.")
            return
        
        house_balance_info = await get_house_balance_display()
        
        text = f"""
<b>ADMIN PANEL</b>

{house_balance_info}

<b>Quick Actions:</b>
"""
        keyboard = [
            [
                InlineKeyboardButton("User Management", callback_data="admin_users"),
                InlineKeyboardButton("Transactions", callback_data="admin_transactions")
            ],
            [
                InlineKeyboardButton("Analytics", callback_data="admin_analytics"),
                InlineKeyboardButton("Settings", callback_data="admin_settings")
            ],
            [
                InlineKeyboardButton("Back to Menu", callback_data="main_panel")
            ]
        ]
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def bonus_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bonuses menu"""
        text = """
<b>BONUSES & REWARDS</b>

Claim your available bonuses and see current promotions!

• <b>Weekly Bonus</b>: Claim every 7 days
• <b>Referral Bonus</b>: Earn for inviting friends
• <b>Special Events</b>: Watch for announcements

More bonus types coming soon!
"""
        keyboard = [
            [InlineKeyboardButton("Claim Weekly Bonus", callback_data="claim_weekly_bonus")],
            [InlineKeyboardButton("Back to Menu", callback_data="main_panel")]
        ]
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def weekly_bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show weekly bonus information"""
        user_id = update.callback_query.from_user.id
        can_claim, seconds_remaining = await can_claim_weekly_bonus(user_id)
        
        if can_claim:
            text = f"""
🎁 <b>WEEKLY BONUS</b> 🎁

✅ <b>Available!</b>

💰 <b>Bonus Amount:</b> ${WEEKLY_BONUS_AMOUNT}
🎯 <b>Frequency:</b> Every {WEEKLY_BONUS_INTERVAL} days

<i>Click the button below to claim your bonus!</i>
"""
            keyboard = [
                [InlineKeyboardButton("🎉 Claim Bonus", callback_data="claim_weekly_bonus")],
                [InlineKeyboardButton("🔙 Back", callback_data="bonus_menu")]
            ]
        else:
            # Calculate time remaining
            hours_remaining = seconds_remaining // 3600
            minutes_remaining = (seconds_remaining % 3600) // 60
            
            text = f"""
🎁 <b>WEEKLY BONUS</b> 🎁

⏰ <b>Not Available Yet</b>

💰 <b>Bonus Amount:</b> ${WEEKLY_BONUS_AMOUNT}
🎯 <b>Frequency:</b> Every {WEEKLY_BONUS_INTERVAL} days

⏳ <b>Time Remaining:</b> {hours_remaining}h {minutes_remaining}m

<i>Come back later to claim your next bonus!</i>
"""
            keyboard = [
                [InlineKeyboardButton("🔙 Back", callback_data="bonus_menu")]
            ]
        
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def claim_weekly_bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle weekly bonus claim"""
        user_id = update.callback_query.from_user.id
        can_claim, seconds_remaining = await can_claim_weekly_bonus(user_id)
        
        if not can_claim:
            hours_remaining = seconds_remaining // 3600
            minutes_remaining = (seconds_remaining % 3600) // 60
            
            text = f"""
❌ <b>Bonus Not Available</b>

You can claim your next weekly bonus in {hours_remaining}h {minutes_remaining}m.
"""
            keyboard = [
                [InlineKeyboardButton("🔙 Back", callback_data="bonus_menu")]
            ]
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
            return
        
        # Claim the bonus
        success = await claim_weekly_bonus(user_id)
        
        if success:
            user = await get_user(user_id)
            balance_str = await format_usd(user['balance'])
            
            text = f"""
🎉 <b>BONUS CLAIMED!</b> 🎉

💰 <b>Bonus Amount:</b> ${WEEKLY_BONUS_AMOUNT}
💳 <b>New Balance:</b> {balance_str}

<i>Congratulations! Your bonus has been added to your account.</i>
"""
        else:
            text = f"""
❌ <b>Error Claiming Bonus</b>

Something went wrong while processing your bonus. Please try again later or contact support.
"""
        
        keyboard = [
            [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre")],
            [InlineKeyboardButton("🔙 Back", callback_data="bonus_menu")]
        ]
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    # Add callback handler for claim_weekly_bonus
    application.add_handler(CallbackQueryHandler(claim_weekly_bonus_callback, pattern=r"^claim_weekly_bonus$"))
    
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input_main))
    # Add your other handlers here, e.g.:
    # application.add_handler(CallbackQueryHandler(callback_handler))
    # application.add_handler(MessageHandler(filters.TEXT, handle_text_input_main))

    await application.run_polling()

def run_telegram_bot():
    """Run the telegram bot with proper event loop management for deployment"""
    try:
        # Simple direct approach for deployment
        asyncio.run(run_telegram_bot_async())
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            # We're in an environment with an existing event loop
            # Create and run in a new thread
            import threading
            def run_in_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(run_telegram_bot_async())
                loop.close()
            
            thread = threading.Thread(target=run_in_thread)
            thread.daemon = True
            thread.start()
            thread.join()  # Wait for completion in deployment
        else:
            raise

if __name__ == "__main__":
    # Environment detection for proper startup
    is_deployment = bool(os.environ.get("RENDER") or os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("HEROKU"))
    
    if is_deployment:
        # In deployment, run bot directly and Flask on different port
        print("🚀 Starting in deployment mode...")
        # Start Flask in background for health checks
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        
        # Run telegram bot in main thread
        run_telegram_bot()
    else:
        # Local development
        print("🏠 Starting in development mode...")

# --- Game Callback Handlers ---

async def game_slots_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show slots game betting interface"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found. Please restart with /start")
        return
    
    balance_str = await format_usd(user['balance'])
    
    text = f"""
<b>SLOTS GAME</b>

<b>Your Balance:</b> {balance_str}

<b>How to Play:</b>
• Choose your bet amount
• Spin the reels for matching symbols
• Win up to 100x your bet!

<b>Symbol Payouts:</b>
• 🍒🍒🍒 = 10x bet
• 🍋🍋🍋 = 20x bet  
• 🍊🍊🍊 = 30x bet
• 🔔🔔🔔 = 50x bet
• 💎💎💎 = 100x bet

Choose your bet amount:
"""
    
    keyboard = [
        [
            InlineKeyboardButton("$1", callback_data="slots_bet_1"),
            InlineKeyboardButton("$5", callback_data="slots_bet_5"),
            InlineKeyboardButton("$10", callback_data="slots_bet_10")
        ],
        [
            InlineKeyboardButton("$25", callback_data="slots_bet_25"),
            InlineKeyboardButton("$50", callback_data="slots_bet_50"),
            InlineKeyboardButton("$100", callback_data="slots_bet_100")
        ],
        [InlineKeyboardButton("Back to Games", callback_data="mini_app_centre")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def game_blackjack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show blackjack game betting interface"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found. Please restart with /start")
        return
    
    balance_str = await format_usd(user['balance'])
    
    text = f"""
<b>BLACKJACK</b>

<b>Your Balance:</b> {balance_str}

<b>How to Play:</b>
• Get as close to 21 as possible
• Beat the dealer without going over
• Blackjack pays 3:2!

<b>Card Values:</b>
• Number cards = Face value
• Face cards = 10 points
• Ace = 1 or 11 points

Choose your bet amount:
"""
    
    keyboard = [
        [
            InlineKeyboardButton("$1", callback_data="blackjack_bet_1"),
            InlineKeyboardButton("$5", callback_data="blackjack_bet_5"),
            InlineKeyboardButton("$10", callback_data="blackjack_bet_10")
        ],
        [
            InlineKeyboardButton("$25", callback_data="blackjack_bet_25"),
            InlineKeyboardButton("$50", callback_data="blackjack_bet_50"),
            InlineKeyboardButton("$100", callback_data="blackjack_bet_100")
        ],
        [InlineKeyboardButton("Back to Games", callback_data="mini_app_centre")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def game_dice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show dice game betting interface"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found. Please restart with /start")
        return
    
    balance_str = await format_usd(user['balance'])
    
    text = f"""
<b>DICE GAME</b>

<b>Your Balance:</b> {balance_str}

<b>How to Play:</b>
• Two dice are rolled
• Predict if the sum will be HIGH or LOW
• HIGH (8-12) and LOW (2-7) both pay 2x

<b>Betting Options:</b>
• HIGH (8-12) = 2x payout
• LOW (2-7) = 2x payout
• Lucky 7 = 5x payout

Choose your bet amount:
"""
    
    keyboard = [
        [
            InlineKeyboardButton("$1", callback_data="dice_bet_1"),
            InlineKeyboardButton("$5", callback_data="dice_bet_5"),
            InlineKeyboardButton("$10", callback_data="dice_bet_10")
        ],
        [
            InlineKeyboardButton("$25", callback_data="dice_bet_25"),
            InlineKeyboardButton("$50", callback_data="dice_bet_50"),
            InlineKeyboardButton("$100", callback_data="dice_bet_100")
        ],
        [InlineKeyboardButton("🔙 Back to Games", callback_data="mini_app_centre")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def game_roulette_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show roulette game interface"""
    query = update.callback_query
    await query.answer()
    
    text = """
<b>ROULETTE</b>

<b>Coming Soon!</b>

This European roulette game is currently under development.

Features coming soon:
• European wheel (single zero)
• Multiple betting options
• Live spinning animation
• High payout multipliers

Stay tuned for updates!
"""
    
    keyboard = [[InlineKeyboardButton("Back to Games", callback_data="mini_app_centre")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# --- Game Logic Functions ---

def generate_slot_reels() -> List[str]:
    """Generate three random symbols for slots"""
    symbols = ['🍒', '🍋', '🍊', '🔔', '💎']
    weights = [40, 30, 20, 8, 2]  # Higher weight = more common
    
    # Create weighted symbol list
    weighted_symbols = []
    for symbol, weight in zip(symbols, weights):
        weighted_symbols.extend([symbol] * weight)
    
    return [random.choice(weighted_symbols) for _ in range(3)]

def calculate_slots_win(reels: List[str], bet_amount: float) -> Tuple[float, str]:
    """Calculate slots winnings"""
    payouts = {'🍒': 10, '🍋': 20, '🍊': 30, '🔔': 50, '💎': 100}
    
    # Check for three matching symbols
    if reels[0] == reels[1] == reels[2]:
        symbol = reels[0]
        multiplier = payouts[symbol]
        win_amount = bet_amount * multiplier
        return win_amount, f"JACKPOT! {symbol}{symbol}{symbol} - {multiplier}x multiplier!"
    
    # Check for two matching symbols (small consolation)
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        win_amount = bet_amount * 0.5
        return win_amount, "Two matching symbols - small win!"
    
    return 0.0, "No match - try again!"

def generate_blackjack_hand() -> List[str]:
    """Generate a blackjack hand"""
    cards = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    return [random.choice(cards) for _ in range(2)]

def calculate_hand_value(hand: List[str]) -> int:
    """Calculate blackjack hand value"""
    value = 0
    aces = 0
    
    for card in hand:
        if card in ['J', 'Q', 'K']:
            value += 10
        elif card == 'A':
            aces += 1
            value += 11
        else:
            value += int(card)
    
    # Adjust for aces
    while value > 21 and aces > 0:
        value -= 10
        aces -= 1
    
    return value

def roll_dice() -> Tuple[int, int]:
    """Roll two dice"""
    return random.randint(1, 6), random.randint(1, 6)

# --- Game Betting Handlers ---

async def handle_slots_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle slots betting"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Extract bet amount from callback data
    bet_amount = float(query.data.split("_")[-1])
    
    # Check user balance
    user = await get_user(user_id)
    if not user or user['balance'] < bet_amount:
        await query.edit_message_text(
            "❌ Insufficient balance! Please deposit more funds.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Deposit", callback_data="deposit")]])
        )
        return
    
    # Deduct bet amount
    success = await deduct_balance(user_id, bet_amount)
    if not success:
        await query.edit_message_text("❌ Error processing bet. Please try again.")
        return
    
    # Play the game
    reels = generate_slot_reels()
    win_amount, result_text = calculate_slots_win(reels, bet_amount)
    
    # Update balance if won
    if win_amount > 0:
        await update_balance(user_id, win_amount)
    
    # Log game session
    await log_game_session(user_id, 'slots', bet_amount, win_amount, result_text)
    
    # Update house balance
    await update_house_balance_on_game(bet_amount, win_amount)
    
    # Get updated balance
    user = await get_user(user_id)
    balance_str = await format_usd(user['balance'])
    
    # Create result message
    slots_display = f"{reels[0]} | {reels[1]} | {reels[2]}"
    
    if win_amount > 0:
        result_message = f"""
<b>SLOT RESULT</b>

{slots_display}

{result_text}

<b>Bet:</b> ${bet_amount:.2f}
<b>Won:</b> ${win_amount:.2f}
<b>Balance:</b> {balance_str}

Keep spinning!
"""
    else:
        result_message = f"""
<b>SLOT RESULT</b>

{slots_display}

{result_text}

<b>Bet:</b> ${bet_amount:.2f}
<b>Lost:</b> ${bet_amount:.2f}
<b>Balance:</b> {balance_str}

Better luck next time!
"""
    
    keyboard = [
        [
            InlineKeyboardButton("Play Again", callback_data="game_slots"),
            InlineKeyboardButton("Other Games", callback_data="mini_app_centre")
        ],
        [InlineKeyboardButton("Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(result_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def handle_blackjack_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle blackjack betting"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Extract bet amount from callback data
    bet_amount = float(query.data.split("_")[-1])
    
    # Check user balance
    user = await get_user(user_id)
    if not user or user['balance'] < bet_amount:
        await query.edit_message_text(
            "❌ Insufficient balance! Please deposit more funds.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Deposit", callback_data="deposit")]])
        )
        return
    
    # Deduct bet amount
    success = await deduct_balance(user_id, bet_amount)
    if not success:
        await query.edit_message_text("❌ Error processing bet. Please try again.")
        return
    
    # Play the game
    player_hand = generate_blackjack_hand()
    dealer_hand = generate_blackjack_hand()
    
    player_value = calculate_hand_value(player_hand)
    dealer_value = calculate_hand_value(dealer_hand)
    
    # Simple blackjack logic (auto-play)
    win_amount = 0.0
    result_text = ""
    
    if player_value == 21:
        # Player blackjack
        win_amount = bet_amount * 2.5  # 3:2 payout
        result_text = "BLACKJACK! You got 21!"
    elif player_value > 21:
        # Player bust
        result_text = f"BUST! You went over 21 with {player_value}"
    elif dealer_value > 21:
        # Dealer bust
        win_amount = bet_amount * 2
        result_text = f"DEALER BUST! Dealer went over 21 with {dealer_value}"
    elif player_value > dealer_value:
        # Player wins
        win_amount = bet_amount * 2
        result_text = f"YOU WIN! {player_value} beats {dealer_value}"
    elif player_value == dealer_value:
        # Push (tie)
        win_amount = bet_amount  # Return bet
        result_text = f"PUSH! Both got {player_value}"
    else:
        # Dealer wins
        result_text = f"DEALER WINS! {dealer_value} beats {player_value}"
    
    # Update balance if won
    if win_amount > 0:
        await update_balance(user_id, win_amount)
    
    # Log game session
    await log_game_session(user_id, 'blackjack', bet_amount, win_amount, result_text)
    
    # Update house balance
    await update_house_balance_on_game(bet_amount, win_amount)
    
    # Get updated balance
    user = await get_user(user_id)
    balance_str = await format_usd(user['balance'])
    
    # Create result message
    player_cards = " ".join(player_hand)
    dealer_cards = " ".join(dealer_hand)
    
    result_message = f"""
<b>BLACKJACK RESULT</b>

<b>Your Hand:</b> {player_cards} (Value: {player_value})
<b>Dealer Hand:</b> {dealer_cards} (Value: {dealer_value})

{result_text}

<b>Bet:</b> ${bet_amount:.2f}
<b>Won:</b> ${win_amount:.2f}
<b>Balance:</b> {balance_str}
"""
    
    keyboard = [
        [
            InlineKeyboardButton("Play Again", callback_data="game_blackjack"),
            InlineKeyboardButton("Other Games", callback_data="mini_app_centre")
        ],
        [InlineKeyboardButton("Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(result_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def handle_dice_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle dice betting - show betting options"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Extract bet amount from callback data
    bet_amount = float(query.data.split("_")[-1])
    
    # Check user balance
    user = await get_user(user_id)
    if not user or user['balance'] < bet_amount:
        await query.edit_message_text(
            "❌ Insufficient balance! Please deposit more funds.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Deposit", callback_data="deposit")]])
        )
        return
    
    # Store bet amount in user data for the next step
    context.user_data['dice_bet_amount'] = bet_amount
    
    balance_str = await format_usd(user['balance'])
    
    text = f"""
<b>DICE GAME</b>

<b>Your Balance:</b> {balance_str}
<b>Bet Amount:</b> ${bet_amount:.2f}

Choose your prediction:
"""
    
    keyboard = [
        [
            InlineKeyboardButton("HIGH (8-12) - 2x", callback_data=f"dice_play_high_{bet_amount}"),
            InlineKeyboardButton("LOW (2-7) - 2x", callback_data=f"dice_play_low_{bet_amount}")
        ],
        [InlineKeyboardButton("LUCKY 7 - 5x", callback_data=f"dice_play_seven_{bet_amount}")],
        [InlineKeyboardButton("Back to Games", callback_data="mini_app_centre")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def handle_dice_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle dice game play"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Parse callback data: dice_play_high_25 or dice_play_low_10 or dice_play_seven_50
    parts = query.data.split("_")
    prediction = parts[2]  # high, low, seven
    bet_amount = float(parts[3])
    
    # Deduct bet amount
    success = await deduct_balance(user_id, bet_amount)
    if not success:
        await query.edit_message_text("❌ Error processing bet. Please try again.")
        return
    
    # Roll dice
    die1, die2 = roll_dice()
    total = die1 + die2
    
    # Get dice emojis
    dice_emojis = {1: '⚀', 2: '⚁', 3: '⚂', 4: '⚃', 5: '⚄', 6: '⚅'}
    die1_emoji = dice_emojis[die1]
    die2_emoji = dice_emojis[die2]
    
    # Calculate result
    win_amount = 0.0
    result_text = ""
    
    if prediction == "high" and total >= 8:
        win_amount = bet_amount * 2
        result_text = f"YOU WIN! {total} is HIGH!"
    elif prediction == "low" and total <= 7:
        win_amount = bet_amount * 2
        result_text = f"YOU WIN! {total} is LOW!"
    elif prediction == "seven" and total == 7:
        win_amount = bet_amount * 5
        result_text = f"LUCKY 7! Perfect prediction!"
    else:
        if prediction == "high":
            result_text = f"You predicted HIGH but got {total}"
        elif prediction == "low":
            result_text = f"You predicted LOW but got {total}"
        elif prediction == "seven":
            result_text = f"You predicted 7 but got {total}"
    
    # Update balance if won
    if win_amount > 0:
        await update_balance(user_id, win_amount)
    
    # Log game session
    await log_game_session(user_id, 'dice', bet_amount, win_amount, result_text)
    
    # Update house balance
    await update_house_balance_on_game(bet_amount, win_amount)
    
    # Get updated balance
    user = await get_user(user_id)
    balance_str = await format_usd(user['balance'])
    
    # Create result message
    result_message = f"""
<b>DICE RESULT</b>

<b>Dice Roll:</b> {die1_emoji} {die2_emoji}
<b>Total:</b> {total}

{result_text}

<b>Bet:</b> ${bet_amount:.2f}
<b>Won:</b> ${win_amount:.2f}
<b>Balance:</b> {balance_str}
"""
    
    keyboard = [
        [
            InlineKeyboardButton("Play Again", callback_data="game_dice"),
            InlineKeyboardButton("Other Games", callback_data="mini_app_centre")
        ],
        [InlineKeyboardButton("Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(result_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)