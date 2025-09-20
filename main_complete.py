# --- Complete Casino Bot with CryptoBot Integration ---

import os
import logging
import sqlite3
import asyncio
import aiohttp
import hmac
import hashlib
import time
import random
import uuid
import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Telegram imports
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    WebApp, 
    BotCommand,
    MenuButtonWebApp
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

# Flask for webhooks
from flask import Flask, request
import nest_asyncio

# Enable nested event loops
nest_asyncio.apply()

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Environment Configuration ---
BOT_TOKEN = os.getenv('BOT_TOKEN', 'your_bot_token_here')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://your-domain.com/casino_webapp_new.html')

# CryptoBot Configuration
CRYPTOBOT_API_TOKEN = os.getenv('CRYPTOBOT_API_TOKEN', 'your_cryptobot_token')
CRYPTOBOT_WEBHOOK_SECRET = os.getenv('CRYPTOBOT_WEBHOOK_SECRET', 'your_webhook_secret')
CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"

# Webhook Configuration
WEBHOOK_ENABLED = os.getenv('WEBHOOK_ENABLED', 'true').lower() == 'true'
WEBHOOK_PORT = os.getenv('WEBHOOK_PORT', '5000')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://your-domain.com/webhook/cryptobot')
SUCCESS_URL = os.getenv('SUCCESS_URL', 'https://your-domain.com/payment_success')

# USD Minimum Deposits
MIN_DEPOSIT_LTC_USD = float(os.getenv('MIN_DEPOSIT_LTC_USD', '5.00'))
MIN_DEPOSIT_TON_USD = float(os.getenv('MIN_DEPOSIT_TON_USD', '2.00'))
MIN_DEPOSIT_SOL_USD = float(os.getenv('MIN_DEPOSIT_SOL_USD', '3.00'))
MIN_DEPOSIT_USDT_USD = float(os.getenv('MIN_DEPOSIT_USDT_USD', '1.00'))

# Exchange rates (simplified - in production, fetch from API)
LTC_USD_RATE = float(os.getenv('LTC_USD_RATE', '75.0'))
TON_USD_RATE = float(os.getenv('TON_USD_RATE', '2.5'))
SOL_USD_RATE = float(os.getenv('SOL_USD_RATE', '20.0'))
USDT_USD_RATE = float(os.getenv('USDT_USD_RATE', '1.0'))

# Database
DB_PATH = os.getenv('DB_PATH', 'casino.db')

# Check if WebApp is available
try:
    from telegram import WebApp
    WEBAPP_IMPORTS_AVAILABLE = True
except ImportError:
    WEBAPP_IMPORTS_AVAILABLE = False
    logger.warning("WebApp imports not available")

# --- Database Functions ---
async def init_db():
    """Initialize the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            vip_level TEXT DEFAULT 'Standard',
            total_wagered REAL DEFAULT 0.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_bonus_claim TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ Database initialized")

async def get_user(user_id: int) -> dict:
    """Get user data from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute('''
            INSERT INTO users (id, balance, vip_level, total_wagered, created_at) 
            VALUES (?, 0.0, 'Standard', 0.0, datetime('now'))
        ''', (user_id,))
        conn.commit()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
    
    conn.close()
    
    return {
        'id': user[0],
        'balance': user[1],
        'vip_level': user[2],
        'total_wagered': user[3],
        'created_at': user[4],
        'last_bonus_claim': user[5]
    }

# --- Helper Functions ---
def get_performance_rating(user: dict) -> str:
    """Get user performance rating"""
    balance = user.get('balance', 0)
    if balance >= 1000:
        return "💎 Excellent"
    elif balance >= 500:
        return "🥇 Great"
    elif balance >= 100:
        return "🥈 Good"
    else:
        return "🥉 Starting"

def get_vip_level(balance: float) -> str:
    """Determine VIP level based on balance or wagered amount"""
    if balance >= 5000:
        return "Diamond"
    elif balance >= 1000:
        return "Gold"
    elif balance >= 500:
        return "Silver"
    elif balance >= 100:
        return "Bronze"
    else:
        return "Standard"

