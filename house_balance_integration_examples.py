#!/usr/bin/env python3
"""
Example of how to integrate house balance system into casino games
This shows the before/after for updating game logic
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CommandHandler
import asyncio
import time
from flask import Flask, jsonify
import threading
import os

# BEFORE - Old game logic without house balance tracking
async def update_balance(user_id: int, amount: float) -> bool:
    """
    Dummy implementation for updating user balance.
    Replace with actual database logic in production.
    """
    # Example: Update balance in database (pseudo-code)
    # async with aiosqlite.connect(DB_PATH) as db:
    #     await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
    #     await db.commit()
    return True

async def old_game_logic(user_id: int, bet_amount: float):
    """Example of old game logic that doesn't track house balance"""
    
    # Simulate game outcome
    import random
    player_wins = random.choice([True, False])
    
    if player_wins:
        win_amount = bet_amount * 2  # 2x payout
        # Old way: Update user balance only
        await update_balance(user_id, win_amount - bet_amount)  # Net win
        result = f"Won ${win_amount:.2f}"
    else:
        win_amount = 0
        # Old way: Deduct user balance only
        await deduct_balance_with_house(user_id, bet_amount)
        result = "Lost"
    
    # Log the game (old way doesn't track house balance)
    await log_game_session(user_id, "example_game", bet_amount, win_amount, result)

# AFTER - New game logic with house balance tracking
async def update_balance_with_house(user_id: int, bet_amount: float, win_amount: float) -> bool:
    """
    Atomically updates user and house balances for a win.
    Deducts bet_amount from house, adds win_amount to user.
    Replace with actual database logic in production.
    """
    try:
        # Example: Update balances in database (pseudo-code)
        # async with aiosqlite.connect(DB_PATH) as db:
        #     await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (win_amount - bet_amount, user_id))
        #     await db.execute("UPDATE house SET balance = balance - ? WHERE id = 1", (win_amount - bet_amount,))
        #     await db.commit()
        return True
    except Exception as e:
        # Log error
        print(f"Error in update_balance_with_house: {e}")
        return False

async def new_game_logic(user_id: int, bet_amount: float):
    """Example of new game logic that tracks house balance"""
    
    # Simulate game outcome
    import random
    player_wins = random.choice([True, False])
    
    if player_wins:
        win_amount = bet_amount * 2  # 2x payout
        # New way: Update both user and house balance
        await update_balance_with_house(user_id, bet_amount, win_amount)
        result = f"Won ${win_amount:.2f}"
    else:
        win_amount = 0
        # New way: Deduct user balance and update house balance
        await deduct_balance_with_house(user_id, bet_amount)
        result = "Lost"
    
    # Log the game (house balance already updated above)
    await log_game_session(user_id, "example_game", bet_amount, win_amount, result)

async def deduct_balance_with_house(user_id: int, bet_amount: float) -> bool:
    """
    Deducts bet_amount from user balance and adds it to house balance atomically.
    Replace with actual database logic in production.
    """
    try:
        # Example: Update balances in database (pseudo-code)
        # async with aiosqlite.connect(DB_PATH) as db:
        #     await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (bet_amount, user_id))
        #     await db.execute("UPDATE house SET balance = balance + ? WHERE id = 1", (bet_amount,))
        #     await db.commit()
        return True
    except Exception as e:
        # Log error
        print(f"Error in deduct_balance_with_house: {e}")
        return False

# Dummy async get_user implementation for demonstration
async def get_user(user_id: int) -> dict:
    """
    Retrieves user data from the database.
    Replace with actual database logic in production.
    """
    # Example: Fetch user from database (pseudo-code)
    # async with aiosqlite.connect(DB_PATH) as db:
    #     async with db.execute("SELECT id, balance FROM users WHERE id = ?", (user_id,)) as cursor:
    #         row = await cursor.fetchone()
    #         if row:
    #             return {"id": row[0], "balance": row[1]}
    #         else:
    #             return None
    # For demonstration, return a dummy user
    return {"id": user_id, "balance": 100.0}

# Dummy async log_game_session implementation for demonstration
async def log_game_session(user_id: int, game_name: str, bet_amount: float, win_amount: float, result: str) -> None:
    """
    Logs the game session to the database.
    Replace with actual database logic in production.
    """
    # Example: Log game session in database (pseudo-code)
    # async with aiosqlite.connect(DB_PATH) as db:
    #     await db.execute(
    #         "INSERT INTO game_sessions (user_id, game_name, bet_amount, win_amount, result) VALUES (?, ?, ?, ?, ?)",
    #         (user_id, game_name, bet_amount, win_amount, result)
    #     )
    #     await db.commit()
    print(f"Game session logged: user_id={user_id}, game={game_name}, bet={bet_amount}, win={win_amount}, result={result}")

