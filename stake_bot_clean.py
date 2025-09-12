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
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
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
FLASK_API_URL = os.getenv("FLASK_API_URL", "http://localhost:5001")
DATABASE_PATH = os.getenv("DATABASE_PATH", "casino_users.db")

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all database operations for user management."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def init_database(self) -> None:
        """Initialize the SQLite database with users table."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    balance REAL DEFAULT 1000.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index for faster lookups
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_telegram_id ON users(telegram_id)
            """)
            
            await db.commit()
            logger.info("✅ Database initialized successfully")
    
    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user data by Telegram ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", 
                (telegram_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def create_user(self, telegram_id: int, username: str = None) -> Dict[str, Any]:
        """Create a new user with default balance."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (telegram_id, username, balance) 
                VALUES (?, ?, ?)
            """, (telegram_id, username, 1000.0))
            await db.commit()
            
        # Return the created user
        return await self.get_user(telegram_id)
    
    async def update_balance(self, telegram_id: int, new_balance: float) -> bool:
        """Update user balance."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE users 
                SET balance = ?, last_active = CURRENT_TIMESTAMP 
                WHERE telegram_id = ?
            """, (new_balance, telegram_id))
            await db.commit()
            return cursor.rowcount > 0
    
    async def update_last_active(self, telegram_id: int) -> None:
        """Update user's last active timestamp."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users 
                SET last_active = CURRENT_TIMESTAMP 
                WHERE telegram_id = ?
            """, (telegram_id,))
            await db.commit()

class APIClient:
    """Handles communication with the Flask backend API."""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
    
    async def check_balance(self, telegram_id: int) -> Optional[float]:
        """Check user balance via API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/api/balance/{telegram_id}"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('balance')
                    return None
        except Exception as e:
            logger.error(f"❌ API balance check failed: {e}")
            return None
    
    async def process_bet(self, telegram_id: int, amount: float, game_type: str) -> Dict[str, Any]:
        """Process a bet via API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/api/bet",
                    json={
                        'telegram_id': telegram_id,
                        'amount': amount,
                        'game_type': game_type
                    }
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    return {'success': False, 'error': 'API request failed'}
        except Exception as e:
            logger.error(f"❌ API bet processing failed: {e}")
            return {'success': False, 'error': str(e)}

class StakeBot:
    """Main bot class that handles all Telegram interactions."""
    
    def __init__(self):
        self.db_manager = DatabaseManager(DATABASE_PATH)
        self.api_client = APIClient(FLASK_API_URL)
        self.application = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - show main menu with WebApp button."""
        user = update.effective_user
        telegram_id = user.id
        username = user.username or user.first_name
        
        # Update last active
        await self.db_manager.update_last_active(telegram_id)
        
        # Get or create user
        user_data = await self.db_manager.get_user(telegram_id)
        if not user_data:
            user_data = await self.db_manager.create_user(telegram_id, username)
            welcome_msg = "🎉 Welcome! You've received 1,000 chips to get started!"
        else:
            welcome_msg = f"👋 Welcome back, {user_data['username'] or 'Player'}!"
        
        # Create WebApp button
        webapp_url = f"{MINI_APP_URL}?telegram_id={telegram_id}&balance={user_data['balance']}"
        webapp_button = InlineKeyboardButton(
            "🎰 Open Stake Casino", 
            web_app=WebAppInfo(url=webapp_url)
        )
        
        # Create keyboard with WebApp and other options
        keyboard = [
            [webapp_button],
            [
                InlineKeyboardButton("💰 Balance", callback_data="balance"),
                InlineKeyboardButton("📊 Stats", callback_data="stats")
            ],
            [
                InlineKeyboardButton("💳 Deposit", callback_data="deposit"),
                InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")
            ],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        
        text = f"""
🎰 **STAKE CASINO BOT** 🎰

{welcome_msg}

💰 **Balance:** {user_data['balance']:,.2f} chips
🎮 **Status:** Ready to play

🚀 **Launch the mini app for the full casino experience!**