def get_daily_bonus_amount(vip_level: str) -> float:
    """Get daily bonus amount based on VIP level"""
    bonus_amounts = {
        "Standard": 5.00,
        "Bronze": 7.50,
        "Silver": 10.00,
        "Gold": 15.00,
        "Diamond": 25.00
    }
    return bonus_amounts.get(vip_level, 5.00)

def get_vip_multiplier(vip_level: str) -> float:
    """Get VIP multiplier for winnings"""
    multipliers = {
        "Standard": 1.0,
        "Bronze": 1.1,
        "Silver": 1.2,
        "Gold": 1.3,
        "Diamond": 1.5
    }
    return multipliers.get(vip_level, 1.0)

def can_claim_weekly_bonus(user_id: int) -> bool:
    """Check if user can claim weekly bonus"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT last_bonus_claim FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return True
            
        # Check if a day has passed (simplified for demo)
        last_claim = datetime.fromisoformat(result[0])
        now = datetime.now()
        return (now - last_claim).days >= 1
        
    except Exception as e:
        logger.error(f"Error checking bonus eligibility: {e}")
        return False

# --- CryptoBot API Functions ---
async def get_crypto_usd_rate(asset: str) -> float:
    """Get crypto to USD rate (simplified)"""
    rates = {
        'LTC': LTC_USD_RATE,
        'TON': TON_USD_RATE,
        'SOL': SOL_USD_RATE,
        'USDT': USDT_USD_RATE
    }
    return rates.get(asset, 1.0)

async def create_crypto_invoice(asset: str, amount: float, user_id: int) -> dict:
    """Create CryptoBot invoice"""
    try:
        payload = {
            'asset': asset,
            'amount': f"{amount:.8f}",
            'description': f'Casino Deposit - {asset}',
            'hidden_message': str(user_id),
            'paid_btn_name': 'callback',
            'paid_btn_url': SUCCESS_URL,
            'payload': f'deposit_{user_id}_{asset}_{amount}',
            'allow_comments': False,
            'allow_anonymous': False,
            'expires_in': 3600  # 1 hour
        }
        
        headers = {
            'Crypto-Pay-API-Token': CRYPTOBOT_API_TOKEN,
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{CRYPTOBOT_API_URL}/createInvoice",
                json=payload,
                headers=headers
            ) as response:
                result = await response.json()
                logger.info(f"CryptoBot invoice response: {result}")
                return result
                
    except Exception as e:
        logger.error(f"Error creating CryptoBot invoice: {e}")
        return {'ok': False, 'error': str(e)}

# --- Bot Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    welcome_text = f"""
🎲 **WELCOME TO CASINO AXIS** 🎲

Hello {update.effective_user.first_name}! 

💰 **Your Balance:** ${user['balance']:.2f} USD
🎯 **VIP Status:** {user['vip_level']}

🚀 **Ready to play?** Choose an option below:

🎮 **Mini App Centre** - Launch our casino games
💳 **Account** - Manage your funds & profile  
🎁 **Bonus** - Claim your daily rewards

✨ **New Player?** Get $10 free bonus!
"""
    
    keyboard = [
        [InlineKeyboardButton("🎮 Mini App Centre", callback_data="mini_app_centre")],
        [InlineKeyboardButton("💳 Account", callback_data="account"),
         InlineKeyboardButton("🎁 Bonus", callback_data="bonus")],
        [InlineKeyboardButton("🏆 VIP Club", callback_data="vip"),
         InlineKeyboardButton("📞 Support", callback_data="support")]
    ]
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def main_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main panel"""
    await start_command(update, context)

# --- Mini App Centre Handler ---
async def mini_app_centre_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show mini app centre with available games"""
    text = """
🎮 **MINI APP CENTRE**

🎯 **Available Games:**
• 🎰 Slots, Roulette, Blackjack
• 🎲 Dice, Crash, Limbo
• 💎 Mines, Plinko, Hi-Lo
• 🃏 Poker and more!

✨ **Features:**
• Native Telegram integration
• Instant play (no downloads)
• Real-time gameplay
• Secure transactions
• Mobile optimized

