#!/usr/bin/env python3
"""
Simplified Telegram Casino Bot
A modular, maintainable casino bot with clean architecture
"""

import os
import sys
import logging
import asyncio
import threading
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, 
    CallbackQueryHandler, MessageHandler, filters, ContextTypes
)

# Import our modular services
from casino_bot.core.config import config
from casino_bot.services.database import db_service
from casino_bot.services.crypto import crypto_service
from casino_bot.services.messages import message_service
from casino_bot.handlers.main_handlers import MainHandlers
from casino_bot.handlers.game_handlers import GameHandlers
from casino_bot.handlers.payment_handlers import PaymentHandlers

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

class CasinoBot:
    """Main casino bot class with simplified structure"""
    
    def __init__(self):
        self.application = None
        self.main_handlers = MainHandlers()
        self.game_handlers = GameHandlers()
        self.payment_handlers = PaymentHandlers()
    
    async def setup(self):
        """Initialize the bot and database"""
        logger.info("🎰 Casino Bot starting up...")
        
        # Initialize database
        await db_service.init_db()
        
        # Create application
        self.application = ApplicationBuilder().token(config.BOT_TOKEN).build()
        
        # Register handlers
        self._register_handlers()
        
        logger.info("✅ Casino Bot setup complete!")
    
    def _register_handlers(self):
        """Register all bot handlers"""
        app = self.application
        
        # Command handlers
        app.add_handler(CommandHandler("start", self.main_handlers.start_command))
        app.add_handler(CommandHandler("deposit", self.payment_handlers.deposit_command))
        app.add_handler(CommandHandler("referral", self.main_handlers.referral_command))
        
        # Payment handlers (high priority)
        app.add_handler(CallbackQueryHandler(
            self.payment_handlers.deposit_callback, pattern=r"^deposit$"
        ))
        app.add_handler(CallbackQueryHandler(
            self.payment_handlers.deposit_crypto_callback, pattern=r"^deposit_LTC$"
        ))
        app.add_handler(CallbackQueryHandler(
            self.payment_handlers.withdraw_callback, pattern=r"^withdraw$"
        ))
        app.add_handler(CallbackQueryHandler(
            self.payment_handlers.withdraw_crypto_callback, pattern=r"^withdraw_LTC$"
        ))
        
        # Game handlers
        app.add_handler(CallbackQueryHandler(
            self.main_handlers.games_menu_callback, pattern=r"^mini_app_centre$"
        ))
        app.add_handler(CallbackQueryHandler(
            self.game_handlers.slots_callback, pattern=r"^game_slots$"
        ))
        app.add_handler(CallbackQueryHandler(
            self.game_handlers.blackjack_callback, pattern=r"^game_blackjack$"
        ))
        app.add_handler(CallbackQueryHandler(
            self.game_handlers.dice_callback, pattern=r"^game_dice$"
        ))
        app.add_handler(CallbackQueryHandler(
            self.game_handlers.coinflip_callback, pattern=r"^game_coinflip$"
        ))
        
        # Game betting handlers
        app.add_handler(CallbackQueryHandler(
            self.game_handlers.handle_slots_bet, pattern=r"^slots_bet_"
        ))
        app.add_handler(CallbackQueryHandler(
            self.game_handlers.handle_blackjack_bet, pattern=r"^blackjack_bet_"
        ))
        app.add_handler(CallbackQueryHandler(
            self.game_handlers.handle_dice_bet, pattern=r"^dice_bet_"
        ))
        app.add_handler(CallbackQueryHandler(
            self.game_handlers.handle_dice_play, pattern=r"^dice_play_"
        ))
        
        # General navigation handlers
        app.add_handler(CallbackQueryHandler(
            self.main_handlers.main_panel_callback, pattern=r"^main_panel$"
        ))
        app.add_handler(CallbackQueryHandler(
            self.main_handlers.user_stats_callback, pattern=r"^user_stats$"
        ))
        app.add_handler(CallbackQueryHandler(
            self.main_handlers.help_menu_callback, pattern=r"^help_menu$"
        ))
        app.add_handler(CallbackQueryHandler(
            self.main_handlers.referral_menu_callback, pattern=r"^referral_menu$"
        ))
        app.add_handler(CallbackQueryHandler(
            self.main_handlers.bonus_menu_callback, pattern=r"^bonus_menu$"
        ))
        app.add_handler(CallbackQueryHandler(
            self.main_handlers.claim_weekly_bonus_callback, pattern=r"^claim_weekly_bonus$"
        ))
        
        # Admin handlers (if admin)
        app.add_handler(CallbackQueryHandler(
            self.main_handlers.admin_panel_callback, pattern=r"^admin_panel$"
        ))
        
        # General callback handler (fallback)
        app.add_handler(CallbackQueryHandler(self.main_handlers.general_callback_handler))
        
        # Text message handler
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self._handle_text_input
        ))
    
    async def _handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text input for various states"""
        # Check for payment states
        if 'awaiting_deposit_amount' in context.user_data:
            await self.payment_handlers.handle_deposit_amount_input(update, context)
        elif 'awaiting_withdraw_amount' in context.user_data:
            await self.payment_handlers.handle_withdraw_amount_input(update, context)
        else:
            # Ignore unexpected text input
            logger.debug(f"Ignored text input from user {update.effective_user.id}: {update.message.text}")
    
    async def run(self):
        """Run the bot"""
        if not self.application:
            await self.setup()
        
        logger.info("🚀 Starting Telegram bot polling...")
        await self.application.run_polling(drop_pending_updates=True)
    
    def run_sync(self):
        """Run the bot synchronously"""
        asyncio.run(self.run())

# Flask app for health checks (deployment)
from flask import Flask

app = Flask(__name__)

@app.route('/keepalive')
def keep_alive():
    """Health check endpoint"""
    return {
        "status": "ok",
        "bot": "casino_bot",
        "version": config.BOT_VERSION,
        "timestamp": datetime.now().isoformat()
    }, 200

def run_flask():
    """Run Flask server for health checks"""
    port = config.PORT
    app.run(host="0.0.0.0", port=port, debug=False)

def main():
    """Main entry point"""
    # Environment detection
    is_deployment = bool(
        os.environ.get("RENDER") or 
        os.environ.get("RAILWAY_ENVIRONMENT") or 
        os.environ.get("HEROKU")
    )
    
    bot = CasinoBot()
    
    if is_deployment:
        # In deployment, run Flask health check server in background
        logger.info("🚀 Starting in deployment mode...")
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # Run bot in main thread
        bot.run_sync()
    else:
        # Local development
        logger.info("🏠 Starting in development mode...")
        bot.run_sync()

if __name__ == "__main__":
    main()