*Choose an option below:*
"""
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"✅ User {telegram_id} ({username}) accessed /start")
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /balance command - show user balance."""
        telegram_id = update.effective_user.id
        
        # Update last active
        await self.db_manager.update_last_active(telegram_id)
        
        # Get user data
        user_data = await self.db_manager.get_user(telegram_id)
        if not user_data:
            await update.message.reply_text("❌ User not found. Please use /start first.")
            return
        
        # Try to get balance from API (if available)
        api_balance = await self.api_client.check_balance(telegram_id)
        if api_balance is not None:
            # Update local balance with API balance
            await self.db_manager.update_balance(telegram_id, api_balance)
            balance = api_balance
        else:
            balance = user_data['balance']
        
        text = f"""
💰 **BALANCE OVERVIEW** 💰

**Current Balance:** {balance:,.2f} chips
**Account:** {user_data['username'] or 'Player'}
**Member Since:** {user_data['created_at'][:10]}

💳 **Quick Actions:**
"""
        
        keyboard = [
            [
                InlineKeyboardButton("💳 Deposit", callback_data="deposit"),
                InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")
            ],
            [
                InlineKeyboardButton("🎰 Play Now", web_app=WebAppInfo(url=f"{MINI_APP_URL}?telegram_id={telegram_id}&balance={balance}")),
            ],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"✅ User {telegram_id} checked balance: {balance:,.2f}")
    
    async def deposit_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /deposit command - show deposit options."""
        telegram_id = update.effective_user.id
        
        # Update last active
        await self.db_manager.update_last_active(telegram_id)
        
        text = """
💳 **DEPOSIT FUNDS** 💳

**Available Methods:**

🏦 **Bank Transfer**
• Processing: 1-3 business days
• Minimum: $10
• Maximum: $10,000
• Fee: Free

💳 **Credit/Debit Card**
• Processing: Instant
• Minimum: $10
• Maximum: $5,000
• Fee: 2.9%

₿ **Cryptocurrency**
• Processing: 10-60 minutes
• Minimum: $10
• Maximum: $50,000
• Fee: Network fees only

📱 **E-Wallet**
• Processing: Instant
• Minimum: $10
• Maximum: $2,500
• Fee: 1.5%

