#!/usr/bin/env python3
"""
Stake-Style Telegram Bot with Mini App Integration
A clean, modular bot that integrates with a web-based casino mini app.

Features:
- WebApp integration with Stake-style interface
- SQLite database for user management
- Flask backend API integration
- Async handlers using python-telegram-bot v20+
- Clean, professional code structure
"""

import os
import logging
import asyncio
import aiohttp
import aiosqlite
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebApp
from telegram.ext import (
    Application, 
    ApplicationBuilder, 
    CommandHandler, 
    ContextTypes,
    CallbackQueryHandler
)
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://my-stake-miniapp.onrender.com")
FLASK_API_URL = os.getenv("FLASK_API_URL", "http://localhost:5000")
DATABASE_PATH = os.getenv("DATABASE_PATH", "casino_users.db")

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all database operations for user management"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with users table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER UNIQUE NOT NULL,
                        balance REAL DEFAULT 1000.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
                logger.info("✅ Database initialized successfully")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user data by Telegram ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    'SELECT * FROM users WHERE telegram_id = ?', 
                    (telegram_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Error getting user {telegram_id}: {e}")
            return None
    
    def create_user(self, telegram_id: int, initial_balance: float = 1000.0) -> bool:
        """Create a new user with initial balance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'INSERT OR IGNORE INTO users (telegram_id, balance) VALUES (?, ?)',
                    (telegram_id, initial_balance)
                )
                conn.commit()
                logger.info(f"✅ User {telegram_id} created with balance {initial_balance}")
                return True
        except Exception as e:
            logger.error(f"❌ Error creating user {telegram_id}: {e}")
            return False
    
    def update_balance(self, telegram_id: int, new_balance: float) -> bool:
        """Update user balance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'UPDATE users SET balance = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?',
                    (new_balance, telegram_id)
                )
                conn.commit()
                logger.info(f"✅ Balance updated for user {telegram_id}: {new_balance}")
                return True
        except Exception as e:
            logger.error(f"❌ Error updating balance for user {telegram_id}: {e}")
            return False

class BackendAPI:
    """Handles communication with Flask backend API"""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
    
    async def check_balance(self, telegram_id: int) -> Optional[float]:
        """Check user balance via backend API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/api/balance/{telegram_id}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('balance')
                    else:
                        logger.warning(f"⚠️ Backend API returned status {response.status}")
                        return None
        except Exception as e:
            logger.error(f"❌ Error checking balance via API: {e}")
            return None
    
    async def place_bet(self, telegram_id: int, amount: float, game_type: str) -> Optional[Dict[str, Any]]:
        """Place a bet via backend API"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'telegram_id': telegram_id,
                    'amount': amount,
                    'game_type': game_type
                }
                async with session.post(
                    f"{self.api_url}/api/bet",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"⚠️ Bet API returned status {response.status}")
                        return None
        except Exception as e:
            logger.error(f"❌ Error placing bet via API: {e}")
            return None