🚀 **Ready to play? Click below!**
"""
    
    keyboard = [
        [InlineKeyboardButton("🎮 Launch Casino", web_app=WebApp(url=WEBAPP_URL))],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Account Handlers ---
async def account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show account information"""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    text = f"""
👤 **ACCOUNT OVERVIEW**

💰 **Balance:** ${user['balance']:.2f} USD
🆔 **User ID:** `{user_id}`
🎯 **VIP Level:** {user.get('vip_level', 'Standard')}
📅 **Member Since:** {user.get('created_at', 'Today')}

💎 **Weekly Bonus Available:** {'✅ Yes' if can_claim_weekly_bonus(user_id) else '❌ Already Claimed'}
"""
    
    keyboard = [
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit"),
         InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🎁 Claim Bonus", callback_data="bonus"),
         InlineKeyboardButton("👑 VIP Status", callback_data="vip")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile"""
    await account_callback(update, context)

# --- Deposit Handlers ---
async def deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show deposit options"""
    text = """
💳 **DEPOSIT FUNDS**

🚀 **Instant Crypto Deposits**
• ⚡ Lightning fast processing
• 🔒 Secure CryptoBot integration
• 💫 Native Telegram payments
• 🎁 No fees on deposits

💰 **Available Assets:**
"""
    
    keyboard = [
        [InlineKeyboardButton(f"🟡 Litecoin (LTC) - Min ${MIN_DEPOSIT_LTC_USD:.2f}", callback_data="deposit_ltc")],
        [InlineKeyboardButton(f"🔵 Toncoin (TON) - Min ${MIN_DEPOSIT_TON_USD:.2f}", callback_data="deposit_ton")],
        [InlineKeyboardButton(f"🟣 Solana (SOL) - Min ${MIN_DEPOSIT_SOL_USD:.2f}", callback_data="deposit_sol")],
        [InlineKeyboardButton(f"🟢 USDT - Min ${MIN_DEPOSIT_USDT_USD:.2f}", callback_data="deposit_usdt")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Crypto Deposit Handlers ---
async def deposit_ltc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle LTC deposit"""
    context.user_data['deposit_asset'] = 'LTC'
    await show_deposit_amount_prompt(update, 'LTC', MIN_DEPOSIT_LTC_USD)
    return 1  # DEPOSIT_AMOUNT state

async def deposit_ton_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle TON deposit"""
    context.user_data['deposit_asset'] = 'TON'
    await show_deposit_amount_prompt(update, 'TON', MIN_DEPOSIT_TON_USD)
    return 1  # DEPOSIT_AMOUNT state

async def deposit_sol_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle SOL deposit"""
    context.user_data['deposit_asset'] = 'SOL'
    await show_deposit_amount_prompt(update, 'SOL', MIN_DEPOSIT_SOL_USD)
    return 1  # DEPOSIT_AMOUNT state

async def deposit_usdt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle USDT deposit"""
    context.user_data['deposit_asset'] = 'USDT'
    await show_deposit_amount_prompt(update, 'USDT', MIN_DEPOSIT_USDT_USD)
    return 1  # DEPOSIT_AMOUNT state

async def show_deposit_amount_prompt(update: Update, asset: str, min_usd: float):
    """Show deposit amount input prompt"""
    text = f"""
💳 **{asset} DEPOSIT**

💰 **Enter USD Amount**

✅ **Minimum:** ${min_usd:.2f} USD
⚡ **Processing:** Instant via CryptoBot
🔒 **Security:** Bank-level encryption

💡 **Example:** Type `10` for $10.00 USD

📝 **Please enter the amount in USD:**
"""
    
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="deposit")]]
    
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Payment Processing ---
async def process_crypto_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process crypto deposit amount and create CryptoBot payment"""
    user_id = update.effective_user.id
    asset = context.user_data.get('deposit_asset')
    amount_text = update.message.text.strip()
    
    try:
        usd_amount = float(amount_text)
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid USD amount.")
        return 1
    
    # Get minimum amounts
    min_amounts = {
        'LTC': MIN_DEPOSIT_LTC_USD,
        'TON': MIN_DEPOSIT_TON_USD,
        'SOL': MIN_DEPOSIT_SOL_USD,
        'USDT': MIN_DEPOSIT_USDT_USD
    }
    
    min_usd = min_amounts.get(asset, 1.00)
    if usd_amount < min_usd:
        await update.message.reply_text(f"❌ Minimum deposit for {asset} is ${min_usd:.2f} USD. Please enter a higher amount.")
        return 1
    
    # Show processing message
    processing_msg = await update.message.reply_text("⏳ Creating your CryptoBot payment...")
    
    # Convert USD to crypto amount
    crypto_rate = await get_crypto_usd_rate(asset)
    crypto_amount = usd_amount / crypto_rate if crypto_rate > 0 else 0
    
    if crypto_amount <= 0:
        await processing_msg.edit_text("❌ Unable to get exchange rate. Please try again later.")
        return ConversationHandler.END
    
    # Create invoice with CryptoBot
    invoice_result = await create_crypto_invoice(asset, crypto_amount, user_id)
    if invoice_result.get('ok'):
        result = invoice_result['result']
        pay_url = result.get('pay_url')
        mini_app_invoice_url = result.get('mini_app_invoice_url')
        invoice_id = result.get('invoice_id')
        
        # Create buttons with native CryptoBot mini app integration
        keyboard = []
        
        # Try to use CryptoBot mini app if available
        if mini_app_invoice_url and WEBAPP_IMPORTS_AVAILABLE:
            try:
                crypto_webapp = WebApp(url=mini_app_invoice_url)
                keyboard.append([InlineKeyboardButton("💳 Pay with CryptoBot", web_app=crypto_webapp)])
                logger.info("✅ CryptoBot mini app button created")
            except Exception as e:
                logger.error(f"❌ Error creating CryptoBot mini app button: {e}")
                keyboard.append([InlineKeyboardButton("💳 Pay with CryptoBot", url=pay_url)])
        else:
            keyboard.append([InlineKeyboardButton("💳 Pay with CryptoBot", url=pay_url)])
        
        keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")])
        
        text = f"""
