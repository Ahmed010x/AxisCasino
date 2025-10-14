"""
Message handling and utilities for the casino bot
"""

import time
import uuid
import logging
from typing import Optional
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class MessageService:
    """Service for handling message prioritization and utilities"""
    
    @staticmethod
    def generate_request_id() -> str:
        """Generate a unique request ID for amount input prioritization"""
        return f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    
    @staticmethod
    async def set_pending_amount_request(context: ContextTypes.DEFAULT_TYPE, state: str, prompt_type: str) -> str:
        """Set a new pending amount request and return its ID"""
        request_id = MessageService.generate_request_id()
        context.user_data['pending_amount_request'] = {
            'id': request_id,
            'state': state,
            'type': prompt_type,
            'timestamp': time.time()
        }
        logger.info(f"Set pending amount request: {request_id} for state {state}")
        return request_id
    
    @staticmethod
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
    
    @staticmethod
    async def clear_amount_request(context: ContextTypes.DEFAULT_TYPE):
        """Clear the pending amount request"""
        context.user_data.pop('pending_amount_request', None)
    
    @staticmethod
    async def send_priority_message(update: Update, prompt_type: str) -> None:
        """Send a message when a newer request has taken priority"""
        await update.message.reply_text(
            f"⚠️ **Request Superseded**\\n\\n"
            f"A newer {prompt_type} request is pending.\\n"
            f"Please respond to the latest prompt or use the menu buttons to navigate.",
            parse_mode=ParseMode.MARKDOWN
        )

# Global message service instance
message_service = MessageService()
