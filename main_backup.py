# bot.py
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
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv
import aiohttp
import aiohttp.web
import signal
import sys
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from flask import Flask
from waitress import serve

import aiosqlite
from bot.database.db import DATABASE_PATH
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

# Import nest_asyncio for event loop compatibility
import nest_asyncio

# Logging setup - Must be at the top before any code that uses logger
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Global variables
start_time = time.time()  # Record bot start time for metrics

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
                SELECT * FROM withdrawals 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
            
            # Convert to dict format
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
        # Check minimum amount
        if amount_usd < MIN_WITHDRAWAL_USD:
            return {"allowed": False, "reason": f"Minimum withdrawal is ${MIN_WITHDRAWAL_USD:.2f}"}
        
        # Check maximum amount
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
    import re
    
    if asset not in CRYPTO_ADDRESS_PATTERNS:
        return False
    
    pattern = CRYPTO_ADDRESS_PATTERNS[asset]
    return bool(re.match(pattern, address))

async def log_withdrawal(user_id: int, asset: str, amount: float, address: str, fee: float, net_amount: float) -> int:
    """Log withdrawal attempt to database"""
    try:
        # Get current USD rate for the asset
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
        # Convert to USD for logging
        asset_rate = await get_crypto_usd_rate(asset)
        amount_usd = amount * asset_rate if asset_rate > 0 else 0
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                INSERT INTO withdrawals (user_id, asset, amount, amount_usd, address, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """, (user_id, asset, amount, amount_usd, address, datetime.now().isoformat()))
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
        
        # Actual CryptoBot API call (commented out for demo):
        # async with aiohttp.ClientSession() as session:
        #     async with session.post('https://pay.crypt.bot/api/transfer', 
        #                           headers=headers, json=data) as response:
        #         result = await response.json()
        #         return result
                
    except Exception as e:
        logger.error(f"Error sending crypto: {e}")
        return {"ok": False, "error": {"name": str(e)}}

async def update_withdrawal_limits(user_id: int, amount_usd: float) -> bool:
    """Update user withdrawal limits/tracking"""
    try:
        # This could track daily limits, monthly limits, etc.
        # For now, we just log the successful withdrawal
        logger.info(f"User {user_id} withdrew ${amount_usd:.2f}")
        return True
    except Exception as e:
        logger.error(f"Error updating withdrawal limits: {e}")
        return False

# --- Essential Utility Functions (Must be defined early) ---

# Complete crypto rate fetching
async def get_crypto_usd_rate(asset: str) -> float:
    """Fetch the current crypto to USD conversion rate from CryptoCompare."""
    url = f"https://min-api.cryptocompare.com/data/price?fsym={asset}&tsyms=USD"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return float(data.get('USD', 0.0))
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
        return f"{ltc_amount:.8f} LTC (Rate unavailable)"
    usd = ltc_amount * rate
    return f"${usd:.2f} USD"

async def format_crypto_usd(crypto_amount: float, asset: str) -> str:
    """Format a crypto amount as USD string using the latest rate."""
    rate = await get_crypto_usd_rate(asset)
    if rate == 0.0:
        return f"{crypto_amount:.8f} {asset} (Rate unavailable)"
    usd = crypto_amount * rate
    return f"${usd:.2f} USD ({crypto_amount:.8f} {asset})"

# --- Owner (Super Admin) Configuration ---
load_dotenv(".env.owner")  # Load owner ID from dedicated file
OWNER_USER_ID = int(os.environ.get("OWNER_USER_ID", "0"))

def is_owner(user_id: int) -> bool:
    """Check if user is the owner (super admin)"""
    return user_id == OWNER_USER_ID

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
                SELECT * FROM withdrawals 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
            
            # Convert to dict format
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
        # Check minimum amount
        if amount_usd < MIN_WITHDRAWAL_USD:
            return {"allowed": False, "reason": f"Minimum withdrawal is ${MIN_WITHDRAWAL_USD:.2f}"}
        
        # Check maximum amount
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
    import re
    
    if asset not in CRYPTO_ADDRESS_PATTERNS:
        return False
    
    pattern = CRYPTO_ADDRESS_PATTERNS[asset]
    return bool(re.match(pattern, address))

async def log_withdrawal(user_id: int, asset: str, amount: float, address: str, fee: float, net_amount: float) -> int:
    """Log withdrawal attempt to database"""
    try:
        # Get current USD rate for the asset
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
        # Convert to USD for logging
        asset_rate = await get_crypto_usd_rate(asset)
        amount_usd = amount * asset_rate if asset_rate > 0 else 0
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                INSERT INTO withdrawals (user_id, asset, amount, amount_usd, address, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """, (user_id, asset, amount, amount_usd, address, datetime.now().isoformat()))
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
        
        # Actual CryptoBot API call (commented out for demo):
        # async with aiohttp.ClientSession() as session:
        #     async with session.post('https://pay.crypt.bot/api/transfer', 
        #                           headers=headers, json=data) as response:
        #         result = await response.json()
        #         return result
                
    except Exception as e:
        logger.error(f"Error sending crypto: {e}")
        return {"ok": False, "error": {"name": str(e)}}

async def update_withdrawal_limits(user_id: int, amount_usd: float) -> bool:
    """Update user withdrawal limits/tracking"""
    try:
        # This could track daily limits, monthly limits, etc.
        # For now, we just log the successful withdrawal
        logger.info(f"User {user_id} withdrew ${amount_usd:.2f}")
        return True
    except Exception as e:
        logger.error(f"Error updating withdrawal limits: {e}")
        return False

# --- Essential Utility Functions (Must be defined early) ---

# Complete crypto rate fetching
async def get_crypto_usd_rate(asset: str) -> float:
    """Fetch the current crypto to USD conversion rate from CryptoCompare."""
    url = f"https://min-api.cryptocompare.com/data/price?fsym={asset}&tsyms=USD"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return float(data.get('USD', 0.0))
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
        return f"{ltc_amount:.8f} LTC (Rate unavailable)"
    usd = ltc_amount * rate
    return f"${usd:.2f} USD"