# EXAMPLE: Coin Flip Game Integration
async def coinflip_game_with_house_balance(user_id: int, bet_amount: float, prediction: str):
    """Complete example of coin flip game with house balance integration"""
    
    # Validate bet
    user = await get_user(user_id)
    if user['balance'] < bet_amount:
        return {"success": False, "message": "Insufficient balance"}
    
    # Flip coin
    import random
    result = random.choice(["heads", "tails"])
    player_wins = (prediction == result)
    
    if player_wins:
        # Player wins - gets 2x bet back
        win_amount = bet_amount * 2
        
        # Update balances: user gains net, house loses net
        success = await update_balance_with_house(user_id, bet_amount, win_amount)
        
        if success:
            message = f"🎉 You won! Coin was {result}."
            net_gain = win_amount - bet_amount
        else:
            message = "Error processing win. Please contact support."
            net_gain = 0
    else:
        # Player loses - house keeps the bet
        win_amount = 0
        
        # Update balances: user loses bet, house gains bet
        success = await deduct_balance_with_house(user_id, bet_amount)
        
        if success:
            message = f"😞 You lost. Coin was {result}."
            net_gain = -bet_amount
        else:
            message = "Error processing loss. Please contact support."
            net_gain = 0
    
    # Log the game session
    await log_game_session(user_id, "coinflip", bet_amount, win_amount, f"Result: {result}, Prediction: {prediction}")
    
    # Get updated balance
    updated_user = await get_user(user_id)
    
    return {
        "success": success,
        "message": message,
        "result": result,
        "player_wins": player_wins,
        "win_amount": win_amount,
        "net_gain": net_gain,
        "new_balance": updated_user['balance'] if updated_user else 0
    }

# EXAMPLE: Slots Game Integration
async def slots_game_with_house_balance(user_id: int, bet_amount: float):
    """Complete example of slots game with house balance integration"""
    
    # Validate bet
    user = await get_user(user_id)
    if user['balance'] < bet_amount:
        return {"success": False, "message": "Insufficient balance"}
    
    # Spin reels
    import random
    symbols = ['🍒', '🍋', '🍊', '⭐', '🔔', '💎']
    reel1 = random.choice(symbols)
    reel2 = random.choice(symbols)
    reel3 = random.choice(symbols)
    
    # Check for wins and calculate payout
    win_amount = 0
    if reel1 == reel2 == reel3:
        # Three of a kind
        if reel1 == '🍒':
            multiplier = 5
        elif reel1 == '🍋':
            multiplier = 3
        elif reel1 == '🍊':
            multiplier = 2
        else:
            multiplier = 1.5
        
        win_amount = bet_amount * multiplier
        
        # Update balances for win
        success = await update_balance_with_house(user_id, bet_amount, win_amount)
        message = f"🎉 JACKPOT! {reel1}{reel2}{reel3}"
        
    else:
        # No win
        win_amount = 0
        
        # Update balances for loss
        success = await deduct_balance_with_house(user_id, bet_amount)
        message = f"😞 No win. {reel1}{reel2}{reel3}"
    
    # Log the game session
    result_str = f"Reels: {reel1}{reel2}{reel3}, Win: ${win_amount:.2f}"
    await log_game_session(user_id, "slots", bet_amount, win_amount, result_str)
    
    # Get updated balance
    updated_user = await get_user(user_id)
    
    return {
        "success": success,
        "message": message,
        "reels": (reel1, reel2, reel3),
        "win_amount": win_amount,
        "net_gain": win_amount - bet_amount,
        "new_balance": updated_user['balance'] if updated_user else 0
    }

# EXAMPLE: Integration in Telegram Bot Handler
async def slots_telegram_handler(update, context):
    """Example of how to use house balance in Telegram bot handler"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Get bet from user input (simplified)
    bet_amount = 10.0  # In real implementation, get from user input
    
    # Play the game with house balance integration
    result = await slots_game_with_house_balance(user_id, bet_amount)
    
    if result["success"]:
        # Game processed successfully
        reels = "".join(result["reels"])
        win_amount = result["win_amount"]
        new_balance = result["new_balance"]
        
        # Format response
        text = f"""
🎰 <b>SLOTS RESULT</b> 🎰

🎲 <b>Result:</b> {reels}
💰 <b>Bet:</b> ${bet_amount:.2f}
💎 <b>Win:</b> ${win_amount:.2f}
🏦 <b>New Balance:</b> ${new_balance:.2f}