class StakeCasinoBot:
    """Main bot class with all command handlers"""
    
    def __init__(self):
        self.db = DatabaseManager(DATABASE_PATH)
        self.api = BackendAPI(FLASK_API_URL)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - Main entry point with mini app integration"""
        user = update.effective_user
        telegram_id = user.id
        username = user.username or user.first_name or f"User_{telegram_id}"
        
        # Get or create user
        user_data = self.db.get_user(telegram_id)
        if not user_data:
            self.db.create_user(telegram_id)
            user_data = self.db.get_user(telegram_id)
            welcome_msg = "🎉 Welcome! You've received 1,000 credits to start playing!"
        else:
            welcome_msg = f"👋 Welcome back, {username}!"
        
        # Create mini app button with WebApp
        mini_app_url = f"{MINI_APP_URL}?telegram_id={telegram_id}&balance={user_data['balance']}"
        webapp = WebApp(url=mini_app_url)
        
        # Build keyboard with mini app integration
        keyboard = [
            [InlineKeyboardButton("🎰 Open Casino Mini App", web_app=webapp)],
            [
                InlineKeyboardButton("💰 Check Balance", callback_data="balance"),
                InlineKeyboardButton("💳 Deposit", callback_data="deposit")
            ],
            [
                InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
                InlineKeyboardButton("📊 Statistics", callback_data="stats")
            ],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
🎰 **STAKE CASINO BOT** 🎰

{welcome_msg}

💰 **Current Balance:** {user_data['balance']:,.2f} credits
🎮 **Ready to play?** Launch the mini app for the full casino experience!

🎯 **Features:**
• 🎰 Slots, Blackjack, Roulette & more
• 🚀 Instant gameplay in mini app
• 💸 Secure deposits & withdrawals
• 📊 Real-time statistics

Choose an option below:
"""
        
        await update.message.reply_text(
            text, 
            reply_markup=reply_markup, 
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"✅ Start command executed for user {telegram_id}")
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /balance command - Show user balance with sync option"""
        telegram_id = update.effective_user.id
        
        # Get balance from local database
        user_data = self.db.get_user(telegram_id)
        if not user_data:
            await update.message.reply_text("❌ User not found. Please use /start first.")
            return
        
        local_balance = user_data['balance']
        
        # Try to sync with backend API
        api_balance = await self.api.check_balance(telegram_id)
        
        if api_balance is not None and abs(api_balance - local_balance) > 0.01:
            # Update local balance if API balance is different
            self.db.update_balance(telegram_id, api_balance)
            balance_status = f"🔄 **Synced:** {api_balance:,.2f} credits"
        else:
            balance_status = f"💰 **Current:** {local_balance:,.2f} credits"
        
        # Create action buttons
        keyboard = [
            [
                InlineKeyboardButton("🎰 Play Now", web_app=WebApp(url=f"{MINI_APP_URL}?telegram_id={telegram_id}")),
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_balance")
            ],
            [
                InlineKeyboardButton("💳 Deposit", callback_data="deposit"),
                InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")
            ],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        
        text = f"""
💰 **BALANCE OVERVIEW** 💰

{balance_status}
📊 **Account:** Premium
🎮 **Status:** Active

