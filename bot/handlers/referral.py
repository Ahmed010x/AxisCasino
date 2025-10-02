"""
Referral System Handlers

Handles referral link generation and commission tracking.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import sys
import os

# Import from main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from main import get_or_create_referral_code, get_referral_stats, get_referral_link


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /referral command - show referral link and stats."""
    user = update.effective_user
    user_id = user.id
    
    # Get or create referral code for user
    referral_code = await get_or_create_referral_code(user_id)
    
    # Get referral stats
    stats = await get_referral_stats(user_id)
    
    # Get bot username (try to get from context or use default)
    try:
        bot = await context.bot.get_me()
        bot_username = bot.username
    except:
        bot_username = "AxisCasinoBot"  # Fallback
    
    # Generate referral link
    referral_link = get_referral_link(bot_username, referral_code)
    
    # Format referral message
    referral_text = f"""
👥 <b>REFERRAL PROGRAM</b> 👥

💰 <b>Earn 20% Commission!</b>

Share your unique referral link and earn <b>20% of what your referrals lose</b> in games!

🔗 <b>Your Referral Link:</b>
<code>{referral_link}</code>

📊 <b>Your Stats:</b>
👥 Total Referrals: <b>{stats['count']}</b>
💵 Total Earned: <b>${stats['earnings']:.2f}</b>

<b>How it works:</b>
1. Share your link with friends
2. They sign up using your link
3. They get a ${5.0:.2f} welcome bonus
4. You earn 20% commission every time they lose a game

💡 <b>Example:</b>
If your referral loses $100, you earn $20!

<i>Start sharing and earning today!</i>
"""
    
    # Add recent referrals if any
    if stats['recent']:
        referral_text += "\n\n📋 <b>Recent Referrals:</b>\n"
        for ref in stats['recent'][:5]:
            username = ref['username'] or 'User'
            bonus = ref['bonus']
            referral_text += f"• {username} - Earned: ${bonus:.2f}\n"
    
    keyboard = [
        [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={referral_link}&text=Join this amazing casino bot!")],
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh_referral_stats")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(referral_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def handle_referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle referral-related callback queries."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "refresh_referral_stats":
        user_id = query.from_user.id
        
        # Get updated stats
        referral_code = await get_or_create_referral_code(user_id)
        stats = await get_referral_stats(user_id)
        
        # Get bot username
        try:
            bot = await context.bot.get_me()
            bot_username = bot.username
        except:
            bot_username = "AxisCasinoBot"
        
        referral_link = get_referral_link(bot_username, referral_code)
        
        # Format updated message
        referral_text = f"""
👥 <b>REFERRAL PROGRAM</b> 👥

💰 <b>Earn 20% Commission!</b>

Share your unique referral link and earn <b>20% of what your referrals lose</b> in games!

🔗 <b>Your Referral Link:</b>
<code>{referral_link}</code>

📊 <b>Your Stats:</b>
👥 Total Referrals: <b>{stats['count']}</b>
💵 Total Earned: <b>${stats['earnings']:.2f}</b>

<b>How it works:</b>
1. Share your link with friends
2. They sign up using your link
3. They get a ${5.0:.2f} welcome bonus
4. You earn 20% commission every time they lose a game

💡 <b>Example:</b>
If your referral loses $100, you earn $20!

<i>Start sharing and earning today!</i>
"""
        
        if stats['recent']:
            referral_text += "\n\n📋 <b>Recent Referrals:</b>\n"
            for ref in stats['recent'][:5]:
                username = ref['username'] or 'User'
                bonus = ref['bonus']
                referral_text += f"• {username} - Earned: ${bonus:.2f}\n"
        
        keyboard = [
            [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={referral_link}&text=Join this amazing casino bot!")],
            [InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh_referral_stats")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(referral_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    
    elif query.data == "referral_menu":
        # Called from main menu
        user_id = query.from_user.id
        referral_code = await get_or_create_referral_code(user_id)
        stats = await get_referral_stats(user_id)
        
        try:
            bot = await context.bot.get_me()
            bot_username = bot.username
        except:
            bot_username = "AxisCasinoBot"
        
        referral_link = get_referral_link(bot_username, referral_code)
        
        referral_text = f"""
👥 <b>REFERRAL PROGRAM</b> 👥

💰 <b>Earn 20% Commission!</b>

Share your unique referral link and earn <b>20% of what your referrals lose</b> in games!

🔗 <b>Your Referral Link:</b>
<code>{referral_link}</code>

📊 <b>Your Stats:</b>
👥 Total Referrals: <b>{stats['count']}</b>
💵 Total Earned: <b>${stats['earnings']:.2f}</b>

<b>How it works:</b>
1. Share your link with friends
2. They sign up using your link
3. They get a ${5.0:.2f} welcome bonus
4. You earn 20% commission every time they lose a game

💡 <b>Example:</b>
If your referral loses $100, you earn $20!

<i>Start sharing and earning today!</i>
"""
        
        if stats['recent']:
            referral_text += "\n\n📋 <b>Recent Referrals:</b>\n"
            for ref in stats['recent'][:5]:
                username = ref['username'] or 'User'
                bonus = ref['bonus']
                referral_text += f"• {username} - Earned: ${bonus:.2f}\n"
        
        keyboard = [
            [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={referral_link}&text=Join this amazing casino bot!")],
            [InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh_referral_stats")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(referral_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


__all__ = ['referral_command', 'handle_referral_callback']
