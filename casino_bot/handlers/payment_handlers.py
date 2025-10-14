"""
Payment handlers for deposits and withdrawals
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..core.config import config
from ..services.database import db_service
from ..services.crypto import crypto_service

logger = logging.getLogger(__name__)

class PaymentHandlers:
    """Handlers for payment operations"""
    
    async def deposit_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /deposit command"""
        user_id = update.effective_user.id
        
        user = await db_service.get_user(user_id)
        if not user:
            await update.message.reply_text(
                "❌ User not found. Please use /start to register first.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Start", callback_data="main_panel")]])
            )
            return
        
        balance_str = f"${user['balance']:.2f}"
        
        text = f"""
💳 <b>DEPOSIT</b>

💰 Balance: {balance_str}

🪙 Litecoin (LTC) - Fast & secure
• Min: $1.00 • Instant processing
"""
        
        keyboard = [
            [InlineKeyboardButton("🪙 Deposit Litecoin (LTC)", callback_data="deposit_LTC")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]
        ]
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def deposit_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle deposit button"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        context.user_data.clear()
        
        user = await db_service.get_user(user_id)
        if not user:
            await query.edit_message_text(
                "❌ User not found. Please use /start to register first.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Start", callback_data="main_panel")]])
            )
            return
        
        balance_str = f"${user['balance']:.2f}"
        
        text = f"""
💳 <b>DEPOSIT</b>

💰 Balance: {balance_str}

🪙 Litecoin (LTC) - Fast & secure
• Min: $1.00 • Instant processing
"""
        
        keyboard = [
            [InlineKeyboardButton("🪙 Deposit Litecoin (LTC)", callback_data="deposit_LTC")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def deposit_crypto_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle specific crypto deposit selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        crypto_type = "LTC"  # For now, only LTC
        
        context.user_data.clear()
        context.user_data['awaiting_deposit_amount'] = crypto_type
        
        # Get current rate
        rate = await crypto_service.get_usd_rate(crypto_type)
        rate_text = f"${rate:.4f}" if rate > 0 else "Rate unavailable"
        
        text = f"""
💳 <b>DEPOSIT {crypto_type}</b>

Rate: 1 {crypto_type} = {rate_text} USD

Enter amount in USD (e.g., "50")

• Min: $1.00 • Max: $10,000
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Deposit", callback_data="deposit")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def withdraw_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle withdraw button"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        context.user_data.clear()
        
        user = await db_service.get_user(user_id)
        if not user:
            await query.edit_message_text(
                "❌ User not found. Please use /start to register first.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Start", callback_data="main_panel")]])
            )
            return
        
        balance = user['balance']
        min_withdrawal = config.MIN_WITHDRAWAL_USD
        
        if balance < min_withdrawal:
            await query.edit_message_text(
                f"❌ Minimum withdrawal is ${min_withdrawal:.2f}.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]])
            )
            return
        
        balance_str = f"${balance:.2f}"
        
        text = f"""
🏦 <b>WITHDRAW FUNDS</b>

💰 Balance: {balance_str}
💸 Available: {balance_str}

• Min: ${min_withdrawal:.2f} | Max: ${config.MAX_WITHDRAWAL_USD:.2f}
• Fee: 2% (min $1.00)
• Processing: 24h
"""
        
        keyboard = [
            [InlineKeyboardButton("🪙 Withdraw Litecoin (LTC)", callback_data="withdraw_LTC")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def withdraw_crypto_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle specific crypto withdrawal"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user = await db_service.get_user(user_id)
        
        if not user:
            await query.edit_message_text("❌ User not found. Please restart with /start")
            return
        
        balance_str = f"${user['balance']:.2f}"
        max_withdrawal = min(user['balance'], config.MAX_WITHDRAWAL_USD)
        
        text = f"""
🏦 <b>WITHDRAW LITECOIN (LTC)</b>

💰 Balance: {balance_str}
💸 Available: ${max_withdrawal:.2f}

Enter withdrawal amount in USD (e.g., "50")
"""
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Withdraw", callback_data="withdraw")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        
        context.user_data['awaiting_withdraw_amount'] = 'LTC'
    
    async def handle_deposit_amount_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle deposit amount input"""
        if 'awaiting_deposit_amount' not in context.user_data:
            return
        
        try:
            amount_usd = float(update.message.text.replace('$', '').replace(',', ''))
            if amount_usd < 1.0:
                await update.message.reply_text("❌ Minimum deposit is $1.00 USD.")
                return
            if amount_usd > 10000.0:
                await update.message.reply_text("❌ Maximum deposit is $10,000.00 USD per transaction.")
                return
            
            del context.user_data['awaiting_deposit_amount']
            await self._process_deposit_demo(update, context, amount_usd)
            
        except ValueError:
            await update.message.reply_text("❌ Invalid amount. Please enter a valid number (e.g., 10 or 25.50)")
    
    async def _process_deposit_demo(self, update: Update, context: ContextTypes.DEFAULT_TYPE, amount_usd: float):
        """Process deposit in demo mode"""
        user_id = update.effective_user.id
        
        # In demo mode, just add the balance
        if config.DEMO_MODE:
            success = await db_service.update_balance(user_id, amount_usd, "deposit")
            if success:
                user = await db_service.get_user(user_id)
                balance_str = f"${user['balance']:.2f}"
                
                text = f"""
✅ <b>DEMO DEPOSIT SUCCESSFUL!</b>

💰 Deposited: ${amount_usd:.2f}
💳 New Balance: {balance_str}

<i>In real mode, this would process via LTC</i>
"""
                
                keyboard = [
                    [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
                ]
                
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text("❌ Error processing deposit.")
        else:
            # Real mode would create CryptoBot invoice
            await update.message.reply_text("💳 Real crypto deposits coming soon!")
    
    async def handle_withdraw_amount_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle withdrawal amount input"""
        if 'awaiting_withdraw_amount' not in context.user_data:
            return
        
        user_id = update.message.from_user.id
        user = await db_service.get_user(user_id)
        
        if not user:
            await update.message.reply_text("❌ User not found.")
            return
        
        try:
            amount_usd = float(update.message.text.replace('$', '').replace(',', ''))
            
            # Check minimum
            if amount_usd < config.MIN_WITHDRAWAL_USD:
                await update.message.reply_text(f"❌ Minimum withdrawal is ${config.MIN_WITHDRAWAL_USD:.2f} USD.")
                return
            
            # Check balance
            user_balance = user.get('balance', 0.0)
            if amount_usd > user_balance:
                balance_str = f"${user_balance:.2f}"
                await update.message.reply_text(
                    f"❌ <b>Insufficient Balance</b>\\n\\n"
                    f"Your balance: {balance_str}\\n"
                    f"Withdrawal amount: ${amount_usd:.2f} USD\\n\\n"
                    f"You need ${amount_usd - user_balance:.2f} more to complete this withdrawal.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Process withdrawal in demo mode
            del context.user_data['awaiting_withdraw_amount']
            
            if config.DEMO_MODE:
                success = await db_service.update_balance(user_id, -amount_usd, "withdrawal")
                if success:
                    user = await db_service.get_user(user_id)
                    balance_str = f"${user['balance']:.2f}"
                    
                    text = f"""
✅ <b>DEMO WITHDRAWAL SUCCESSFUL!</b>

💸 Withdrawn: ${amount_usd:.2f}
💳 New Balance: {balance_str}

<i>In real mode, this would process to your LTC wallet</i>
"""
                    
                    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]]
                    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
                else:
                    await update.message.reply_text("❌ Error processing withdrawal.")
            else:
                await update.message.reply_text("🏦 Real crypto withdrawals coming soon!")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid amount. Please enter a valid number (e.g., 10 or 25.50)")