🎯 **Quick Actions:**
Use the buttons below to manage your account or start playing!
"""
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"✅ Balance command executed for user {telegram_id}")
    
    async def deposit_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /deposit command - Deposit funds placeholder"""
        telegram_id = update.effective_user.id
        
        keyboard = [
            [
                InlineKeyboardButton("💳 Credit Card", callback_data="deposit_card"),
                InlineKeyboardButton("🏦 Bank Transfer", callback_data="deposit_bank")
            ],
            [
                InlineKeyboardButton("₿ Crypto", callback_data="deposit_crypto"),
                InlineKeyboardButton("📱 E-Wallet", callback_data="deposit_ewallet")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        
        text = f"""
💳 **DEPOSIT FUNDS** 💳

📊 **Available Methods:**

**💳 Credit/Debit Card**
• Instant processing
• Min: $10 | Max: $5,000
• Fee: 2.5%

**🏦 Bank Transfer**
• 1-3 business days
• Min: $25 | Max: $10,000
• Fee: Free

**₿ Cryptocurrency**
• Bitcoin, Ethereum, USDT
• 10-60 min processing
• Min: $5 | Fee: Network only

**📱 E-Wallets**
• PayPal, Skrill, Neteller
• Instant processing
• Min: $10 | Fee: 1.5%

🔒 **All transactions are secure and encrypted**

Choose your preferred method:
"""
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"✅ Deposit command executed for user {telegram_id}")
    
    async def withdraw_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /withdraw command - Withdraw funds placeholder"""
        telegram_id = update.effective_user.id
        
        user_data = self.db.get_user(telegram_id)
        if not user_data:
            await update.message.reply_text("❌ User not found. Please use /start first.")
            return
        
        balance = user_data['balance']
        min_withdrawal = 50.0
        
        if balance < min_withdrawal:
            await update.message.reply_text(
                f"❌ Minimum withdrawal amount is {min_withdrawal:,.2f} credits.\n"
                f"Your current balance: {balance:,.2f} credits"
            )
            return
        
        keyboard = [
            [
                InlineKeyboardButton("🏦 Bank Transfer", callback_data="withdraw_bank"),
                InlineKeyboardButton("₿ Crypto", callback_data="withdraw_crypto")
            ],
            [
                InlineKeyboardButton("📱 E-Wallet", callback_data="withdraw_ewallet"),
                InlineKeyboardButton("💳 Card", callback_data="withdraw_card")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        
        text = f"""
💸 **WITHDRAW FUNDS** 💸

💰 **Available Balance:** {balance:,.2f} credits
⏱️ **Processing Time:** 24-72 hours

📋 **Withdrawal Methods:**

**🏦 Bank Transfer**
• 1-3 business days
• Min: 50 credits | Fee: Free
• Most secure option

**₿ Cryptocurrency**
• 10-60 min processing
• Min: 25 credits | Fee: Network
• Fastest option

**📱 E-Wallets**
• 6-24 hours
• Min: 50 credits | Fee: 2%
• Convenient option

**💳 Debit Card**
• 1-5 business days
• Min: 50 credits | Fee: 1.5%
• Direct to card

🔒 **Identity verification may be required**

Choose your withdrawal method:
"""
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"✅ Withdraw command executed for user {telegram_id}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command - Show bot help and instructions"""
        
        keyboard = [
            [InlineKeyboardButton("🎰 Start Playing", web_app=WebApp(url=MINI_APP_URL))],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        
        text = f"""
❓ **STAKE CASINO BOT HELP** ❓

**🎯 Available Commands:**
• `/start` - Main menu with mini app
• `/balance` - Check your current balance
• `/deposit` - Add funds to your account
• `/withdraw` - Withdraw your winnings
• `/help` - Show this help message

**🎰 How to Play:**
1. Click "🎰 Open Casino Mini App" to launch games
2. Play slots, blackjack, roulette, and more
3. Your balance syncs automatically
4. Withdraw winnings anytime

**💳 Financial Operations:**
• Secure deposits via multiple methods
• Fast withdrawals (24-72h processing)
• Real-time balance updates
• Encrypted transactions

**🎮 Mini App Features:**
• Full-screen gaming experience
• Real-time multiplayer games
• Progressive jackpots
• Live dealer games
• Mobile optimized

**🔒 Security:**
• All funds are secure
• Licensed and regulated
• 24/7 customer support
• Responsible gaming tools

Need help? Contact our support team!
"""
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"✅ Help command executed")
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        telegram_id = query.from_user.id
        
        # Route callbacks to appropriate handlers
        if data == "main_menu":
            await self.start_command(update, context)
        elif data == "balance" or data == "refresh_balance":
            await self.balance_command(update, context)
        elif data == "deposit":
            await self.deposit_command(update, context)
        elif data == "withdraw":
            await self.withdraw_command(update, context)
        elif data == "help":
            await self.help_command(update, context)
        elif data.startswith("deposit_") or data.startswith("withdraw_"):
            # Placeholder for specific payment method handlers
            method = data.split("_")[1]
            await query.edit_message_text(
                f"🚧 {method.title()} integration coming soon!\n\n"
                f"This feature is currently under development. "
                f"Please check back later or contact support for assistance.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
                ])
            )
        else:
            # Unknown callback
            await query.edit_message_text(
                "❌ Unknown action. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
                ])
            )
        
        logger.info(f"✅ Callback '{data}' handled for user {telegram_id}")

async def main():
    """Main function to run the bot"""
    
    # Validate configuration
    if BOT_TOKEN == 'your_bot_token_here':
        logger.error("❌ Please set your BOT_TOKEN environment variable")
        return
    
    # Initialize bot
    bot = StakeCasinoBot()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("balance", bot.balance_command))
    application.add_handler(CommandHandler("deposit", bot.deposit_command))
    application.add_handler(CommandHandler("withdraw", bot.withdraw_command))
    application.add_handler(CommandHandler("help", bot.help_command))
    
    # Register callback query handler
    from telegram.ext import CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(bot.callback_handler))
    
    logger.info("🚀 Starting Stake Casino Bot...")
    logger.info(f"🌐 Mini App URL: {MINI_APP_URL}")
    logger.info(f"🔌 Backend API: {FLASK_API_URL}")
    
    # Start the bot
    await application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    """Entry point"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
