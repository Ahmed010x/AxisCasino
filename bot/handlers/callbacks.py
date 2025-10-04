"""
Callback Query Handlers

Handles all inline button callbacks from the bot interface.
"""

from telegram import Update
from telegram.ext import ContextTypes
from bot.handlers.start import help_command
from bot.handlers.account import balance, daily_bonus, stats
from bot.games.slots import handle_slots_callback
from bot.games.blackjack import handle_blackjack_callback
from bot.games.roulette import handle_roulette_callback
from bot.games.dice import handle_dice_callback
from bot.games.basketball import handle_basketball_callback
from bot.utils.achievements import handle_achievements_callback
from bot.handlers.leaderboard import handle_leaderboard_callback
from bot.handlers.payment_handlers import (
    payments_menu, deposit_menu, withdraw_menu, process_deposit,
    process_deposit_amount, process_withdrawal, process_withdrawal_amount,
    transaction_history, payment_info
)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Main menu callbacks
    if data == "main_menu":
        from bot.handlers.start import start
        await start(update, context)
    elif data == "check_balance":
        await balance(update, context)
    elif data == "daily_bonus":
        await daily_bonus(update, context)
    elif data == "check_stats":
        await stats(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data == "games_menu":
        from bot.handlers.games import games_menu
        await games_menu(update, context)
    elif data == "account_balance":
        await balance(update, context)
    
    # Game launch callbacks
    elif data == "game_slots":
        from bot.handlers.games import slots
        await slots(update, context)
    elif data == "game_blackjack":
        from bot.handlers.games import blackjack
        await blackjack(update, context)
    elif data == "game_roulette":
        from bot.handlers.games import roulette
        await roulette(update, context)
    elif data == "game_dice":
        from bot.handlers.games import dice
        await dice(update, context)
    elif data == "game_basketball":
        from bot.handlers.games import basketball
        await basketball(update, context)
    
    # Achievement callbacks
    elif data.startswith("check_achievements") or data.startswith("achievements_"):
        await handle_achievements_callback(update, context)
    
    # Leaderboard callbacks
    elif data.startswith("leaderboard_"):
        await handle_leaderboard_callback(update, context)
    
    # Game-specific callbacks
    elif data.startswith("slots_"):
        await handle_slots_callback(update, context)
    elif data.startswith("blackjack_"):
        await handle_blackjack_callback(update, context)
    elif data.startswith("roulette_"):
        await handle_roulette_callback(update, context)
    elif data.startswith("dice_"):
        await handle_dice_callback(update, context)
    elif data.startswith("basketball_"):
        await handle_basketball_callback(update, context)
    
    # Payment callbacks
    elif data == "payment_menu":
        await payments_menu(update, context)
    elif data == "payment_deposit":
        await deposit_menu(update, context)
    elif data == "payment_withdraw":
        await withdraw_menu(update, context)
    elif data == "payment_history":
        await transaction_history(update, context)
    elif data == "payment_info":
        await payment_info(update, context)
    elif data.startswith("deposit_"):
        if data.startswith("deposit_amount_"):
            await process_deposit_amount(update, context)
        else:
            await process_deposit(update, context)
    elif data.startswith("withdraw_"):
        if data.startswith("withdraw_amount_"):
            await process_withdrawal_amount(update, context)
        else:
            await process_withdrawal(update, context)
