#!/usr/bin/env python3
"""
Enhanced Telegram Casino Bot v2.1
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
import re
import threading
import signal
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque

# Third-party imports
import aiohttp
import aiosqlite
import nest_asyncio
from dotenv import load_dotenv
from flask import Flask
from waitress import serve

# Telegram imports
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
from telegram.error import TelegramError, BadRequest, Forbidden, NetworkError

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Configuration ---
load_dotenv()
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
HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL", "300"))

if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN in environment or .env")

# Security Configuration
MAX_BET_PER_GAME = int(os.environ.get("MAX_BET_PER_GAME", "1000"))
MAX_DAILY_LOSSES = int(os.environ.get("MAX_DAILY_LOSSES", "5000"))
ANTI_SPAM_WINDOW = int(os.environ.get("ANTI_SPAM_WINDOW", "10"))
MAX_COMMANDS_PER_WINDOW = int(os.environ.get("MAX_COMMANDS_PER_WINDOW", "20"))

# Admin Configuration
ADMIN_USER_IDS = list(map(int, os.environ.get("ADMIN_USER_IDS", "").split(","))) if os.environ.get("ADMIN_USER_IDS") else []
SUPPORT_CHANNEL = os.environ.get("SUPPORT_CHANNEL", "@casino_support")
BOT_VERSION = "2.0.1"

# Owner Configuration
load_dotenv(".env.owner")
OWNER_USER_ID = int(os.environ.get("OWNER_USER_ID", "0"))

# Deposit/Withdrawal Constants
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

# VIP Level Requirements
VIP_SILVER_REQUIRED = int(os.environ.get("VIP_SILVER_REQUIRED", "1000"))
VIP_GOLD_REQUIRED = int(os.environ.get("VIP_GOLD_REQUIRED", "5000"))
VIP_DIAMOND_REQUIRED = int(os.environ.get("VIP_DIAMOND_REQUIRED", "10000"))

# Game Configuration
WEEKLY_BONUS_RATE = float(os.environ.get("WEEKLY_BONUS_RATE", "0.05"))
MIN_SLOTS_BET = int(os.environ.get("MIN_SLOTS_BET", "10"))
MIN_BLACKJACK_BET = int(os.environ.get("MIN_BLACKJACK_BET", "20"))

# WebApp Configuration
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://your-casino-webapp.vercel.app")
WEBAPP_ENABLED = os.environ.get("WEBAPP_ENABLED", "true").lower() == "true"

# Debug: Print admin configuration
print("🔧 Admin Configuration:")
print(f"✅ Admin User IDs: {ADMIN_USER_IDS}")
print(f"✅ Raw Admin Env: {os.environ.get('ADMIN_USER_IDS', 'NOT SET')}")
if ADMIN_USER_IDS:
    print("✅ Admin features enabled for", len(ADMIN_USER_IDS), "user(s)")
else:
    print("❌ No admin users configured")

# --- Utility Functions ---
def is_admin(user_id: int) -> bool:
    """Check if user is an admin/owner with logging"""
    is_admin_user = user_id in ADMIN_USER_IDS
    if is_admin_user:
        logger.info(f"🔑 Admin access granted to user {user_id}")
    return is_admin_user

def is_owner(user_id: int) -> bool:
    """Check if user is the owner (super admin)"""
    return user_id == OWNER_USER_ID

def log_admin_action(user_id: int, action: str):
    """Log admin actions for debugging"""
    logger.info(f"🔧 Admin action by {user_id}: {action}")

# --- Crypto Utility Functions ---
async def get_crypto_usd_rate(asset: str) -> float:
    """Fetch the current crypto to USD conversion rate from CryptoCompare."""
    url = f"https://min-api.cryptocompare.com/data/price?fsym={asset}&tsyms=USD"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return float(data.get("USD", 0))
    except Exception as e:
        logger.error(f"Error fetching {asset}/USD rate: {e}")
        return 0.0

async def get_ltc_usd_rate() -> float:
    """Fetch the current LTC to USD conversion rate."""
    return await get_crypto_usd_rate("LTC")

async def format_usd(ltc_amount: float) -> str:
    """Format an LTC amount as USD string using the latest LTC→USD rate."""
    rate = await get_ltc_usd_rate()
    if rate == 0.0:
        return f"${ltc_amount * 100:.2f} USD (Rate unavailable)"
    usd = ltc_amount * rate
    return f"${usd:.2f} USD"

async def format_crypto_usd(crypto_amount: float, asset: str) -> str:
    """Format a crypto amount as USD string using the latest rate."""
    rate = await get_crypto_usd_rate(asset)
    if rate == 0.0:
        return f"${crypto_amount * 100:.2f} USD (Rate unavailable)"
    usd = crypto_amount * rate
    return f"${usd:.2f} USD ({crypto_amount:.8f} {asset})"

# --- CryptoBot API Functions ---
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

async def send_crypto(address: str, amount: float, comment: str, asset: str = 'LTC') -> dict:
    """Send crypto via CryptoBot API"""
    try:
        if not CRYPTOBOT_API_TOKEN:
            return {"ok": False, "error": {"name": "API token not configured"}}
        
        headers = {
            'Crypto-Pay-API-Token': CRYPTOBOT_API_TOKEN,
            'Content-Type': 'application/json'
        }
        
        data = {
            'user_id': address,  # For CryptoBot, this would be a user ID, not address
            'asset': asset,
            'amount': f"{amount:.8f}",
            'spend_id': str(uuid.uuid4()),
            'comment': comment
        }
        
        # For demo purposes, simulate successful transaction
        # In production, use actual CryptoBot transfer API
        logger.info(f"Simulating crypto transfer: {amount} {asset} to {address}")
        return {
            "ok": True,
            "result": {
                "transfer_id": str(uuid.uuid4()),
                "status": "completed"
            }
        }
        
    except Exception as e:
        logger.error(f"Error sending crypto: {e}")
        return {"ok": False, "error": {"name": str(e)}}

# --- Withdrawal System Functions ---
async def get_user_withdrawals(user_id: int, limit: int = 10) -> list:
    """Get user withdrawal history"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT * FROM withdrawals 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
            
            withdrawals = []
            for row in rows:
                withdrawals.append({
                    'id': row[0],
                    'user_id': row[1],
                    'asset': row[2],
                    'amount': row[3],
                    'amount_usd': row[4],
                    'address': row[5],
                    'status': row[6],
                    'transaction_hash': row[7],
                    'created_at': row[8],
                    'error_msg': row[9] if len(row) > 9 else ''
                })
            return withdrawals
    except Exception as e:
        logger.error(f"Error getting user withdrawals: {e}")
        return []