💳 **{asset} PAYMENT READY** 💳

💰 **Amount:** ${usd_amount:.2f} USD ({crypto_amount:.8f} {asset})
🆔 **Invoice ID:** `{invoice_id}`

💫 **Native CryptoBot Integration**
• Payment processed within Telegram
• No external apps needed
• Instant balance updates
• Secure & encrypted

⚡ **Payment Instructions:**
1. Click "Pay with CryptoBot" below
2. Complete payment in the mini app
3. Return to this chat automatically
4. Your balance updates instantly

⏰ **Payment expires in 60 minutes**

🚀 **Ready to pay? Click the button below!**
"""
        
        await processing_msg.edit_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode=ParseMode.MARKDOWN, 
            disable_web_page_preview=True
        )
    else:
        error_msg = invoice_result.get('error', 'Unknown error')
        await processing_msg.edit_text(f"❌ Error creating payment: {error_msg}\n\nPlease try again or contact support.")
    
    return ConversationHandler.END

# --- Withdraw Handler ---
async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show withdraw options"""
    text = """
💸 **WITHDRAW FUNDS**

🚧 **Coming Soon!**

⚡ **What to expect:**
• Instant crypto withdrawals
• Multiple asset support
• Low fees
• Secure processing

🔔 **We'll notify you when withdrawals are available!**

💡 **For now, enjoy our games and earn more!**
"""
    
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]]
    
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Bonus Handlers ---
async def bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bonus options"""
    await claim_weekly_bonus_callback(update, context)

async def claim_weekly_bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle weekly bonus claim"""
    user_id = update.effective_user.id
    
    if can_claim_weekly_bonus(user_id):
        bonus_amount = 10.00
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users 
                SET balance = balance + ?, 
                    last_bonus_claim = datetime('now')
                WHERE id = ?
            """, (bonus_amount, user_id))
            
            conn.commit()
            conn.close()
            
            text = f"""
🎁 **WEEKLY BONUS CLAIMED!**

💰 **Bonus Amount:** ${bonus_amount:.2f} USD
✅ **Added to your balance**

🎯 **Next bonus available in 7 days**

