"""
Configuration management for the casino bot
"""

import os
import logging
from typing import List
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Config:
    """Central configuration management"""
    
    def __init__(self):
        # Load environment files
        load_dotenv()
        load_dotenv(".env.owner")
        load_dotenv("env.litecoin")
        
        # Core bot configuration
        self.BOT_TOKEN = os.environ.get("BOT_TOKEN")
        self.DB_PATH = os.environ.get("CASINO_DB", "casino.db")
        self.BOT_VERSION = "2.1.0"
        
        if not self.BOT_TOKEN:
            raise RuntimeError("Set BOT_TOKEN in environment or .env")
        
        # Demo mode
        self.DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"
        
        # Owner and admin configuration
        self.OWNER_USER_ID = int(os.environ.get("OWNER_USER_ID", "0"))
        admin_ids_str = os.environ.get("ADMIN_USER_IDS", "")
        self.ADMIN_USER_IDS: List[int] = []
        if admin_ids_str:
            try:
                self.ADMIN_USER_IDS = list(map(int, admin_ids_str.split(",")))
            except ValueError:
                logger.warning("Invalid ADMIN_USER_IDS format in environment")
        
        # CryptoBot configuration
        self.CRYPTOBOT_API_TOKEN = os.environ.get("CRYPTOBOT_API_TOKEN")
        self.CRYPTOBOT_USD_ASSET = os.environ.get("CRYPTOBOT_USD_ASSET", "LTC")
        self.CRYPTOBOT_WEBHOOK_SECRET = os.environ.get("CRYPTOBOT_WEBHOOK_SECRET")
        
        # Render hosting configuration
        self.PORT = int(os.environ.get("PORT", "8001"))
        self.RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
        self.HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL", "300"))
        
        # Security Configuration
        self.MAX_BET_PER_GAME = int(os.environ.get("MAX_BET_PER_GAME", "1000"))
        self.MAX_DAILY_LOSSES = int(os.environ.get("MAX_DAILY_LOSSES", "5000"))
        self.ANTI_SPAM_WINDOW = int(os.environ.get("ANTI_SPAM_WINDOW", "10"))
        self.MAX_COMMANDS_PER_WINDOW = int(os.environ.get("MAX_COMMANDS_PER_WINDOW", "20"))
        
        # Withdrawal limits
        self.MIN_WITHDRAWAL_USD = float(os.environ.get("MIN_WITHDRAWAL_USD", "1.00"))
        self.MAX_WITHDRAWAL_USD = float(os.environ.get("MAX_WITHDRAWAL_USD", "10000.00"))
        
        # Support and channels
        self.SUPPORT_CHANNEL = os.environ.get("SUPPORT_CHANNEL", "@casino_support")
        
        # Conversation states
        self.DEPOSIT_LTC_AMOUNT = "DEPOSIT_LTC_AMOUNT"
        self.WITHDRAW_LTC_AMOUNT = "WITHDRAW_LTC_AMOUNT"
        self.WITHDRAW_LTC_ADDRESS = "WITHDRAW_LTC_ADDRESS"
    
    def is_owner(self, user_id: int) -> bool:
        """Check if user is the owner (super admin)"""
        return user_id == self.OWNER_USER_ID
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is an admin/owner"""
        is_admin_user = user_id in self.ADMIN_USER_IDS or self.is_owner(user_id)
        if is_admin_user:
            logger.info(f"Admin access granted to user {user_id}")
        return is_admin_user

# Global config instance
config = Config()