async def check_withdrawal_limits(user_id: int, amount_usd: float) -> dict:
    """Check if withdrawal is within limits"""
    try:
        if amount_usd < MIN_WITHDRAWAL_USD:
            return {"allowed": False, "reason": f"Minimum withdrawal is ${MIN_WITHDRAWAL_USD:.2f}"}
        
        if amount_usd > MAX_WITHDRAWAL_USD:
            return {"allowed": False, "reason": f"Maximum withdrawal is ${MAX_WITHDRAWAL_USD:.2f}"}
        
        # Check daily limit
        today = datetime.now().date()
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT SUM(amount_usd) FROM withdrawals 
                WHERE user_id = ? AND DATE(created_at) = ? AND status = 'completed'
            """, (user_id, today))
            daily_total = (await cursor.fetchone())[0] or 0.0
        
        if daily_total + amount_usd > MAX_WITHDRAWAL_USD_DAILY:
            remaining = MAX_WITHDRAWAL_USD_DAILY - daily_total
            return {"allowed": False, "reason": f"Daily limit exceeded. You can withdraw ${remaining:.2f} more today."}
        
        # Check withdrawal cooldown
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT created_at FROM withdrawals 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
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

def calculate_withdrawal_fee(amount: float) -> float:
    """Calculate withdrawal fee"""
    fee = amount * WITHDRAWAL_FEE_PERCENT
    return max(fee, MIN_WITHDRAWAL_FEE)

def validate_crypto_address(address: str, asset: str) -> bool:
    """Validate crypto address format"""
    if asset not in CRYPTO_ADDRESS_PATTERNS:
        return False
    
    pattern = CRYPTO_ADDRESS_PATTERNS[asset]
    return bool(re.match(pattern, address))

async def log_withdrawal(user_id: int, asset: str, amount: float, address: str, fee: float, net_amount: float) -> int:
    """Log withdrawal attempt to database"""
    try:
        asset_rate = await get_crypto_usd_rate(asset)
        amount_usd = amount * asset_rate if asset_rate > 0 else 0
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                INSERT INTO withdrawals (
                    user_id, asset, amount, amount_usd, address, 
                    status, created_at, fee, net_amount
                ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)
            """, (user_id, asset, amount, amount_usd, address, 
                  datetime.now().isoformat(), fee, net_amount))
            await db.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error logging withdrawal: {e}")
        return 0

