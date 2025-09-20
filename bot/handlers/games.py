"""
Game Command Handlers

Handles all casino game commands.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database.user import get_user
from bot.games.slots import play_slots, handle_slots_callback
from bot.games.blackjack import start_blackjack, handle_blackjack_callback
from bot.games.roulette import show_roulette_menu, handle_roulette_callback
from bot.games.dice import show_dice_menu, handle_dice_callback
from bot.games.poker import show_poker_menu, handle_poker_callback


async def slots(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /slots command."""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("❌ Please use /start first to register.")
        return
    
    if user_data['balance'] < 10:
        await update.message.reply_text("❌ You need at least 10 chips to play slots! Use /daily for free chips.")
        return
    
    # Show betting options
    keyboard = [
        [
            InlineKeyboardButton("10 chips", callback_data="slots_bet_10"),
            InlineKeyboardButton("25 chips", callback_data="slots_bet_25")
        ],
        [
            InlineKeyboardButton("50 chips", callback_data="slots_bet_50"),
            InlineKeyboardButton("100 chips", callback_data="slots_bet_100")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    slots_text = f"""
🎰 **SLOT MACHINE** 🎰

Current Balance: **{user_data['balance']} chips**

Choose your bet amount:

**Payouts:**
🍒🍒🍒 = 10x bet
🍋🍋🍋 = 20x bet
🍊🍊🍊 = 30x bet
🔔🔔🔔 = 50x bet
💎💎💎 = 100x bet

Good luck! 🍀
"""
    
    await update.message.reply_text(slots_text, reply_markup=reply_markup, parse_mode='Markdown')


async def blackjack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /blackjack command."""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("❌ Please use /start first to register.")
        return
    
    if user_data['balance'] < 20:
        await update.message.reply_text("❌ You need at least 20 chips to play blackjack! Use /daily for free chips.")
        return
    
    # Show betting options
    keyboard = [
        [
            InlineKeyboardButton("20 chips", callback_data="blackjack_bet_20"),
            InlineKeyboardButton("50 chips", callback_data="blackjack_bet_50")
        ],
        [
            InlineKeyboardButton("100 chips", callback_data="blackjack_bet_100"),
            InlineKeyboardButton("200 chips", callback_data="blackjack_bet_200")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    blackjack_text = f"""
🃏 **BLACKJACK** 🃏

Current Balance: **{user_data['balance']} chips**

**Rules:**
• Get as close to 21 as possible
• Don't go over 21 (bust)
• Dealer must hit on 16, stand on 17
• Blackjack pays 3:2

Choose your bet amount:
"""
    
    await update.message.reply_text(blackjack_text, reply_markup=reply_markup, parse_mode='Markdown')


async def roulette(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /roulette command."""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("❌ Please use /start first to register.")
        return
    
    if user_data['balance'] < 15:
        await update.message.reply_text("❌ You need at least 15 chips to play roulette! Use /daily for free chips.")
        return
    
    await show_roulette_menu(update, user_data['balance'])


async def dice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /dice command."""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("❌ Please use /start first to register.")
        return
    
    if user_data['balance'] < 10:
        await update.message.reply_text("❌ You need at least 10 chips to play dice! Use /daily for free chips.")
        return
    
    await show_dice_menu(update, user_data['balance'])


async def poker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /poker command."""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("❌ Please use /start first to register.")
        return
    
    if user_data['balance'] < 25:
        await update.message.reply_text("❌ You need at least 25 chips to play poker! Use /daily for free chips.")
        return
    
    await show_poker_menu(update, user_data['balance'])


async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /achievements command."""
    user_id = update.effective_user.id
    from bot.utils.achievements import show_achievements_menu
    await show_achievements_menu(update, user_id)


async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the games menu."""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("❌ Please use /start first to register.")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("🎰 Slots", callback_data="game_slots"),
            InlineKeyboardButton("🃏 Blackjack", callback_data="game_blackjack")
        ],
        [
            InlineKeyboardButton("🎲 Roulette", callback_data="game_roulette"),
            InlineKeyboardButton("🎯 Dice", callback_data="game_dice")
        ],
        [
            InlineKeyboardButton("🃏 Poker", callback_data="game_poker"),
            InlineKeyboardButton("🏆 Achievements", callback_data="check_achievements")
        ],
        [
            InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
🎮 **Game Center**

**Your Balance:** {user_data['balance']:,} chips

Choose a game to play:

🎰 **Slots** - Classic slot machine
🃏 **Blackjack** - Beat the dealer
🎲 **Roulette** - Spin the wheel
🎯 **Dice** - Multiple dice games
🃏 **Poker** - Texas Hold'em
"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def mini_casino_app(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Unified mini casino app: lets users play all games from a single interactive menu.
    """
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    if not user_data:
        await update.message.reply_text("❌ Please use /start first to register.")
        return
    keyboard = [
        [InlineKeyboardButton("🎰 Slots", callback_data="mini_slots"), InlineKeyboardButton("🃏 Blackjack", callback_data="mini_blackjack")],
        [InlineKeyboardButton("🎲 Roulette", callback_data="mini_roulette"), InlineKeyboardButton("🎯 Dice", callback_data="mini_dice")],
        [InlineKeyboardButton("🃏 Poker", callback_data="mini_poker"), InlineKeyboardButton("🏆 Achievements", callback_data="mini_achievements")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"""
🎮 **Mini Casino App**

Your Balance: **{user_data['balance']} chips**

Select a game to play below:
"""
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def mini_casino_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback router for the mini casino app.
    """
    query = update.callback_query
    data = query.data
    if data == "mini_slots":
        await slots(update, context)
    elif data == "mini_blackjack":
        await blackjack(update, context)
    elif data == "mini_roulette":
        await roulette(update, context)
    elif data == "mini_dice":
        await dice(update, context)
    elif data == "mini_poker":
        await poker(update, context)
    elif data == "mini_achievements":
        await achievements(update, context)
    elif data == "main_menu":
        # You can route to your main menu handler here
        await update.callback_query.edit_message_text("🏠 Main menu coming soon!")
    else:
        await query.answer("❌ Unknown mini app action!")