*Contact support to process your deposit.*
"""
        
        keyboard = [
            [InlineKeyboardButton("📞 Contact Support", url="https://t.me/your_support_bot")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"✅ User {telegram_id} accessed deposit menu")
    
    async def withdraw_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /withdraw command - show withdrawal options."""
        telegram_id = update.effective_user.id
        
        # Update last active
        await self.db_manager.update_last_active(telegram_id)
        
        # Get user balance
        user_data = await self.db_manager.get_user(telegram_id)
        if not user_data:
            await update.message.reply_text("❌ User not found. Please use /start first.")
            return
        
        balance = user_data['balance']
        min_withdrawal = 50.0
        
        if balance < min_withdrawal:
            text = f"""
💸 **WITHDRAWAL** 💸

❌ **Insufficient Balance**

**Current Balance:** {balance:,.2f} chips
**Minimum Withdrawal:** {min_withdrawal:,.2f} chips

*You need at least {min_withdrawal:,.2f} chips to make a withdrawal.*
"""
        else:
            text = f"""
💸 **WITHDRAW FUNDS** 💸

**Available Balance:** {balance:,.2f} chips

**Withdrawal Methods:**

🏦 **Bank Transfer**
• Processing: 1-5 business days
• Minimum: $50
• Maximum: $25,000
• Fee: Free

₿ **Cryptocurrency**
• Processing: 10-60 minutes
• Minimum: $50
• Maximum: $100,000
• Fee: Network fees only

📱 **E-Wallet**
• Processing: 24-48 hours
• Minimum: $50
• Maximum: $10,000
• Fee: 2%

*Contact support to process your withdrawal.*
"""
        
        keyboard = [
            [InlineKeyboardButton("📞 Contact Support", url="https://t.me/your_support_bot")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"✅ User {telegram_id} accessed withdrawal menu")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command - show help information."""
        text = """
🎰 **STAKE CASINO BOT HELP** 🎰

**Commands:**
/start - Main menu with casino access
/balance - Check your current balance
/deposit - Add funds to your account
/withdraw - Withdraw your winnings
/help - Show this help message

**How to Play:**
1. Use /start to access the main menu
2. Click "🎰 Open Stake Casino" to launch the mini app
3. Play games directly in the web interface
4. Your balance syncs automatically with the bot

**Features:**
🎮 Full casino experience in the mini app
💰 Real-time balance synchronization
💳 Multiple deposit/withdrawal methods
📊 Game statistics and history
🎁 Bonuses and promotions

**Support:**
Need help? Contact our support team anytime.

*Ready to play? Use /start to begin!*
"""
        
        keyboard = [
            [InlineKeyboardButton("🎰 Start Playing", callback_data="main_menu")],
            [InlineKeyboardButton("📞 Contact Support", url="https://t.me/your_support_bot")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline keyboard callbacks."""
        query = update.callback_query
        await query.answer()
        
        telegram_id = query.from_user.id
        data = query.data
        
        if data == "main_menu":
            # Simulate start command for main menu
            fake_update = type('obj', (object,), {
                'message': query.message,
                'effective_user': query.from_user
            })()
            await self.start_command(fake_update, context)
            
        elif data == "balance":
            # Simulate balance command
            fake_update = type('obj', (object,), {
                'message': query.message,
                'effective_user': query.from_user
            })()
            await self.balance_command(fake_update, context)
            
        elif data == "deposit":
            # Simulate deposit command
            fake_update = type('obj', (object,), {
                'message': query.message,
                'effective_user': query.from_user
            })()
            await self.deposit_command(fake_update, context)
            
        elif data == "withdraw":
            # Simulate withdraw command
            fake_update = type('obj', (object,), {
                'message': query.message,
                'effective_user': query.from_user
            })()
            await self.withdraw_command(fake_update, context)
            
        elif data == "stats":
            user_data = await self.db_manager.get_user(telegram_id)
            text = f"""
📊 **PLAYER STATISTICS** 📊

**Account:** {user_data['username'] or 'Player'}
**Balance:** {user_data['balance']:,.2f} chips
**Member Since:** {user_data['created_at'][:10]}
**Last Active:** {user_data['last_active'][:10]}

*Detailed stats available in the mini app!*
"""
            keyboard = [
                [InlineKeyboardButton("🎰 Play Now", web_app=WebAppInfo(url=f"{MINI_APP_URL}?telegram_id={telegram_id}"))],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
            ]
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            
        elif data == "help":
            await self.help_command(update, context)
    
    async def setup_handlers(self) -> None:
        """Set up all command and callback handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("balance", self.balance_command))
        self.application.add_handler(CommandHandler("deposit", self.deposit_command))
        self.application.add_handler(CommandHandler("withdraw", self.withdraw_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Callback handler
        self.application.add_handler(CallbackQueryHandler(self.handle_callbacks))
        
        logger.info("✅ All handlers registered")
    
    async def run(self) -> None:
        """Start the bot."""
        if not BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        # Initialize database
        await self.db_manager.init_database()
        
        # Create application
        self.application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Setup handlers
        await self.setup_handlers()
        
        # Start the bot
        logger.info("🚀 Starting Stake Casino Bot...")
        logger.info(f"🎰 Mini App URL: {MINI_APP_URL}")
        logger.info(f"🔗 Flask API URL: {FLASK_API_URL}")
        
        # Run the bot
        await self.application.run_polling(drop_pending_updates=True)

async def main():
    """Main entry point."""
    try:
        bot = StakeBot()
        await bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise

if __name__ == "__main__":
    print("🎰 Stake Casino Bot")
    print("🚀 Starting...")
    
    # Run the bot
    asyncio.run(main())
