"""
Main bot handlers for navigation, stats, and core functionality
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..core.config import config
from ..services.database import db_service
from ..services.messages import message_service

logger = logging.getLogger(__name__)

class MainHandlers:
    """Handlers for main bot functionality"""
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Get or create user
        user = await db_service.get_user(user_id)
        if not user:
            success = await db_service.create_user(user_id, username)
            if not success:
                await update.message.reply_text("❌ Error creating account. Please try again.")
                return
            user = await db_service.get_user(user_id)
        
        # Format balance
        balance = user.get('balance', 0.0)
        balance_str = f"${balance:.2f}"
        
        welcome_text = f"""
🎰 <b>AXIS CASINO</b>

Welcome, {username}! 👋

💰 <b>Balance:</b> {balance_str}

<b>Choose an action:</b>
"""
        
        keyboard = [
            [
                InlineKeyboardButton("💳 Deposit", callback_data="deposit"),
                InlineKeyboardButton("🏦 Withdraw", callback_data="withdraw")
            ],
            [
                InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre"),
                InlineKeyboardButton("👥 Referrals", callback_data="referral_menu")
            ],
            [
                InlineKeyboardButton("🎁 Bonuses", callback_data="bonus_menu"),
                InlineKeyboardButton("📊 Statistics", callback_data="user_stats")
            ],
            [InlineKeyboardButton("❓ Help", callback_data="help_menu")]
        ]
        
        # Add admin panel for admins
        if config.is_admin(user_id):
            keyboard.append([InlineKeyboardButton("🔧 Admin Panel", callback_data="admin_panel")])
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def main_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main panel (same as /start but for callbacks)"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        username = query.from_user.username or query.from_user.first_name
        
        user = await db_service.get_user(user_id)
        if not user:
            await query.edit_message_text("❌ User not found. Please use /start to register.")
            return
        
        balance = user.get('balance', 0.0)
        balance_str = f"${balance:.2f}"
        
        welcome_text = f"""
🎰 <b>AXIS CASINO</b>

Welcome, {username}! 👋

💰 <b>Balance:</b> {balance_str}

<b>Choose an action:</b>
"""
        
        keyboard = [
            [
                InlineKeyboardButton("💳 Deposit", callback_data="deposit"),
                InlineKeyboardButton("🏦 Withdraw", callback_data="withdraw")
            ],
            [
                InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre"),
                InlineKeyboardButton("👥 Referrals", callback_data="referral_menu")
            ],
            [
                InlineKeyboardButton("🎁 Bonuses", callback_data="bonus_menu"),
                InlineKeyboardButton("📊 Statistics", callback_data="user_stats")
            ],
            [InlineKeyboardButton("❓ Help", callback_data="help_menu")]
        ]
        
        if config.is_admin(user_id):
            keyboard.append([InlineKeyboardButton("🔧 Admin Panel", callback_data="admin_panel")])
        
        await query.edit_message_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def games_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show games menu"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user = await db_service.get_user(user_id)
        
        if not user:
            await query.edit_message_text("❌ User not found. Please use /start to register.")
            return
        
        balance = user['balance']
        balance_str = f"${balance:.2f}"
        
        text = f"""
🎮 <b>CASINO GAMES</b>

💰 Balance: {balance_str}

Choose your game:

🎰 Slots • 🃏 Blackjack • 🎲 Dice • 🪙 Coin Flip

