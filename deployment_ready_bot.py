#!/usr/bin/env python3
"""
Deployment-Ready Casino Bot with Web Server
Includes keep-alive, port binding, and all enhancements
"""

import os
import asyncio
import logging
from flask import Flask, jsonify
import threading
import time
from telegram.ext import Application

# Import all enhancements
from house_balance_integration_examples import (
    start_web_server, enhanced_keep_alive_pinger, house_balance_command
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeploymentReadyBot:
    """Production-ready bot with web server and keep-alive"""
    
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        self.port = int(os.getenv('PORT', 8080))
        self.app = None
        
    async def setup_bot(self):
        """Setup and configure the bot"""
        if not self.bot_token:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        # Create application
        self.app = Application.builder().token(self.bot_token).build()
        
        # Add basic handlers
        from telegram.ext import CommandHandler
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("housebal", house_balance_command))
        
        logger.info("✅ Bot handlers configured")
        
    async def start_command(self, update, context):
        """Enhanced start command"""
        user = update.effective_user
        welcome_text = f"""
🎰 <b>Welcome to Enhanced Casino Bot!</b> 🎰

Hello {user.first_name}! 👋

🚀 <b>Status:</b> Fully Operational
🔗 <b>Web Server:</b> Running on port {self.port}
💰 <b>House Balance:</b> Available via /housebal
🎮 <b>Games:</b> Coming soon with enhancements!

🔐 <b>Features:</b>
• Keep-alive system active
• Web server for deployment
• House balance tracking
• Enhanced security
• Professional monitoring

Ready to play! 🎲
"""
        
        await update.message.reply_text(welcome_text, parse_mode='HTML')
    
    def start_web_server(self):
        """Start the Flask web server"""
        start_web_server()  # From house_balance_integration_examples
        logger.info(f"🌐 Web server started on port {self.port}")
    
    async def run_bot(self):
        """Run the bot with all services"""
        try:
            # Setup bot
            await self.setup_bot()
            
            # Start web server in background
            self.start_web_server()
            
            # Start keep-alive task
            asyncio.create_task(enhanced_keep_alive_pinger(300))
            
            # Start the bot
            logger.info("🚀 Starting Enhanced Casino Bot...")
            await self.app.run_polling()
            
        except Exception as e:
            logger.error(f"❌ Bot startup failed: {e}")
            raise

async def main():
    """Main entry point"""
    print("🎰 Enhanced Telegram Casino Bot - Deployment Ready")
    print("=" * 50)
    
    # Create and run bot
    bot = DeploymentReadyBot()
    await bot.run_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        exit(1)