async def format_crypto_usd(crypto_amount: float, asset: str) -> str:
    """Format a crypto amount as USD string using the latest rate."""
    rate = await get_crypto_usd_rate(asset)
    if rate == 0.0:
        return f"{crypto_amount:.8f} {asset} (Rate unavailable)"
    usd = crypto_amount * rate
    return f"${usd:.2f} USD ({crypto_amount:.8f} {asset})"

# --- Owner (Super Admin) Configuration ---
load_dotenv(".env.owner")  # Load owner ID from dedicated file
OWNER_USER_ID = int(os.environ.get("OWNER_USER_ID", "0"))

def is_owner(user_id: int) -> bool:
    """Check if user is the owner (super admin)"""
    return user_id == OWNER_USER_ID

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
                SELECT * FROM withdrawals 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
            
            # Convert to dict format
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
        # Check minimum amount
        if amount_usd < MIN_WITHDRAWAL_USD:
            return {"allowed": False, "reason": f"Minimum withdrawal is ${MIN_WITHDRAWAL_USD:.2f}"}
        
        # Check maximum amount
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
    import re
    
    if asset not in CRYPTO_ADDRESS_PATTERNS:
        return False
    
    pattern = CRYPTO_ADDRESS_PATTERNS[asset]
    return bool(re.match(pattern, address))