Good luck! 🍀
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🎰 Slots", callback_data="game_slots"),
                InlineKeyboardButton("🃏 Blackjack", callback_data="game_blackjack")
            ],
            [
                InlineKeyboardButton("🎲 Dice", callback_data="game_dice"),
                InlineKeyboardButton("🪙 Coin Flip", callback_data="game_coinflip")
            ],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def user_stats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user statistics"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user = await db_service.get_user(user_id)
        
        if not user:
            await query.edit_message_text("❌ User not found.")
            return
        
        balance_str = f"${user.get('balance', 0.0):.2f}"
        wagered_str = f"${user.get('total_wagered', 0.0):.2f}"
        won_str = f"${user.get('total_won', 0.0):.2f}"
        
        text = f"""
📊 <b>YOUR STATISTICS</b>

💰 Balance: {balance_str}
🎮 Games Played: {user.get('games_played', 0):,}
💵 Total Wagered: {wagered_str}
🏆 Total Won: {won_str}

🔥 Win Streak: {user.get('win_streak', 0)} (Max: {user.get('max_win_streak', 0)})
💎 Biggest Win: ${user.get('biggest_win', 0.0):.2f}

Member since: {user.get('created_at', '')[:10] if user.get('created_at') else 'Unknown'}
"""
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def help_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help menu"""
        query = update.callback_query
        await query.answer()
        
        text = """
❓ <b>HELP & SUPPORT</b>

<b>Getting Started:</b>
• /start - Access your panel
• Deposit funds to play
• Choose games & place bets
• Withdraw your winnings

<b>Payments:</b>
• Litecoin (LTC) supported
• Fast & secure transactions

Need help? Contact support.
"""
        
        keyboard = [
            [InlineKeyboardButton("🎮 Games", callback_data="mini_app_centre")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def referral_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show referral menu"""
        query = update.callback_query
        await query.answer()
        
        text = """
👥 <b>REFERRAL PROGRAM</b>

💰 <b>Earn 20% Commission!</b>

Share your referral link and earn commission when your friends play!

Coming soon - full referral system!
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def referral_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /referral command"""
        text = """
👥 <b>REFERRAL PROGRAM</b>

💰 <b>Earn 20% Commission!</b>

Share your referral link and earn commission when your friends play!

Coming soon - full referral system!
"""
        
        keyboard = [
            [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def bonus_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bonuses menu"""
        query = update.callback_query
        await query.answer()
        
        text = """
🎁 <b>BONUSES & REWARDS</b>

Claim your available bonuses!

• <b>Weekly Bonus</b>: Claim every 7 days
• <b>Referral Bonus</b>: Earn for invites
• <b>Special Events</b>: Watch for announcements

More coming soon!
"""
        
        keyboard = [
            [InlineKeyboardButton("🎁 Claim Weekly Bonus", callback_data="claim_weekly_bonus")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def claim_weekly_bonus_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle weekly bonus claim"""
        query = update.callback_query
        await query.answer()
        
        # Simple demo bonus for now
        user_id = query.from_user.id
        bonus_amount = 5.0
        
        success = await db_service.update_balance(user_id, bonus_amount, "bonus")
        
        if success:
            user = await db_service.get_user(user_id)
            balance_str = f"${user['balance']:.2f}"
            
            text = f"""
🎉 <b>BONUS CLAIMED!</b>

💰 Bonus: ${bonus_amount:.2f}
💳 Balance: {balance_str}

Enjoy your bonus!
"""
        else:
            text = """
❌ <b>Error Claiming Bonus</b>

Please try again or contact support.
"""
        
        keyboard = [
            [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre")],
            [InlineKeyboardButton("🔙 Back", callback_data="bonus_menu")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def admin_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin panel (admin only)"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not config.is_admin(user_id):
            await query.edit_message_text("❌ Access denied.")
            return
        
        text = """
🔧 <b>ADMIN PANEL</b>

Casino administration tools

<b>Features coming soon:</b>
• User management
• Transaction logs
• System analytics
• Game settings
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_panel")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    async def general_callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unmatched callback queries"""
        query = update.callback_query
        await query.answer()
        
        logger.warning(f"Unhandled callback: {query.data}")
        
        # Return to main menu
        await self.main_panel_callback(update, context)
    
    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text input for various states"""
        # Check for payment states first
        if 'awaiting_deposit_amount' in context.user_data:
            # This would be handled by payment handlers
            pass
        elif 'awaiting_withdraw_amount' in context.user_data:
            # This would be handled by payment handlers
            pass
        else:
            # For now, just ignore unexpected text input
            logger.debug(f"Ignored text input from user {update.effective_user.id}: {update.message.text}")