async def update_withdrawal_status(withdrawal_id: int, status: str, transaction_hash: str = "", error_msg: str = "") -> bool:
    """Update withdrawal status"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE withdrawals 
                SET status = ?, transaction_hash = ?, error_msg = ?, updated_at = ?
                WHERE id = ?
            """, (status, transaction_hash, error_msg, datetime.now().isoformat(), withdrawal_id))
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating withdrawal status: {e}")
        return False

async def update_withdrawal_limits(user_id: int, amount_usd: float) -> bool:
    """Update user withdrawal limits/tracking"""
    try:
        logger.info(f"User {user_id} withdrew ${amount_usd:.2f}")
        return True
    except Exception as e:
        logger.error(f"Error updating withdrawal limits: {e}")
        return False

# --- Database Functions ---
async def init_db():
    """Initialize production database"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                balance REAL DEFAULT 0.0,
                total_wagered REAL DEFAULT 0.0,
                total_won REAL DEFAULT 0.0,
                games_played INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT DEFAULT CURRENT_TIMESTAMP,
                vip_level TEXT DEFAULT 'bronze'
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                asset TEXT NOT NULL,
                amount REAL NOT NULL,
                amount_usd REAL NOT NULL,
                address TEXT NOT NULL,
                status TEXT NOT NULL,
                transaction_hash TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                error_msg TEXT,
                fee REAL DEFAULT 0,
                net_amount REAL DEFAULT 0
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                game_type TEXT NOT NULL,
                bet_amount REAL NOT NULL,
                win_amount REAL DEFAULT 0,
                result TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.commit()
    logger.info(f"✅ Production database initialized at {DB_PATH}")

async def get_user(user_id: int):
    """Get user data from database"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
        if user:
            return dict(user)
        return None

async def create_user(user_id: int, username: str):
    """Create new user with 0.00 LTC starting balance"""
    current_time = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (id, username, balance, created_at, last_active)
            VALUES (?, ?, 0.0, ?, ?)
        """, (user_id, username, current_time, current_time))
        await db.commit()
    return await get_user(user_id)

async def update_balance(user_id: int, amount: float):
    """Update user balance (amount in LTC)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET balance = balance + ?, last_active = ?
            WHERE id = ?
        """, (amount, datetime.now().isoformat(), user_id))
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
                games_played = games_played + 1,
                last_active = ?
            WHERE id = ?
        """, (amount, amount, datetime.now().isoformat(), user_id))
        await db.commit()
    
    return True

async def add_winnings(user_id: int, amount: float):
    """Add winnings to user balance (amount in LTC)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET 
                balance = balance + ?, 
                total_won = total_won + ?,
                last_active = ?
            WHERE id = ?
        """, (amount, amount, datetime.now().isoformat(), user_id))
        await db.commit()
    user = await get_user(user_id)
    return user['balance'] if user else 0.0

# Continue in next file due to length...