🚀 **Use your bonus to play games!**
"""
            
            keyboard = [
                [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
            ]
            
        except Exception as e:
            logger.error(f"Error claiming bonus: {e}")
            text = "❌ Error claiming bonus. Please try again later."
            keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]]
    else:
        text = """
⏰ **WEEKLY BONUS NOT AVAILABLE**

🎁 **Bonus Status:** Already claimed this week
📅 **Next Available:** In a few days

💡 **Tip:** Bonuses reset every Monday!

🎮 **Meanwhile, enjoy our games!**
"""
        
        keyboard = [
            [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
    
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def check_bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check bonus status"""
    user_id = update.effective_user.id
    eligible = can_claim_weekly_bonus(user_id)
    
    if eligible:
        text = """
🎁 **WEEKLY BONUS AVAILABLE!**

💰 **Amount:** $10.00 USD
⏰ **Status:** Ready to claim
🎯 **Action:** Click "Claim Bonus" below

✨ **Bonus resets every Monday**
"""
        
        keyboard = [
            [InlineKeyboardButton("🎁 Claim Bonus", callback_data="claim_weekly_bonus")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
    else:
        text = """
⏰ **WEEKLY BONUS STATUS**

💰 **Amount:** $10.00 USD  
⏰ **Status:** Already claimed
🗓️ **Next Available:** Monday

🎮 **Keep playing to earn more!**
"""
        
        keyboard = [
            [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
    
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def claim_daily_bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle daily bonus claim (redirects to weekly bonus for now)"""
    await claim_weekly_bonus_callback(update, context)

async def bonus_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bonus actions"""
    await claim_weekly_bonus_callback(update, context)

# --- VIP Handlers ---
async def vip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show VIP information"""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    vip_level = user.get('vip_level', 'Standard')
    
    text = f"""
👑 **VIP STATUS**

🌟 **Current Level:** {vip_level}
💎 **Total Wagered:** ${user.get('total_wagered', 0):.2f}
🎁 **VIP Benefits Available:** {'✅ Yes' if vip_level != 'Standard' else '❌ Upgrade Required'}

🔥 **VIP Levels:**
• 🥉 **Bronze:** $100+ wagered
• 🥈 **Silver:** $500+ wagered  
• 🥇 **Gold:** $1,000+ wagered
• 💎 **Diamond:** $5,000+ wagered

⭐ **Exclusive Benefits:**
• Higher betting limits
• Exclusive games access
• Priority support
• Special bonuses
• Faster withdrawals
"""
    
    keyboard = [
        [InlineKeyboardButton("🎁 VIP Benefits", callback_data="vip_benefits")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def vip_benefits_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show VIP benefits details"""
    text = """
💎 **VIP BENEFITS BREAKDOWN**

🥉 **Bronze VIP:**
• 5% bonus on deposits
• Extended support hours
• Access to Bronze tournaments

🥈 **Silver VIP:**
• 10% bonus on deposits
• Priority customer support
• Weekly cashback: 2%
• Access to Silver tournaments

🥇 **Gold VIP:**
• 15% bonus on deposits
• Dedicated VIP manager
• Weekly cashback: 5%
• Monthly bonus: $50
• Access to Gold tournaments

💎 **Diamond VIP:**
• 25% bonus on deposits
• Personal account manager
• Weekly cashback: 10%
• Monthly bonus: $200
• Exclusive Diamond games
• Priority withdrawals (1 hour)
"""
    
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]]
    
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Support Handler ---
async def support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show support information"""
    text = """
🎯 **SUPPORT CENTER**

📞 **Contact Options:**
• 💬 Live Chat: @CasinoSupport
• 📧 Email: support@example.com
• 🆔 Telegram: Available 24/7

❓ **Common Questions:**
• How to deposit? Use /start → Deposit
• Withdrawal issues? Contact support
• Game questions? Check game rules
• VIP upgrades? Play more games!

🛡️ **Security:**
• We use bank-level encryption
• Funds are secured with CryptoBot
• Fair gaming guaranteed

⚡ **Response Time:** Usually within 1 hour
"""
    
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]]
    
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Game Handlers (Placeholders) ---
async def casino_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Navigate to casino/games section"""
    await mini_app_centre_callback(update, context)

async def blackjack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Blackjack game handler"""
    await show_coming_soon(update, "🃏 Blackjack")

async def roulette_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Roulette game handler"""
    await show_coming_soon(update, "🎰 Roulette")

async def slots_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Slots game handler"""
    await show_coming_soon(update, "🎰 Slots")

async def dice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dice game handler"""
    await show_coming_soon(update, "🎲 Dice")

async def poker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Poker game handler"""
    await show_coming_soon(update, "🃏 Poker")

async def show_coming_soon(update: Update, game_name: str):
    """Show coming soon message for games"""
    text = f"""
🚧 **{game_name} - COMING SOON!** 🚧

🎮 This exciting game is currently under development.

✨ **What to expect:**
• Professional game mechanics
• Fair random outcomes
• Real-time multiplayer (where applicable)
• Progressive jackpots
• Stunning graphics

🔔 **Stay tuned!** We'll notify you when it's ready.

🎯 **For now, try our Mini App Centre!**
"""
    
    keyboard = [
        [InlineKeyboardButton("🎮 Mini App Centre", callback_data="mini_app_centre")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Generic Callback Handler ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unrecognized callbacks"""
    query = update.callback_query
    await query.answer("🚧 Feature coming soon!", show_alert=True)

# --- Conversation Handler Setup ---
DEPOSIT_AMOUNT = 1

deposit_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(deposit_ltc_callback, pattern="^deposit_ltc$"),
        CallbackQueryHandler(deposit_ton_callback, pattern="^deposit_ton$"),
        CallbackQueryHandler(deposit_sol_callback, pattern="^deposit_sol$"),
        CallbackQueryHandler(deposit_usdt_callback, pattern="^deposit_usdt$"),
    ],
    states={
        DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_crypto_deposit)],
    },
    fallbacks=[
        CommandHandler('cancel', lambda u, c: ConversationHandler.END),
        CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^deposit$"),
        CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^main_panel$")
    ],
)

