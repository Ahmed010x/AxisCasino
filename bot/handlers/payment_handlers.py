"""
Payment command handlers for the Telegram Casino Bot.

Handles deposit, withdrawal, and payment management commands.
"""

import logging
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.database.user import get_user, create_user
from bot.handlers.payments import (
    DepositProcessor, WithdrawalProcessor, PaymentProcessor, 
    PaymentMethodManager
)

logger = logging.getLogger(__name__)


async def payments_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main payments menu."""
    user_id = update.effective_user.id
    
    # Ensure user exists
    user = await get_user(user_id)
    if not user:
        await create_user(user_id, update.effective_user.username)
        user = await get_user(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("💰 Deposit", callback_data="payment_deposit"),
            InlineKeyboardButton("💸 Withdraw", callback_data="payment_withdraw")
        ],
        [
            InlineKeyboardButton("📊 Transaction History", callback_data="payment_history"),
            InlineKeyboardButton("💳 Payment Methods", callback_data="payment_methods")
        ],
        [
            InlineKeyboardButton("ℹ️ Payment Info", callback_data="payment_info"),
            InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
💼 **Payment Center**

**Current Balance:** {user['balance']:,} coins

Choose an option below to manage your payments:

💰 **Deposit** - Add coins to your account
💸 **Withdraw** - Cash out your winnings
📊 **History** - View transaction history
💳 **Methods** - Manage payment methods
"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def deposit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show deposit options."""
    keyboard = [
        [
            InlineKeyboardButton("⭐ Telegram Stars", callback_data="deposit_stars"),
            InlineKeyboardButton("₿ Cryptocurrency", callback_data="deposit_crypto")
        ],
        [
            InlineKeyboardButton("💳 Credit Card", callback_data="deposit_card"),
            InlineKeyboardButton("🎮 Demo Deposit", callback_data="deposit_demo")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="payment_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
💰 **Deposit Options**

Choose your preferred deposit method:

⭐ **Telegram Stars** - Use Telegram's built-in payment
₿ **Cryptocurrency** - Bitcoin, Ethereum, USDT
💳 **Credit Card** - Visa, Mastercard, etc.
🎮 **Demo Deposit** - For testing (free coins)

**Deposit Limits:**
• Minimum: 100 coins
• Maximum: 100,000 coins per transaction
"""
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show withdrawal options."""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("₿ Cryptocurrency", callback_data="withdraw_crypto"),
            InlineKeyboardButton("💳 Bank Card", callback_data="withdraw_card")
        ],
        [
            InlineKeyboardButton("🅿️ PayPal", callback_data="withdraw_paypal"),
            InlineKeyboardButton("💸 Quick Withdraw", callback_data="withdraw_quick")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="payment_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    available_balance = max(0, user['balance'] - 100)  # Keep 100 coins minimum
    
    text = f"""
💸 **Withdrawal Options**

**Available Balance:** {available_balance:,} coins
*(Keeping 100 coins minimum in account)*

Choose your withdrawal method:

₿ **Cryptocurrency** - Fast & secure
💳 **Bank Card** - 1-3 business days
🅿️ **PayPal** - Instant to 24 hours
💸 **Quick Withdraw** - Pre-set amounts

**Withdrawal Limits:**
• Minimum: 500 coins
• Processing time varies by method
"""
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def process_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process deposit based on selected method."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    method_map = {
        "deposit_stars": ("telegram_stars", "Telegram Stars"),
        "deposit_crypto": ("crypto", "Cryptocurrency"),
        "deposit_card": ("card", "Credit Card"),
        "deposit_demo": ("demo", "Demo")
    }
    
    if query.data not in method_map:
        await query.answer("Invalid deposit method")
        return
    
    method_id, method_name = method_map[query.data]
    
    # For demo purposes, show amount selection
    keyboard = [
        [
            InlineKeyboardButton("100 coins - $1", callback_data=f"deposit_amount_{method_id}_100"),
            InlineKeyboardButton("500 coins - $5", callback_data=f"deposit_amount_{method_id}_500")
        ],
        [
            InlineKeyboardButton("1,000 coins - $10", callback_data=f"deposit_amount_{method_id}_1000"),
            InlineKeyboardButton("5,000 coins - $50", callback_data=f"deposit_amount_{method_id}_5000")
        ],
        [
            InlineKeyboardButton("10,000 coins - $100", callback_data=f"deposit_amount_{method_id}_10000"),
            InlineKeyboardButton("💰 Custom Amount", callback_data=f"deposit_custom_{method_id}")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="payment_deposit")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
💰 **{method_name} Deposit**

Select the amount you want to deposit:

**Exchange Rate:** 1 USD = 100 coins

Choose a preset amount or enter a custom amount:
"""
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def process_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process the actual deposit."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Parse callback data: deposit_amount_{method}_{amount}
    parts = query.data.split('_')
    if len(parts) != 4:
        await query.answer("Invalid deposit request")
        return
    
    method = parts[2]
    amount = int(parts[3])
    
    # Process the deposit
    success, message = await DepositProcessor.process_deposit(
        user_id, amount, method, {}
    )
    
    if success:
        # Show success message
        keyboard = [
            [InlineKeyboardButton("✅ View Balance", callback_data="account_balance")],
            [InlineKeyboardButton("🎮 Play Games", callback_data="games_menu")],
            [InlineKeyboardButton("💼 Payment Center", callback_data="payment_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
✅ **Deposit Successful!**

{message}

**Amount:** {amount:,} coins
**Method:** {method.replace('_', ' ').title()}

Your coins have been added to your account!
"""
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # Show error message
        keyboard = [
            [InlineKeyboardButton("🔄 Try Again", callback_data="payment_deposit")],
            [InlineKeyboardButton("🔙 Payment Center", callback_data="payment_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
❌ **Deposit Failed**

{message}

Please try again or contact support if the problem persists.
"""
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process withdrawal based on selected method."""
    query = update.callback_query
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    method_map = {
        "withdraw_crypto": ("crypto", "Cryptocurrency"),
        "withdraw_card": ("card", "Bank Card"),
        "withdraw_paypal": ("paypal", "PayPal"),
        "withdraw_quick": ("quick", "Quick Withdraw")
    }
    
    if query.data not in method_map:
        await query.answer("Invalid withdrawal method")
        return
    
    method_id, method_name = method_map[query.data]
    available_balance = max(0, user['balance'] - 100)
    
    if method_id == "quick":
        # Quick withdraw with preset amounts
        amounts = [500, 1000, 2500, 5000, 10000]
        keyboard = []
        
        for amount in amounts:
            if amount <= available_balance:
                usd_value = amount / 100
                keyboard.append([InlineKeyboardButton(
                    f"{amount:,} coins (${usd_value})", 
                    callback_data=f"withdraw_amount_crypto_{amount}"
                )])
        
        if available_balance >= 500:
            keyboard.append([InlineKeyboardButton("💰 Custom Amount", callback_data="withdraw_custom_crypto")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="payment_withdraw")])
        
    else:
        # Regular withdrawal amounts
        amounts = [500, 1000, 2500, 5000, available_balance] if available_balance >= 500 else []
        keyboard = []
        
        for amount in amounts:
            if amount > 0 and amount >= 500:
                usd_value = amount / 100
                keyboard.append([InlineKeyboardButton(
                    f"{amount:,} coins (${usd_value})", 
                    callback_data=f"withdraw_amount_{method_id}_{amount}"
                )])
        
        if available_balance >= 500:
            keyboard.append([InlineKeyboardButton("💰 Custom Amount", callback_data=f"withdraw_custom_{method_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="payment_withdraw")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
💸 **{method_name} Withdrawal**

**Available Balance:** {available_balance:,} coins

Select the amount you want to withdraw:

**Exchange Rate:** 100 coins = 1 USD

**Processing Times:**
• Crypto: Instant - 1 hour
• Bank Card: 1-3 business days  
• PayPal: Instant - 24 hours
"""
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def process_withdrawal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process the actual withdrawal."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Parse callback data: withdraw_amount_{method}_{amount}
    parts = query.data.split('_')
    if len(parts) != 4:
        await query.answer("Invalid withdrawal request")
        return
    
    method = parts[2]
    amount = int(parts[3])
    
    # Process the withdrawal
    success, message = await WithdrawalProcessor.process_withdrawal(
        user_id, amount, method, {}
    )
    
    if success:
        # Show success message
        keyboard = [
            [InlineKeyboardButton("📊 Transaction History", callback_data="payment_history")],
            [InlineKeyboardButton("💼 Payment Center", callback_data="payment_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
✅ **Withdrawal Submitted!**

{message}

**Amount:** {amount:,} coins
**Method:** {method.replace('_', ' ').title()}
**USD Value:** ${amount/100:.2f}

Your withdrawal is being processed!
"""
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # Show error message
        keyboard = [
            [InlineKeyboardButton("🔄 Try Again", callback_data="payment_withdraw")],
            [InlineKeyboardButton("🔙 Payment Center", callback_data="payment_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
❌ **Withdrawal Failed**

{message}

Please try again or contact support.
"""
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def transaction_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's transaction history."""
    user_id = update.effective_user.id
    
    transactions = await PaymentProcessor.get_user_transactions(user_id, 10)
    
    if not transactions:
        text = """
📊 **Transaction History**

No transactions found.

Start playing games or make a deposit to see your transaction history here!
"""
        keyboard = [[InlineKeyboardButton("💰 Make Deposit", callback_data="payment_deposit")]]
    else:
        text = "📊 **Transaction History**\n\n"
        
        for tx in transactions:
            status_emoji = {"completed": "✅", "pending": "⏳", "failed": "❌"}.get(tx['status'], "❓")
            type_emoji = {"deposit": "💰", "withdrawal": "💸", "bonus": "🎁", "game_win": "🎉", "game_loss": "💸"}.get(tx['transaction_type'], "💱")
            
            amount_str = f"+{tx['amount']:,}" if tx['transaction_type'] in ['deposit', 'bonus', 'game_win'] else f"-{tx['amount']:,}"
            
            text += f"{status_emoji} {type_emoji} **{tx['transaction_type'].title()}**\n"
            text += f"   Amount: {amount_str} coins\n"
            text += f"   Date: {tx['created_at'][:16]}\n"
            if tx['description']:
                text += f"   Note: {tx['description'][:30]}...\n" if len(tx['description']) > 30 else f"   Note: {tx['description']}\n"
            text += "\n"
        
        keyboard = [
            [InlineKeyboardButton("💰 Deposit", callback_data="payment_deposit"),
             InlineKeyboardButton("💸 Withdraw", callback_data="payment_withdraw")]
        ]
    
    keyboard.append([InlineKeyboardButton("🔙 Payment Center", callback_data="payment_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show payment information and help."""
    text = """
ℹ️ **Payment Information**

**💰 Deposits:**
• Minimum: 100 coins ($1)
• Maximum: 100,000 coins ($1,000)
• Methods: Telegram Stars, Crypto, Cards
• Processing: Instant

**💸 Withdrawals:**
• Minimum: 500 coins ($5)
• Account minimum: 100 coins (kept)
• Methods: Crypto, Bank Card, PayPal
• Processing: Instant to 3 days

**💱 Exchange Rate:**
• 100 coins = $1 USD

**🔒 Security:**
• All transactions are encrypted
• Secure payment processing
• Transaction history tracking
• Instant balance updates

**❓ Support:**
• Contact @CasinoSupport for help
• Transaction issues resolved within 24h
• Refunds processed automatically for failed transactions

**🎮 Gaming:**
• Play responsibly
• Set your own limits
• Take breaks regularly
"""
    
    keyboard = [
        [InlineKeyboardButton("💰 Make Deposit", callback_data="payment_deposit")],
        [InlineKeyboardButton("🔙 Payment Center", callback_data="payment_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
