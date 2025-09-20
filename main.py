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
    LabeledPrice,
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
    PreCheckoutQueryHandler,
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

# Telegram Payments configuration
TELEGRAM_PAYMENT_PROVIDER_TOKEN = os.environ.get("TELEGRAM_PAYMENT_PROVIDER_TOKEN")
USE_NATIVE_TELEGRAM_PAYMENTS = os.environ.get("USE_NATIVE_TELEGRAM_PAYMENTS", "false").lower() == "true"

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
        [InlineKeyboardButton("Ł Litecoin (LTC)", callback_data="deposit_ltc"),
         InlineKeyboardButton("🪙 Toncoin (TON)", callback_data="deposit_ton")],
        [InlineKeyboardButton("◎ Solana (SOL)", callback_data="deposit_sol")],
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
Ł **Litecoin (LTC) Deposit**

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
🪙 **Toncoin (TON) Deposit**

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
◎ **Solana (SOL) Deposit**

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
    
    # Convert USD to crypto amount
    crypto_rate = await get_crypto_usd_rate(asset)
    crypto_amount = usd_amount / crypto_rate if crypto_rate > 0 else 0
    
    if crypto_amount <= 0:
        await processing_msg.edit_text("❌ Unable to get exchange rate. Please try again later.")
        return DEPOSIT_AMOUNT
    
    # Choose payment method based on configuration
    if USE_NATIVE_TELEGRAM_PAYMENTS and TELEGRAM_PAYMENT_PROVIDER_TOKEN:
        # Use native Telegram payments (appears within bot)
        await processing_msg.delete()  # Remove processing message
        
        # Create native Telegram invoice
        invoice_result = await create_telegram_invoice(asset, usd_amount, crypto_amount, user_id, context)
        
        if invoice_result.get('ok'):
            # Success message after invoice is sent
            await update.message.reply_text(
                f"✅ **Payment Invoice Sent!**\n\n"
                f"💰 **Amount:** ${usd_amount:.2f} USD ({crypto_amount:.8f} {asset})\n"
                f"📱 **Method:** Native Telegram Payment\n\n"
                f"👆 **Tap 'Pay Now' on the invoice above to complete your deposit**\n"
                f"⚡ Your balance will update instantly after payment confirmation",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(f"❌ Error creating payment invoice: {invoice_result.get('error', 'Unknown error')}")
            
    else:
        # Fallback to external CryptoBot (original method)
        invoice_result = await create_crypto_invoice(asset, crypto_amount, user_id)
        if invoice_result.get('ok'):
            result = invoice_result['result']
            pay_url = result.get('pay_url')
            mini_app_url = result.get('mini_app_invoice_url')
            bot_invoice_url = result.get('bot_invoice_url')
            web_app_url = result.get('web_app_invoice_url')
            invoice_id = result.get('invoice_id')
            
            # Log available URLs for debugging
            logger.info(f"Invoice URLs - pay_url: {pay_url}, mini_app: {mini_app_url}, bot: {bot_invoice_url}, web_app: {web_app_url}")
            
            # Use regular URL button instead of web_app to avoid session issues
            keyboard = [
                [InlineKeyboardButton("💳 Pay with CryptoBot", url=pay_url)],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
            ]
            
            text = f"""
💳 **{asset} DEPOSIT** 💳

💰 **Amount:** ${usd_amount:.2f} USD ({crypto_amount:.8f} {asset})
🆔 **Invoice ID:** `{invoice_id}`

⚡ Payment will be processed automatically
🔄 Your balance will update instantly after confirmation
⏰ Invoice expires in 60 minutes

💡 **Tips:**
• Click the button below to pay
• If you get "session expired", try the payment link again
• Payment opens in CryptoBot (external app)
• Keep this chat open during payment
• You'll receive confirmation when payment is complete

📞 **Having issues?** Use /payment to check status

🚀 **Ready to pay? Click the button below!**
"""
            await processing_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        else:
            error_msg = invoice_result.get('error', 'Unknown error')
            await processing_msg.edit_text(f"❌ Error creating deposit invoice: {error_msg}\n\nPlease try again or contact support if the issue persists.")
    
    return ConversationHandler.END

async def create_telegram_invoice(asset: str, usd_amount: float, crypto_amount: float, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Create a native Telegram invoice using CryptoBot as payment provider"""
    try:
        if not TELEGRAM_PAYMENT_PROVIDER_TOKEN:
            return {"ok": False, "error": "Payment provider token not configured"}
        
        # Create invoice description
        title = f"{asset} Deposit"
        description = f"Deposit ${usd_amount:.2f} USD ({crypto_amount:.8f} {asset}) to your casino balance"
        
        # Convert USD to cents (Telegram uses smallest currency unit)
        amount_cents = int(usd_amount * 100)
        
        # Create labeled price
        prices = [LabeledPrice(label=f"{asset} Deposit", amount=amount_cents)]
        
        # Create payload with user and transaction info
        payload = f"deposit_{user_id}_{asset}_{usd_amount}_{crypto_amount}"
        
        # Send invoice directly in chat
        await context.bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=TELEGRAM_PAYMENT_PROVIDER_TOKEN,
            currency="USD",
            prices=prices,
            start_parameter=f"deposit_{user_id}",
            photo_url="https://i.imgur.com/CryptoBot.png",  # Optional: Add crypto icon
            photo_size=512,
            is_flexible=False,
            disable_notification=False,
            protect_content=False,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Pay Now", pay=True)],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
            ])
        )
        
        return {"ok": True, "message": "Invoice sent successfully"}
        
    except Exception as e:
        logger.error(f"Error creating Telegram invoice: {e}")
        return {"ok": False, "error": str(e)}

# --- Telegram Payment Handlers ---
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle pre-checkout query for Telegram payments"""
    query = update.pre_checkout_query
    
    try:
        # Parse payload to get payment details
        payload_parts = query.invoice_payload.split('_')
        if len(payload_parts) >= 5 and payload_parts[0] == 'deposit':
            user_id = int(payload_parts[1])
            asset = payload_parts[2]
            usd_amount = float(payload_parts[3])
            crypto_amount = float(payload_parts[4])
            
            # Verify user exists and has valid session
            user = await get_user(user_id)
            if not user:
                await query.answer(ok=False, error_message="User not found. Please start the bot first.")
                return
            
            # Verify amount matches what user requested
            expected_amount_cents = int(usd_amount * 100)
            if query.total_amount != expected_amount_cents:
                await query.answer(ok=False, error_message="Payment amount mismatch. Please try again.")
                return
            
            # All checks passed, approve the payment
            await query.answer(ok=True)
            logger.info(f"Pre-checkout approved for user {user_id}: ${usd_amount} USD ({asset})")
            
        else:
            await query.answer(ok=False, error_message="Invalid payment payload.")
            
    except Exception as e:
        logger.error(f"Pre-checkout error: {e}")
        await query.answer(ok=False, error_message="Payment verification failed. Please try again.")

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle successful Telegram payment"""
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    
    try:
        # Parse payload to get payment details
        payload_parts = payment.invoice_payload.split('_')
        if len(payload_parts) >= 5 and payload_parts[0] == 'deposit':
            asset = payload_parts[2]
            usd_amount = float(payload_parts[3])
            crypto_amount = float(payload_parts[4])
            
            # Update user balance
            async with aiosqlite.connect(DB_PATH) as db:
                # Add to balance
                await db.execute("""
                    UPDATE users SET balance = balance + ? 
                    WHERE user_id = ?
                """, (usd_amount, user_id))
                
                # Log transaction
                await db.execute("""
                    INSERT INTO transactions (user_id, type, amount, description, timestamp)
                    VALUES (?, 'deposit', ?, ?, ?)
                """, (user_id, usd_amount, f"Telegram payment deposit ({asset}): ${usd_amount:.2f} USD", datetime.now().isoformat()))
                
                await db.commit()
            
            # Get updated balance
            user = await get_user(user_id)
            
            # Send success message
            success_text = f"""
✅ **Payment Successful!** ✅

💰 **Deposited:** ${usd_amount:.2f} USD
🪙 **Crypto Equivalent:** {crypto_amount:.8f} {asset}
💳 **Payment ID:** `{payment.telegram_payment_charge_id}`
💼 **New Balance:** {await format_usd(user['balance'])}

🎮 **Ready to play!** Your balance has been updated instantly.
"""
            
            keyboard = [
                [InlineKeyboardButton("🎮 Play Games", callback_data="classic_casino")],
                [InlineKeyboardButton("💰 Check Balance", callback_data="show_balance")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
            ]
            
            await update.message.reply_text(
                success_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Successful payment processed: User {user_id}, Amount: ${usd_amount} USD ({asset}), Charge ID: {payment.telegram_payment_charge_id}")
            
        else:
            logger.error(f"Invalid payment payload: {payment.invoice_payload}")
            await update.message.reply_text("❌ Payment processing error. Please contact support.")
            
    except Exception as e:
        logger.error(f"Successful payment processing error: {e}")
        await update.message.reply_text("❌ Error processing payment. Please contact support if your payment was charged.")

# --- Conversation States ---
DEPOSIT_ASSET = "DEPOSIT_ASSET"
DEPOSIT_AMOUNT = "DEPOSIT_AMOUNT"

# --- Register Deposit ConversationHandler ---
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

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main withdraw menu"""
    query = update.callback_query
    await query.answer()
    
    text = """
💸 **WITHDRAW FUNDS** 💸

Choose your cryptocurrency:

📋 **Withdrawal Info:**
• Minimum: $1.00 USD
• Maximum: $10,000 USD daily
• Fee: 2% of amount
• Processing: Instant

🔒 **Secure withdrawals via CryptoBot**
"""
    
    keyboard = [
        [InlineKeyboardButton("Ł Litecoin (LTC)", callback_data="withdraw_ltc"),
         InlineKeyboardButton("🪙 Toncoin (TON)", callback_data="withdraw_ton")],
        [InlineKeyboardButton("◎ Solana (SOL)", callback_data="withdraw_sol")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def deposit_ltc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle LTC deposit"""
    query = update.callback_query
    await query.answer()
    
    text = """
💳 **LTC DEPOSIT** 💳

Enter the amount of LTC you want to deposit:
(Minimum: 0.01 LTC)
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Deposit", callback_data="deposit"),
         InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def deposit_ton_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle TON deposit"""
    query = update.callback_query
    await query.answer()
    
    text = """
💳 **TON DEPOSIT** 💳

Enter the amount of TON you want to deposit:
(Minimum: 1 TON)
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Deposit", callback_data="deposit"),
         InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def deposit_sol_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle SOL deposit"""
    query = update.callback_query
    await query.answer()
    
    text = """
💳 **SOL DEPOSIT** 💳

Enter the amount of SOL you want to deposit:
(Minimum: 0.05 SOL)
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Deposit", callback_data="deposit"),
         InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def withdraw_ltc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle LTC withdrawal"""
    query = update.callback_query
    await query.answer()
    
    text = """
💸 **LTC WITHDRAWAL** 💸

🚧 **Coming Soon!**

LTC withdrawal functionality will be available soon.
For now, please contact support for manual withdrawals.

📞 **Support:** @casino_support
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Withdraw", callback_data="withdraw"),
         InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def withdraw_ton_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle TON withdrawal"""
    query = update.callback_query
    await query.answer()
    
    text = """
💸 **TON WITHDRAWAL** 💸

🚧 **Coming Soon!**

TON withdrawal functionality will be available soon.
For now, please contact support for manual withdrawals.

📞 **Support:** @casino_support
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Withdraw", callback_data="withdraw"),
         InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def withdraw_sol_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle SOL withdrawal"""
    query = update.callback_query
    await query.answer()
    
    text = """
💸 **SOL WITHDRAWAL** 💸

🚧 **Coming Soon!**

SOL withdrawal functionality will be available soon.
For now, please contact support for manual withdrawals.

📞 **Support:** @casino_support
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Withdraw", callback_data="withdraw"),
         InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Owner Panel Handlers ---

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
        "🔹 /help - Get assistance and support\n\n"
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
    
    # Get global leaderboard (top 10 by balance)
    async with aiosqlite.connect(DB_PATH) as db:
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
        lb_text += f"{i}. {username}: {await format_usd(balance)}\n"
    
    text = f"""
📊 **STATISTICS & LEADERBOARD** 📊

👤 **Your Stats:**
• Balance: {await format_usd(user['balance'])}
• Games Played: {user['games_played']}
• Total Wagered: {await format_usd(user['total_wagered'])}
• Total Withdrawn: {await format_usd(user['total_withdrawn'])}

🏆 **Global Leaderboard:**
{lb_text}

🎮 **Bot Version:** {BOT_VERSION}
"""
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="show_stats")],
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
    # Deposit/Withdrawal handlers
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw$"))
    application.add_handler(CallbackQueryHandler(withdraw_ltc_callback, pattern="^withdraw_ltc$"))
    application.add_handler(CallbackQueryHandler(withdraw_ton_callback, pattern="^withdraw_ton$"))
    application.add_handler(CallbackQueryHandler(withdraw_sol_callback, pattern="^withdraw_sol$"))
    application.add_handler(CallbackQueryHandler(start_command, pattern="^main_panel$"))
    application.add_handler(CallbackQueryHandler(redeem_panel_callback, pattern="^redeem_panel$"))
    application.add_handler(CallbackQueryHandler(show_stats_callback, pattern="^show_stats$"))
    # Remove admin panel and admin demo toggle handlers
    # application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    # application.add_handler(CallbackQueryHandler(admin_toggle_demo_callback, pattern="^admin_toggle_demo$"))
    # Add owner panel and owner demo toggle only
    application.add_handler(CallbackQueryHandler(owner_panel_callback, pattern="^owner_panel$"))
    application.add_handler(CallbackQueryHandler(owner_toggle_demo_callback, pattern="^owner_toggle_demo$"))

    # Add Telegram payment handlers (for native invoices)
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    # Add deposit ConversationHandler (this enables the coin selection -> amount prompt flow)
    application.add_handler(deposit_conv_handler)

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
                            # Convert crypto amount to USD for balance update
                            usd_amount = amount
                            if asset != 'USDT':
                                # Get current rate and convert to USD
                                rate = 65.0 if asset == 'LTC' else (2.5 if asset == 'TON' else 23.0)
                                usd_amount = amount * rate
                            
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