# --- CryptoBot Webhook Server ---
async def setup_cryptobot_webhook_server():
    """Setup Flask server for CryptoBot webhooks"""
    app = Flask(__name__)
    
    @app.route('/webhook/cryptobot', methods=['POST'])
    def cryptobot_webhook():
        try:
            data = request.get_json()
            logger.info(f"CryptoBot webhook received: {data}")
            
            # Verify webhook signature if available
            signature = request.headers.get('Crypto-Pay-Signature')
            if signature and CRYPTOBOT_WEBHOOK_SECRET:
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
                            rates = {
                                'LTC': LTC_USD_RATE,
                                'TON': TON_USD_RATE,
                                'SOL': SOL_USD_RATE,
                                'USDT': USDT_USD_RATE
                            }
                            rate = rates.get(asset, 1.0)
                            usd_amount = amount * rate
                        
                        # Update user balance synchronously
                        try:
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            
                            cursor.execute("""
                                UPDATE users SET balance = balance + ? 
                                WHERE id = ?
                            """, (usd_amount, user_id))
                            
                            conn.commit()
                            conn.close()
                            
                            logger.info(f"Payment processed: User {user_id}, Amount: {amount} {asset} (${usd_amount:.2f} USD), Invoice: {invoice_id}")
                            
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
        <head>
            <title>Payment Success</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; 
                    text-align: center; 
                    padding: 50px 20px;
                    margin: 0;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                }
                .success-container {
                    background: rgba(255,255,255,0.1);
                    padding: 40px;
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255,255,255,0.2);
                    max-width: 400px;
                    width: 100%;
                }
                h2 { font-size: 2em; margin-bottom: 20px; }
                p { font-size: 1.1em; margin-bottom: 15px; }
                .checkmark { font-size: 4em; margin-bottom: 20px; animation: bounce 1s ease; }
                @keyframes bounce {
                    0%, 20%, 60%, 100% { transform: translateY(0); }
                    40% { transform: translateY(-20px); }
                    80% { transform: translateY(-10px); }
                }
            </style>
        </head>
        <body>
            <div class="success-container">
                <div class="checkmark">✅</div>
                <h2>Payment Completed!</h2>
                <p>Your deposit has been processed successfully.</p>
                <p>Return to the bot to continue playing!</p>
            </div>
            <script>
                setTimeout(() => {
                    if (window.Telegram && window.Telegram.WebApp) {
                        window.Telegram.WebApp.close();
                    } else {
                        window.close();
                    }
                }, 3000);
            </script>
        </body>
        </html>
        """
    
    return app

# --- Menu Button Setup ---
async def setup_webapp_menu_button(application):
    """Set up the webapp menu button"""
    try:
        if WEBAPP_IMPORTS_AVAILABLE:
            webapp_button = MenuButtonWebApp(text="🎮 Casino", web_app=WebApp(url=WEBAPP_URL))
            await application.bot.set_chat_menu_button(menu_button=webapp_button)
            logger.info("✅ Webapp menu button set")
    except Exception as e:
        logger.error(f"❌ Failed to set webapp menu button: {e}")

# --- Main Function ---
async def main():
    """Main function to start the bot"""
    logger.info("🚀 Starting Casino Bot...")
    
    # Initialize database
    await init_db()
    
    # Create the Application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Register handlers in order of specificity
    
    # Start command
    application.add_handler(CommandHandler("start", start_command))
    
    # Deposit conversation handler (must be before other callback handlers)
    application.add_handler(deposit_conversation)
    
    # Specific callback handlers
    application.add_handler(CallbackQueryHandler(main_panel_callback, pattern="^main_panel$"))
    application.add_handler(CallbackQueryHandler(casino_callback, pattern="^casino$"))
    application.add_handler(CallbackQueryHandler(account_callback, pattern="^account$"))
    application.add_handler(CallbackQueryHandler(deposit_callback, pattern="^deposit$"))
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw$"))
    application.add_handler(CallbackQueryHandler(profile_callback, pattern="^profile$"))
    application.add_handler(CallbackQueryHandler(bonus_callback, pattern="^bonus$"))
    application.add_handler(CallbackQueryHandler(support_callback, pattern="^support$"))
    
    # Game handlers
    application.add_handler(CallbackQueryHandler(blackjack_callback, pattern="^blackjack$"))
    application.add_handler(CallbackQueryHandler(roulette_callback, pattern="^roulette$"))
    application.add_handler(CallbackQueryHandler(slots_callback, pattern="^slots$"))
    application.add_handler(CallbackQueryHandler(dice_callback, pattern="^dice$"))
    application.add_handler(CallbackQueryHandler(poker_callback, pattern="^poker$"))
    
    # Mini app handler
    application.add_handler(CallbackQueryHandler(mini_app_centre_callback, pattern="^mini_app_centre$"))
    
    # Weekly bonus handlers
    application.add_handler(CallbackQueryHandler(claim_weekly_bonus_callback, pattern="^claim_weekly_bonus$"))
    application.add_handler(CallbackQueryHandler(check_bonus_callback, pattern="^check_bonus$"))
    
    # VIP handlers
    application.add_handler(CallbackQueryHandler(vip_callback, pattern="^vip$"))
    application.add_handler(CallbackQueryHandler(vip_benefits_callback, pattern="^vip_benefits$"))
    
    # Generic callback handler (should be last)
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Set up mini app menu button
    await setup_webapp_menu_button(application)
    
    logger.info("✅ Bot handlers registered")
    
    # Start webhook server for CryptoBot payments
    if WEBHOOK_ENABLED:
        try:
            webhook_app = await setup_cryptobot_webhook_server()
            logger.info("🔗 CryptoBot webhook server configured")
            
            # Run webhook server in a separate thread
            def run_webhook():
                webhook_app.run(host='0.0.0.0', port=int(WEBHOOK_PORT), debug=False)
            
            import threading
            webhook_thread = threading.Thread(target=run_webhook, daemon=True)
            webhook_thread.start()
            logger.info(f"🌐 Webhook server started on port {WEBHOOK_PORT}")
        except Exception as e:
            logger.error(f"❌ Failed to start webhook server: {e}")
    
    # Start the bot
    logger.info("🎲 Casino Bot is running...")
    await application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