async def log_withdrawal(user_id: int, asset: str, amount: float, address: str, fee: float, net_amount: float) -> int:
    """Log withdrawal attempt to database"""
    try:
        # Get current USD rate for the asset
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
        # Convert to USD for logging
        asset_rate = await get_crypto_usd_rate(asset)
        amount_usd = amount * asset_rate if asset_rate > 0 else 0
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                INSERT INTO withdrawals (user_id, asset, amount, amount_usd, address, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """, (user_id, asset, amount, amount_usd, address, datetime.now().isoformat()))
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
        
        # Actual CryptoBot API call (commented out for demo):
        # async with aiohttp.ClientSession() as session:
        #     async with session.post('https://pay.crypt.bot/api/transfer', 
        #                           headers=headers, json=data) as response:
        #         result = await response.json()
        #         return result
                
    except Exception as e:
        logger.error(f"Error sending crypto: {e}")
        return {"ok": False, "error": {"name": str(e)}}

async def update_withdrawal_limits(user_id: int, amount_usd: float) -> bool:
    """Update user withdrawal limits/tracking"""
    try:
        # This could track daily limits, monthly limits, etc.
        # For now, we just log the successful withdrawal
        logger.info(f"User {user_id} withdrew ${amount_usd:.2f}")
        return True
    except Exception as e:
        logger.error(f"Error updating withdrawal limits: {e}")
        return False

# --- Essential Utility Functions (Must be defined early) ---

# Complete crypto rate fetching
async def get_crypto_usd_rate(asset: str) -> float:
    """Fetch the current crypto to USD conversion rate from CryptoCompare."""
    url = f"https://min-api.cryptocompare.com/data/price?fsym={asset}&tsyms=USD"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return float(data.get('USD', 0.0))
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
        return f"{ltc_amount:.8f} LTC (Rate unavailable)"
    usd = ltc_amount * rate
    return f"${usd:.2f} USD"

async def format_crypto_usd(crypto_amount: float, asset: str) -> str:
    """Format a crypto amount as USD string using the latest rate."""
    rate = await get_crypto_usd_rate(asset)
    if rate == 0.0:
        return f"{crypto_amount:.8f} {asset} (Rate unavailable)"
    usd = crypto_amount * rate
    return f"${usd:.2f} USD ({crypto_amount:.8f} {asset})"

# --- Owner (Super Admin) Configuration ---
load_dotenv(".env.owner")  # Load owner ID from dedicated file
OWNER_USER_ID = int(os.environ.get("OWNER_USER_ID", "0"))

def is_owner(user_id: int) -> bool:
    """Check if user is the owner (super admin)"""
    return user_id == OWNER_USER_ID

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
                SELECT * FROM withdrawals 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
            
            # Convert to dict format
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
        # Check minimum amount
        if amount_usd < MIN_WITHDRAWAL_USD:
            return {"allowed": False, "reason": f"Minimum withdrawal is ${MIN_WITHDRAWAL_USD:.2f}"}
        
        # Check maximum amount
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

# --- Start Command ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    user_data = await get_user(user_id)
    if not user_data:
        user_data = await create_user(user_id, username)
    
    balance_usd = await format_usd(user_data['balance'])
    text = (
        f"🎰 CASINO BOT 🎰\n\n"
        f"👋 Welcome, {username}!\n\n"
        f"💰 Balance: {balance_usd}\n"
        f"🏆 Games Played: {user_data['games_played']}\n\n"
        "Choose an action below:"
    )
    keyboard = [
        [InlineKeyboardButton("🎮 Play", callback_data="mini_app_centre"), 
         InlineKeyboardButton("💰 Balance", callback_data="show_balance")],
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit"), 
         InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🎁 Redeem", callback_data="redeem_panel"), 
         InlineKeyboardButton("ℹ️ Help", callback_data="show_help")]
    ]
    
    if hasattr(update, 'callback_query') and update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error editing start message: {e}")
    else:
        message = getattr(update, 'message', None)
        if message:
            await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            logger.error("Could not send start message - no message context found")

# --- Mini App Centre ---
async def show_mini_app_centre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the simplified Mini App Centre with only an All Games button"""
    user_id = update.effective_user.id
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
        [InlineKeyboardButton("🎮 All Games", callback_data="all_games")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# --- Mini App Command ---
async def mini_app_centre_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command handler for /app"""
    await show_mini_app_centre(update, context)

# --- Classic Casino Handler ---
# Remove references to unwanted games (Poker, Turbo Spin, Memory Game, Daily Challenge, Bonus Hunt)
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

**🃏 BLACKJACK**
*Beat the dealer with strategy*
• Traditional 21 gameplay
• Insurance & double down
• Multiple betting options
• RTP: 98.5%

**🎡 ROULETTE**
*Red or black? Place your bets*
• European & American styles
• Inside & outside bets
• Live dealer experience
• RTP: 97.3%

**🎲 DICE GAMES**
*Simple odds, instant results*
• Even/odd predictions
• High/low bets
• Quick gameplay
• RTP: 98%
"""
    
    keyboard = [
        [InlineKeyboardButton("🎰 SLOTS", callback_data="play_slots"), InlineKeyboardButton("🃏 BLACKJACK", callback_data="play_blackjack")],
        [InlineKeyboardButton("🎡 ROULETTE", callback_data="play_roulette"), InlineKeyboardButton("🎲 DICE", callback_data="play_dice")],
        [InlineKeyboardButton("🔙 Back to App Centre", callback_data="mini_app_centre")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Slots Game ---
async def play_slots_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle slots game"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = await get_user(user_id)
    # Remove balance check here; let user set up bet first
    text = f"""
🎰 **SLOT MACHINES** 🎰

💰 Choose your bet amount (in USD):

🎯 **Game Info:**
• 3-reel classic slots
• Multiple paylines
• Bonus symbols
• Progressive jackpots

Select your bet:
"""
    
    keyboard = [
        [InlineKeyboardButton("🎰 Bet $10", callback_data="slots_bet_10"), InlineKeyboardButton("🎰 Bet $25", callback_data="slots_bet_25")],
        [InlineKeyboardButton("🎰 Bet $50", callback_data="slots_bet_50"), InlineKeyboardButton("🎰 Bet $100", callback_data="slots_bet_100")],
        [InlineKeyboardButton("🔙 Back to Classic", callback_data="classic_casino")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def handle_slots_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle slots betting"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    try:
        bet = int(data.split("_")[-1])
    except:
        await query.answer("Invalid bet", show_alert=True)
        return

    user = await get_user(user_id)
    # TRUE ADMIN TEST MODE: allow all admins/owners to play with zero balance, always win, no deduction
    if is_admin(user_id):
        log_admin_action(user_id, f"Playing slots in test mode with ${bet} bet")
        symbols = ["💎", "💎", "💎"]
        multiplier = 100
        win_amount = bet * multiplier
        text = f"🎰 {' '.join(symbols)}\n\n🧪 <b>TEST MODE (ADMIN/OWNER)</b>\n🎉 <b>JACKPOT!</b> You won <b>${win_amount:,}</b> (x{multiplier})!\n\n💰 <b>Balance:</b> {await format_usd(user['balance'])}"
        keyboard = [
            [InlineKeyboardButton("🔄 Play Again", callback_data="play_slots"), InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return
    # DEMO MODE: allow all users to play with zero balance, always win, no deduction
    if DEMO_MODE and user['balance'] < bet:
        symbols = ["💎", "💎", "💎"]
        multiplier = 100
        win_amount = bet * multiplier
        text = f"🎰 {' '.join(symbols)}\n\n🧪 <b>DEMO MODE</b>\n🎉 <b>JACKPOT!</b> You won <b>${win_amount:,}</b> (x{multiplier})!\n\n💰 <b>Balance:</b> {await format_usd(user['balance'])}"
        keyboard = [
            [InlineKeyboardButton("🔄 Play Again", callback_data="play_slots"), InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return
    # Allow owner/admins to play even with zero balance
    if user['balance'] < bet and is_admin(user_id):
        log_admin_action(user_id, f"Playing slots with insufficient balance (admin override)")
        # Do NOT deduct balance for owner/admins, just proceed
        pass
    elif user['balance'] < bet:
        await query.edit_message_text(
            "❌ You have no funds to play. Please deposit to continue.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Deposit", callback_data="deposit")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
            ])
        )
        return
    else:
        result = await deduct_balance(user_id, bet)
        if result is False:
            await query.edit_message_text(
                "❌ You have no funds to play. Please deposit to continue.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Deposit", callback_data="deposit")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
                ])
            )
            return

    # Simple slots simulation
    symbols = ["🍒", "🍋", "🍊", "🔔", "💎"]
    reel = [random.choice(symbols) for _ in range(3)]

    if reel[0] == reel[1] == reel[2]:
        # Jackpot!
        multiplier = {"🍒": 10, "🍋": 20, "🍊": 30, "🔔": 50, "💎": 100}.get(reel[0], 10)
        win_amount = bet * multiplier
        await update_balance(user_id, win_amount)
        text = f"🎰 {' '.join(reel)}\n\n🎉 **JACKPOT!** You won **${win_amount:,}** (x{multiplier})!"
    else:
        text = f"🎰 {' '.join(reel)}\n\n😢 No match. You lost **${bet:,}**."

    user_after = await get_user(user_id)
    keyboard = [
        [InlineKeyboardButton("🔄 Play Again", callback_data="play_slots"), InlineKeyboardButton("🎮 Other Games", callback_data="classic_casino")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    text += f"\n\n💰 **Balance:** {await format_usd(user_after['balance'])}"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# Coin Flip Game
async def coin_flip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle coin flip game"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    # Remove balance check here; let user set up bet first
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
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
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
    # TRUE ADMIN TEST MODE: allow all admins/owners to play with zero balance, always win, no deduction
    if is_admin(user_id):
        log_admin_action(user_id, f"Playing coin flip in test mode with ${bet} bet")
        coin_result = choice
        win_amount = bet * 1.92
        text = f"🪙 <b>COIN FLIP RESULT</b> 🪙\n\n🧪 <b>TEST MODE (ADMIN/OWNER)</b>\n🎉 <b>YOU WIN!</b>\n\n{'🟡' if choice == 'heads' else '⚫'} Coin landed on <b>{choice.upper()}</b>\n{'🟡' if choice == 'heads' else '⚫'} You chose <b>{choice.upper()}</b>\n\n💰 Won: <b>${win_amount:.2f}</b>\n\n💰 <b>New Balance:</b> {await format_usd(user['balance'])}\n\nPlay again or try another game:"
        keyboard = [
            [InlineKeyboardButton("🔄 Flip Again", callback_data="coin_flip"), InlineKeyboardButton("🎮 Other Games", callback_data="inline_games")],
            [InlineKeyboardButton("🎰 Slots", callback_data="play_slots"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return
    # DEMO MODE: allow all users to play with zero balance, always win, no deduction
    if DEMO_MODE and user['balance'] < bet:
        coin_result = choice = "heads"
        win_amount = bet * 1.92
        text = f"🪙 <b>COIN FLIP RESULT</b> 🪙\n\n🧪 <b>DEMO MODE</b>\n🎉 <b>YOU WIN!</b>\n\n🟡 Coin landed on <b>HEADS</b>\n🟡 You chose <b>HEADS</b>\n\n💰 Won: <b>${win_amount:.2f}</b>\n\n💰 <b>New Balance:</b> {await format_usd(user['balance'])}\n\nPlay again or try another game:"
        keyboard = [
            [InlineKeyboardButton("🔄 Flip Again", callback_data="coin_flip"), InlineKeyboardButton("🎮 Other Games", callback_data="inline_games")],
            [InlineKeyboardButton("🎰 Slots", callback_data="play_slots"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return
    # Flip coin
    coin_result = random.choice(["heads", "tails"])
    coin_emoji = "🟡" if coin_result == "heads" else "⚫"
    choice_emoji = "🟡" if choice == "heads" else "⚫"
    
    if choice == coin_result:
        # Win - 1.92x payout (not 2x)
        win_amount = bet * 1.92
        await update_balance(user_id, win_amount)
        outcome = f"🎉 **YOU WIN!**\n\n{coin_emoji} Coin landed on **{coin_result.upper()}**\n{choice_emoji} You chose **{choice.upper()}**\n\n💰 Won: **${win_amount:.2f}**"
    else:
        outcome = f"😢 **YOU LOSE!**\n\n{coin_emoji} Coin landed on **{coin_result.upper()}**\n{choice_emoji} You chose **{choice.upper()}**\n\n💸 Lost: **${bet:,}**"
    
    user_after = await get_user(user_id)
    
    text = f"""
🪙 **COIN FLIP RESULT** 🪙

{outcome}

💰 **New Balance:** {await format_usd(user_after['balance'])}

Play again or try another game:
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Flip Again", callback_data="coin_flip"), InlineKeyboardButton("🎮 Other Games", callback_data="inline_games")],
        [InlineKeyboardButton("🎰 Slots", callback_data="play_slots"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Dice Prediction Game ---
async def play_dice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle dice prediction game"""
    query = update.callback_query
    await query.answer()
    user_id = query.effective_user.id
    user = await get_user(user_id)
    # Remove balance check here; let user set up bet first
    balance = await format_usd(user['balance'])
    text = (
        f"🎲 <b>DICE PREDICTION</b> 🎲\n\n"
        f"💰 <b>Your Balance:</b> {balance}\n\n"
        "Predict the outcome of a 6-sided dice roll.\n"
        "Choose your prediction below, then enter your bet amount in USD.\n\n"
        "<b>Payouts:</b>\n"
        "• Correct Number (1-6): 6x\n"
        "• Even/Odd: 2x\n"
        "• High (4-6)/Low (1-3): 2x\n"
    )
    keyboard = [
        [InlineKeyboardButton("1️⃣", callback_data="dice_predict_1"), InlineKeyboardButton("2️⃣", callback_data="dice_predict_2"), InlineKeyboardButton("3️⃣", callback_data="dice_predict_3")],
        [InlineKeyboardButton("4️⃣", callback_data="dice_predict_4"), InlineKeyboardButton("5️⃣", callback_data="dice_predict_5"), InlineKeyboardButton("6️⃣", callback_data="dice_predict_6")],
        [InlineKeyboardButton("Even", callback_data="dice_predict_even"), InlineKeyboardButton("Odd", callback_data="dice_predict_odd")],
        [InlineKeyboardButton("High (4-6)", callback_data="dice_predict_high"), InlineKeyboardButton("Low (1-3)", callback_data="dice_predict_low")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    context.user_data['dice_prediction'] = None
    context.user_data['dice_bet_stage'] = 'choose_prediction'

async def dice_prediction_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    prediction = data.replace("dice_predict_", "")
    context.user_data['dice_prediction'] = prediction
    context.user_data['dice_bet_stage'] = 'enter_bet'
    text = (
        f"🎲 <b>DICE PREDICTION</b> 🎲\n\n"
        f"You chose: <b>{prediction.title()}</b>\n\n"
        "Enter your bet amount in USD (e.g. 5):"
    )
    await query.edit_message_text(text, parse_mode=ParseMode.HTML)
    return 'dice_bet_amount'

async def dice_prediction_bet_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    try:
        bet_usd = float(update.message.text.strip())
        if bet_usd <= 0:
            await update.message.reply_text("❌ Invalid amount. Enter a positive USD amount:")
            return 'dice_bet_amount'
    except Exception:
        await update.message.reply_text("❌ Invalid amount. Enter a positive USD amount:")
        return 'dice_bet_amount'
    ltc_usd_rate = await get_ltc_usd_rate()
    bet_ltc = bet_usd / ltc_usd_rate if ltc_usd_rate > 0 else 0
    # TRUE ADMIN TEST MODE: allow all admins/owners to play with zero balance, always win, no deduction
    if is_admin(user_id):
        log_admin_action(user_id, f"Playing dice in test mode with ${bet_usd} bet")
        prediction = context.user_data.get('dice_prediction')
        roll = int(prediction) if prediction in [str(i) for i in range(1, 7)] else 2
        payout = bet_ltc * 6 if prediction in [str(i) for i in range(1, 7)] else bet_ltc * 2
        result_text = f"🧪 <b>TEST MODE (ADMIN/OWNER)</b>\n🎉 <b>You WON!</b>\nDice rolled: <b>{roll}</b>\nPayout: <b>${bet_usd * (payout / bet_ltc) if bet_ltc else bet_usd * 2:.2f}</b>"
        balance = await format_usd(user['balance'])
        text = (
            f"🎲 <b>DICE RESULT</b> 🎲\n\n"
            f"{result_text}\n\n"
            f"💰 <b>New Balance:</b> {balance}"
        )
        keyboard = [
            [InlineKeyboardButton("🔄 Play Again", callback_data="play_dice")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    # DEMO MODE: allow all users to play with zero balance, always win, no deduction
    if DEMO_MODE and user['balance'] < bet_ltc:
        prediction = context.user_data.get('dice_prediction')
        roll = 6 if prediction in [str(i) for i in range(1, 7)] else 2  # Always win
        payout = bet_ltc * 6 if prediction in [str(i) for i in range(1, 7)] else bet_ltc * 2
        result_text = f"🧪 <b>DEMO MODE</b>\n🎉 <b>You WON!</b>\nDice rolled: <b>{roll}</b>\nPayout: <b>${bet_usd * (payout / bet_ltc) if bet_ltc else bet_usd * 2:.2f}</b>"
        balance = await format_usd(user['balance'])
        text = (
            f"🎲 <b>DICE RESULT</b> 🎲\n\n"
            f"{result_text}\n\n"
            f"💰 <b>New Balance:</b> {balance}"
        )
        keyboard = [
            [InlineKeyboardButton("🔄 Play Again", callback_data="play_dice")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    # Roll the dice
    roll = random.randint(1, 6)
    user_bet = context.user_data.get('dice_prediction')
    
    # Calculate payout based on bet type
    if user_bet.isdigit() and 1 <= int(user_bet) <= 6:
        # User guessed a specific number
        if roll == int(user_bet):
            payout = bet_ltc * 6
            result_text = f"🎉 **YOU WIN!** Dice rolled: **{roll}** (x6)\nPayout: **${payout:.2f}**"
        else:
            payout = 0
            result_text = f"😢 You guessed {user_bet}, but dice rolled **{roll}**."
    else:
        # Even/Odd or High/Low bet
        if (user_bet == "even" and roll % 2 == 0) or (user_bet == "odd" and roll % 2 == 1):
            payout = bet_ltc * 2
            result_text = f"🎉 **YOU WIN!** Dice rolled: **{roll}** (Even/Odd)\nPayout: **${payout:.2f}**"
        elif (user_bet == "high" and roll >= 4) or (user_bet == "low" and roll <= 3):
            payout = bet_ltc * 2
            result_text = f"🎉 **YOU WIN!** Dice rolled: **{roll}** (High/Low)\nPayout: **${payout:.2f}**"
        else:
            payout = 0
            result_text = f"😢 Sorry, you lost. Dice rolled **{roll}**."
    
    # Update balance and show result
    if payout > 0:
        await update_balance(user_id, payout)
    
    user_after = await get_user(user_id)
    text = f"""
🎲 **DICE RESULT** 🎲

{result_text}

💰 **New Balance:** {await format_usd(user_after['balance'])}

Play again or try another game:
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Play Again", callback_data="play_dice"), InlineKeyboardButton("🎮 Other Games", callback_data="inline_games")],
        [InlineKeyboardButton("🎰 Slots", callback_data="play_slots"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Enhanced Deposit Amount Handler ---
async def deposit_crypto_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    asset = context.user_data.get('deposit_asset', 'LTC')
    asset_name = {"LTC": "Litecoin", "TON": "Toncoin", "SOL": "Solana"}.get(asset, asset)
    
    try:
        usd_amount = float(update.message.text.strip())
        if usd_amount < 0.50:
            await update.message.reply_text(
                f"❌ Minimum deposit is $0.50. Please enter a valid amount for {asset_name}:"
            )
            return DEPOSIT_LTC_AMOUNT
    except Exception:
        await update.message.reply_text(
            f"❌ Invalid amount. Please enter a valid USD amount (min $0.50) for {asset_name}:"
        )
        return DEPOSIT_LTC_AMOUNT
    
    try:
        # Get current rate for the selected asset
        asset_usd_rate = await get_crypto_usd_rate(asset)
        if asset_usd_rate == 0.0:
            await update.message.reply_text(
                f"❌ Unable to fetch {asset}/USD rate. Please try again later."
            )
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
            logger.error(f"Missing required env vars: {missing_env}")
            await update.message.reply_text(
                "❌ Deposit system misconfigured. Please contact support."
            )
            return ConversationHandler.END
        
        # Create invoice
        payload = {"hidden_message": str(user_id), "asset": asset}
        invoice = await create_crypto_invoice(asset, asset_amount, user_id, payload=payload)
        
        if invoice.get("ok"):
            result = invoice["result"]
            mini_app_url = result.get("mini_app_invoice_url")
            
            text = (
                f"✅ <b>{asset_name} Deposit Invoice Created!</b>\n\n"
                f"💰 <b>Amount:</b> ${usd_amount:.2f} USD\n"
                f"🪙 <b>Asset:</b> {asset_amount:.8f} {asset}\n"
                f"💱 <b>Rate:</b> 1 {asset} = ${asset_usd_rate:.2f}\n\n"
                f"<b>Tap the button below to pay instantly:</b>"
            )
            
            buttons = []
            if mini_app_url:
                buttons.append([InlineKeyboardButton(f"💸 Pay {asset_amount:.6f} {asset}", url=mini_app_url)])
            
            text += "\n\n<b>Your balance will update automatically after payment.</b>"
            await update.message.reply_text(
                text, 
                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None, 
                parse_mode=ParseMode.HTML
            )
        else:
            error_msg = invoice.get("error", "Unknown error")
            logger.error(f"CryptoBot API error for {asset}: {invoice}")
            await update.message.reply_text(
                f"❌ Failed to create {asset_name} invoice: {error_msg}\nPlease try again later."
            )
            
    except Exception as e:
        logger.error(f"Deposit error for {asset}: {e}")
        await update.message.reply_text(
            f"❌ {asset_name} deposit system temporarily unavailable. Please try again later."
        )
    
    return ConversationHandler.END

# --- Multi-Asset Withdrawal System ---
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
            date = w['created_at'][:10] if w['created_at'] else "Unknown"
            withdrawal_history += f"• {status_emoji} ${w['amount_usd']:.2f} - {date}\n"

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

# --- Multi-Asset Withdrawal Handlers ---
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

# --- Enhanced Withdrawal Amount Handler ---
async def withdraw_crypto_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    asset = context.user_data.get('withdraw_asset', 'LTC')
    asset_name = {"LTC": "Litecoin", "TON": "Toncoin", "SOL": "Solana"}.get(asset, asset)
    
    try:
        usd_amount = float(update.message.text.strip())
        # Validate minimum amount
        if usd_amount < MIN_WITHDRAWAL_USD:
            await update.message.reply_text(f"❌ Minimum withdrawal is ${MIN_WITHDRAWAL_USD:.2f}.")
            return WITHDRAW_LTC_AMOUNT
            
        # Check withdrawal limits
        limits_check = await check_withdrawal_limits(user_id, usd_amount)
        if not limits_check['allowed']:
            await update.message.reply_text(f"❌ {limits_check['reason']}")
            return WITHDRAW_LTC_AMOUNT
            
        # Convert USD to asset amount
        asset_usd_rate = await get_crypto_usd_rate(asset)
        if asset_usd_rate == 0.0:
            await update.message.reply_text(f"❌ Unable to fetch {asset}/USD rate. Please try again later.")
            return WITHDRAW_LTC_AMOUNT
            
        asset_amount = usd_amount / asset_usd_rate
        
        # Check if user has sufficient balance
        if user['balance'] < asset_amount:
            await update.message.reply_text(
                "❌ No funds to withdraw.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Deposit", callback_data="deposit")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
                ])
            )
            return WITHDRAW_LTC_AMOUNT
            
        # Calculate fees
        fee_asset = calculate_withdrawal_fee(asset_amount)
        fee_usd = fee_asset * asset_usd_rate
        net_asset = asset_amount - fee_asset
        net_usd = net_asset * asset_usd_rate
        
        # Validate that after fees, user still gets meaningful amount
        if net_asset <= 0:
            await update.message.reply_text("❌ Amount too small after fees. Please enter a larger amount.")
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

# --- Enhanced Withdrawal Address Handler ---
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
    
    # Basic address validation (you can enhance this for each asset)
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
        user_id, asset, asset_amount, address, fee_asset, net_amount
    )
    
    try:
        # Deduct full amount from balance (including fees)
        if not await deduct_balance(user_id, asset_amount):
            await update_withdrawal_status(withdrawal_id, 'failed', '', 'Failed to deduct balance')
            await update.message.reply_text("❌ Failed to process withdrawal. Please try again.")
            return ConversationHandler.END
        
        # Send crypto via CryptoBot (send net amount after fees)
        result = await send_crypto(address, net_amount, f"Withdrawal for user {user_id}", asset=asset)
        
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
                f"Please try again later or contact support."
            )
            logger.error(f"CryptoBot withdrawal failed for user {user_id}: {result}")
            
    except Exception as e:
        # Exception occurred - refund user
        await update_balance(user_id, asset_amount)  # Refund full amount
        await update_withdrawal_status(withdrawal_id, 'failed', '', str(e))
        
        await update.message.reply_text(
            f"❌ <b>{asset_name} Withdrawal Failed</b>\n\n"
            "Your balance has been refunded.\n"
            "Please try again later or contact support."
        )
        logger.error(f"Withdrawal exception for user {user_id}: {e}")
    
    return ConversationHandler.END

# --- Statistics Handler ---
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

# --- Enhanced Error Handling and Bot Improvements ---

# Add better error handling wrapper
def handle_errors(func):
    """Decorator for error handling in bot functions"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            # Try to send error message to user if update object is available
            if args and hasattr(args[0], 'effective_user'):
                try:
                    await args[0].message.reply_text("❌ An error occurred. Please try again later.")
                except:
                    pass
            return None
    return wrapper

@handle_errors
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

# Enhanced start command with better error handling
@handle_errors
async def enhanced_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start command with better error handling"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    try:
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
            status_text = "🔑 <b>ADMIN</b> • "
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
        if hasattr(update, 'callback_query') and update.callback_query:
            try:
                await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
            except Exception as e:
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("❌ Welcome! There was an issue loading your data. Please try again.")

# Enhanced admin panel
@handle_errors
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
        f"• Demo Mode: {'ON' if DEMO_MODE else 'OFF'}\n\n"
        f"🎮 <b>Admin Commands:</b>\n"
        f"• /admin - Check admin status\n"
        f"• /demo - Toggle demo mode\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎮 Toggle Demo Mode", callback_data="admin_toggle_demo")],
        [InlineKeyboardButton("📊 User Stats", callback_data="admin_user_stats")],
        [InlineKeyboardButton("💰 Balance Report", callback_data="admin_balance_report")],
        [InlineKeyboardButton("📈 Game Statistics", callback_data="owner_game_stats")],
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="owner_refresh_stats")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

@handle_errors
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

# --- Owner Panel Functions ---
@handle_errors
async def owner_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner panel with full administrative features"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        await query.answer("❌ Access denied. Owner only.", show_alert=True)
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
👑 **OWNER CONTROL PANEL** 👑

📊 **System Statistics:**
• Total Users: {total_users:,}
• Total Balance: {total_balance_usd}
• Total Wagered: {total_wagered_usd}
• Total Games: {total_games:,}
• Demo Mode: {'ON' if DEMO_MODE else 'OFF'}

💰 **Today's Activity:**
• Withdrawals: {withdrawals_today} (${withdrawal_amount_today:.2f})

🎮 **Bot Version:** {BOT_VERSION}
🔧 **Admin Users:** {len(ADMIN_USER_IDS)}
"""
    
    keyboard = [
        [InlineKeyboardButton("📊 Detailed Stats", callback_data="owner_detailed_stats")],
        [InlineKeyboardButton("👥 User Management", callback_data="owner_user_mgmt")],
        [InlineKeyboardButton("💰 Financial Report", callback_data="owner_financial")],
        [InlineKeyboardButton("🎮 Toggle Demo Mode", callback_data="admin_toggle_demo")],
        [InlineKeyboardButton("⚙️ System Health", callback_data="owner_system_health")],
        [InlineKeyboardButton("🔄 Refresh Data", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def owner_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed statistics"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        await query.answer("❌ Access denied.", show_alert=True)
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Game statistics
        cursor = await db.execute("""
            SELECT game_type, COUNT(*), SUM(bet_amount), SUM(win_amount)
            FROM game_sessions
            GROUP BY game_type
        """)
        game_stats = await cursor.fetchall()
        
        # Top users by wagering
        cursor = await db.execute("""
            SELECT username, total_wagered, games_played, balance
            FROM users
            ORDER BY total_wagered DESC
            LIMIT 5
        """)
        top_users = await cursor.fetchall()
    
    stats_text = "📈 **DETAILED STATISTICS** 📈\n\n"
    
    if game_stats:
        stats_text += "🎮 **Game Performance:**\n"
        for game, count, total_bet, total_win in game_stats:
            rtp = (total_win / total_bet * 100) if total_bet > 0 else 0
            stats_text += f"• {game}: {count} games, RTP: {rtp:.1f}%\n"
    
    if top_users:
        stats_text += "\n👑 **Top Players:**\n"
        for i, (username, wagered, games, balance) in enumerate(top_users, 1):
            wagered_usd = await format_usd(wagered)
            stats_text += f"{i}. {username}: {wagered_usd} wagered\n"
    
    keyboard = [
        [InlineKeyboardButton("👑 Back to Owner Panel", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Missing Command Handlers ---
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
• 🃏 Blackjack - Beat the dealer
• 🎡 Roulette - Red or black

**Features:**
• Multi-asset deposits (LTC, TON, SOL)
• Instant withdrawals
• Demo mode for testing
• Fair random results

**Support:**
Contact @casino_support for help
"""
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help callback"""
    await help_command(update, context)

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

# --- Owner Panel Functions ---
async def owner_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner panel with full administrative features"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        await query.answer("❌ Access denied. Owner only.", show_alert=True)
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
👑 **OWNER CONTROL PANEL** 👑

📊 **System Statistics:**
• Total Users: {total_users:,}
• Total Balance: {total_balance_usd}
• Total Wagered: {total_wagered_usd}
• Total Games: {total_games:,}
• Demo Mode: {'ON' if DEMO_MODE else 'OFF'}

💰 **Today's Activity:**
• Withdrawals: {withdrawals_today} (${withdrawal_amount_today:.2f})

🎮 **Bot Version:** {BOT_VERSION}
🔧 **Admin Users:** {len(ADMIN_USER_IDS)}
"""
    
    keyboard = [
        [InlineKeyboardButton("📊 Detailed Stats", callback_data="owner_detailed_stats")],
        [InlineKeyboardButton("👥 User Management", callback_data="owner_user_mgmt")],
        [InlineKeyboardButton("💰 Financial Report", callback_data="owner_financial")],
        [InlineKeyboardButton("🎮 Toggle Demo Mode", callback_data="admin_toggle_demo")],
        [InlineKeyboardButton("⚙️ System Health", callback_data="owner_system_health")],
        [InlineKeyboardButton("🔄 Refresh Data", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def owner_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed statistics"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        await query.answer("❌ Access denied.", show_alert=True)
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Game statistics
        cursor = await db.execute("""
            SELECT game_type, COUNT(*), SUM(bet_amount), SUM(win_amount)
            FROM game_sessions
            GROUP BY game_type
        """)
        game_stats = await cursor.fetchall()
        
        # Top users by wagering
        cursor = await db.execute("""
            SELECT username, total_wagered, games_played, balance
            FROM users
            ORDER BY total_wagered DESC
            LIMIT 5
        """)
        top_users = await cursor.fetchall()
    
    stats_text = "📈 **DETAILED STATISTICS** 📈\n\n"
    
    if game_stats:
        stats_text += "🎮 **Game Performance:**\n"
        for game, count, total_bet, total_win in game_stats:
            rtp = (total_win / total_bet * 100) if total_bet > 0 else 0
            stats_text += f"• {game}: {count} games, RTP: {rtp:.1f}%\n"
    
    if top_users:
        stats_text += "\n👑 **Top Players:**\n"
        for i, (username, wagered, games, balance) in enumerate(top_users, 1):
            wagered_usd = await format_usd(wagered)
            stats_text += f"{i}. {username}: {wagered_usd} wagered\n"
    
    keyboard = [
        [InlineKeyboardButton("👑 Back to Owner Panel", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Missing Command Handlers ---
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
• 🃏 Blackjack - Beat the dealer
• 🎡 Roulette - Red or black

**Features:**
• Multi-asset deposits (LTC, TON, SOL)
• Instant withdrawals
• Demo mode for testing
• Fair random results

**Support:**
Contact @casino_support for help
"""
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help callback"""
    await help_command(update, context)

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

# --- Owner Panel Functions ---
async def owner_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner panel with full administrative features"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        await query.answer("❌ Access denied. Owner only.", show_alert=True)
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
👑 **OWNER CONTROL PANEL** 👑

📊 **System Statistics:**
• Total Users: {total_users:,}
• Total Balance: {total_balance_usd}
• Total Wagered: {total_wagered_usd}
• Total Games: {total_games:,}
• Demo Mode: {'ON' if DEMO_MODE else 'OFF'}

💰 **Today's Activity:**
• Withdrawals: {withdrawals_today} (${withdrawal_amount_today:.2f})

🎮 **Bot Version:** {BOT_VERSION}
🔧 **Admin Users:** {len(ADMIN_USER_IDS)}
"""
    
    keyboard = [
        [InlineKeyboardButton("📊 Detailed Stats", callback_data="owner_detailed_stats")],
        [InlineKeyboardButton("👥 User Management", callback_data="owner_user_mgmt")],
        [InlineKeyboardButton("💰 Financial Report", callback_data="owner_financial")],
        [InlineKeyboardButton("🎮 Toggle Demo Mode", callback_data="admin_toggle_demo")],
        [InlineKeyboardButton("⚙️ System Health", callback_data="owner_system_health")],
        [InlineKeyboardButton("🔄 Refresh Data", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def owner_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed statistics"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        await query.answer("❌ Access denied.", show_alert=True)
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Game statistics
        cursor = await db.execute("""
            SELECT game_type, COUNT(*), SUM(bet_amount), SUM(win_amount)
            FROM game_sessions
            GROUP BY game_type
        """)
        game_stats = await cursor.fetchall()
        
        # Top users by wagering
        cursor = await db.execute("""
            SELECT username, total_wagered, games_played, balance
            FROM users
            ORDER BY total_wagered DESC
            LIMIT 5
        """)
        top_users = await cursor.fetchall()
    
    stats_text = "📈 **DETAILED STATISTICS** 📈\n\n"
    
    if game_stats:
        stats_text += "🎮 **Game Performance:**\n"
        for game, count, total_bet, total_win in game_stats:
            rtp = (total_win / total_bet * 100) if total_bet > 0 else 0
            stats_text += f"• {game}: {count} games, RTP: {rtp:.1f}%\n"
    
    if top_users:
        stats_text += "\n👑 **Top Players:**\n"
        for i, (username, wagered, games, balance) in enumerate(top_users, 1):
            wagered_usd = await format_usd(wagered)
            stats_text += f"{i}. {username}: {wagered_usd} wagered\n"
    
    keyboard = [
        [InlineKeyboardButton("👑 Back to Owner Panel", callback_data="owner_panel")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Missing Callback Handlers ---
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

# --- Async Main Entry Point ---
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
    application.add_handler(CallbackQueryHandler(dice_prediction_choose, pattern="^dice_predict_"))
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw$"))
    application.add_handler(CallbackQueryHandler(withdraw_crypto_ltc, pattern="^withdraw_crypto_ltc$"))
    application.add_handler(CallbackQueryHandler(withdraw_crypto_ton, pattern="^withdraw_crypto_ton$"))
    application.add_handler(CallbackQueryHandler(withdraw_crypto_sol, pattern="^withdraw_crypto_sol$"))
    application.add_handler(CallbackQueryHandler(start_command, pattern="^main_panel$"))
    application.add_handler(CallbackQueryHandler(redeem_panel_callback, pattern="^redeem_panel$"))
    application.add_handler(CallbackQueryHandler(show_help, pattern="^show_help$"))
    
    # Deposit handlers
    application.add_handler(CallbackQueryHandler(deposit_crypto_ltc, pattern="^deposit_crypto_ltc$"))
    application.add_handler(CallbackQueryHandler(deposit_crypto_ton, pattern="^deposit_crypto_ton$"))
    application.add_handler(CallbackQueryHandler(deposit_crypto_sol, pattern="^deposit_crypto_sol$"))
    
    # Admin/Owner handlers
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_toggle_demo_callback, pattern="^admin_toggle_demo$"))
    application.add_handler(CallbackQueryHandler(owner_panel_callback, pattern="^owner_panel$"))
    application.add_handler(CallbackQueryHandler(owner_detailed_stats, pattern="^owner_detailed_stats$"))
    
    # Conversation handlers for deposit/withdrawal
    deposit_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(deposit_callback, pattern="^deposit$")],
        states={
            DEPOSIT_LTC_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_crypto_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    application.add_handler(deposit_conv_handler)
    
    withdraw_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(withdraw_crypto_ltc, pattern="^withdraw_crypto_ltc$"),
            CallbackQueryHandler(withdraw_crypto_ton, pattern="^withdraw_crypto_ton$"),
            CallbackQueryHandler(withdraw_crypto_sol, pattern="^withdraw_crypto_sol$"),
        ],
        states={
            WITHDRAW_LTC_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_crypto_amount)],
            WITHDRAW_LTC_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_crypto_address)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    application.add_handler(withdraw_conv_handler)
    
    dice_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(dice_prediction_choose, pattern="^dice_predict_")],
        states={
            'dice_bet_amount': [MessageHandler(filters.TEXT & ~filters.COMMAND, dice_prediction_bet_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    application.add_handler(dice_conv_handler)
    
    # Catch-all callback handler for unhandled callbacks
    application.add_handler(CallbackQueryHandler(default_callback_handler))
    
    logger.info("✅ All handlers registered")
    logger.info(f"🎰 Casino Bot v{BOT_VERSION} is ready!")
    logger.info(f"🔧 Admin users: {ADMIN_USER_IDS}")
    logger.info(f"👑 Owner user: {OWNER_USER_ID}")
    logger.info(f"🧪 Demo mode: {'ON' if DEMO_MODE else 'OFF'}")
    
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
            
        # Start server
        serve(app, host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
    
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
    import nest_asyncio
    import logging
    
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
        
        # Run the bot
        logger.info("Starting bot...")
        asyncio.run(async_main())
        
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        import sys
        sys.exit(1)