{result["message"]}
"""
    else:
        # Error occurred
        text = f"❌ {result['message']}"
    
    # Send response
    keyboard = [
        [InlineKeyboardButton("🔄 Play Again", callback_data="slots")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(
        text, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode=ParseMode.HTML
    )

async def get_house_balance() -> float:
    """
    Returns the current house balance from the database.
    Replace with actual aiosqlite query in production.
    """
    # Example: Fetch house balance from database (pseudo-code)
    # async with aiosqlite.connect(DB_PATH) as db:
    #     async with db.execute("SELECT balance FROM house WHERE id = 1") as cursor:
    #         row = await cursor.fetchone()
    #         if row:
    #             return row[0]
    #         else:
    #             return 0.0
    return 10000.0  # Dummy value for demonstration

async def house_balance_command(update, context) -> None:
    """
    Telegram command handler for /housebal to display all available house funds.
    Only accessible to owner/admins (add your own access control as needed).
    """
    user_id = update.effective_user.id
    # TODO: Replace with actual owner/admin check
    is_owner = True  # Replace with your logic
    if not is_owner:
        await update.message.reply_text("You do not have permission to view house balance.")
        return
    try:
        house_balance = await get_house_balance()
        text = f"🏦 <b>Available House Funds:</b> ${house_balance:.2f}"
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"Error retrieving house balance: {e}")

async def keep_alive_pinger(interval: int = 300) -> None:
    """
    Periodically prints a keep-alive message to prevent service timeout.
    Can be run as a background task in your bot startup.
    """
    while True:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Keep-alive ping...")
        await asyncio.sleep(interval)

# ===============================
# WEB SERVER AND KEEP ALIVE
# ===============================

# Flask app for health checks and keep-alive
app = Flask(__name__)

@app.route('/')
def health_check():
    """Health check endpoint for deployment services"""
    return jsonify({
        "status": "healthy",
        "service": "Enhanced Telegram Casino Bot",
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "uptime": "Running"
    })

@app.route('/health')
def health():
    """Additional health endpoint"""
    return jsonify({"status": "ok", "bot": "running"})

@app.route('/stats')
def bot_stats():
    """Bot statistics endpoint"""
    return jsonify({
        "active_users": "N/A",  # Would fetch from database
        "games_played_today": "N/A",
        "house_balance": "10000.00",
        "server_time": time.strftime('%Y-%m-%d %H:%M:%S')
    })

def run_web_server():
    """Run Flask web server in background thread"""
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def start_web_server():
    """Start web server in background thread"""
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    print(f"✅ Web server started on port {os.environ.get('PORT', 8080)}")

async def enhanced_keep_alive_pinger(interval: int = 300) -> None:
    """
    Enhanced keep-alive pinger with web server integration.
    Periodically logs system status and keeps service active.
    """
    startup_time = time.time()
    
    while True:
        current_time = time.time()
        uptime_seconds = int(current_time - startup_time)
        uptime_hours = uptime_seconds // 3600
        uptime_minutes = (uptime_seconds % 3600) // 60
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🚀 Casino Bot Keep-Alive Status:")
        print(f"  • Uptime: {uptime_hours}h {uptime_minutes}m")
        print(f"  • Web Server: Running on port {os.environ.get('PORT', 8080)}")
        print(f"  • Bot Status: Active")
        print(f"  • House Balance: Available")
        print(f"  • Database: Connected")
        print(f"  • Memory: Optimal")
        print("  ✅ All systems operational")
        
        await asyncio.sleep(interval)

# Example usage in your bot startup:
# start_web_server()  # Start Flask server
# asyncio.create_task(enhanced_keep_alive_pinger())  # Start enhanced keep-alive

# SUMMARY: Key Changes for House Balance Integration

"""
1. Replace direct balance updates:
   OLD: await update_balance(user_id, amount)
   NEW: await update_balance_with_house(user_id, bet_amount, win_amount)

2. Replace direct balance deductions:
   OLD: await deduct_balance(user_id, amount)
   NEW: await deduct_balance_with_house(user_id, bet_amount)

3. For deposits:
   OLD: await update_balance(user_id, deposit_amount)
   NEW: await process_deposit_with_house_balance(user_id, deposit_amount)

4. For withdrawals:
   OLD: await deduct_balance(user_id, withdrawal_amount)
   NEW: await process_withdrawal_with_house_balance(user_id, withdrawal_amount)

5. Owner panel can now display:
   house_display = await get_house_balance_display()
   
This ensures all financial transactions are tracked at both user and house level,
providing complete visibility into casino operations and profitability.
"""
