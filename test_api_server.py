#!/usr/bin/env python3
"""
Test script for the casino web API without Telegram bot
"""
import asyncio
import aiosqlite
import os
import sys
from dotenv import load_dotenv
from aiohttp import web
import json
import random
import uuid
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()
DB_PATH = os.environ.get("CASINO_DB", "casino.db")
PORT = int(os.environ.get("PORT", "3000"))

# --- Database Functions ---
async def init_db():
    """Initialize database"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                balance INTEGER DEFAULT 1000,
                games_played INTEGER DEFAULT 0,
                total_wagered INTEGER DEFAULT 0,
                total_won INTEGER DEFAULT 0,
                created_at TEXT DEFAULT '',
                last_active TEXT DEFAULT ''
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                game_type TEXT NOT NULL,
                bet_amount INTEGER NOT NULL,
                win_amount INTEGER DEFAULT 0,
                result TEXT NOT NULL,
                timestamp TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        await db.commit()
    logger.info("✅ Database initialized")

async def get_user(user_id: int):
    """Get user data"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT id, username, balance, games_played, total_wagered, total_won, created_at, last_active 
            FROM users WHERE id = ?
        """, (user_id,))
        row = await cur.fetchone()
        if row:
            return dict(row)
        return None

async def create_user(user_id: int, username: str):
    """Create new user"""
    current_time = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users 
            (id, username, balance, created_at, last_active) 
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, 1000, current_time, current_time))
        await db.commit()
    return await get_user(user_id)

async def update_balance(user_id: int, amount: int):
    """Update user balance"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
        await db.commit()

async def deduct_balance(user_id: int, amount: int):
    """Deduct balance with validation"""
    user = await get_user(user_id)
    if not user or user['balance'] < amount:
        return False
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET 
                balance = balance - ?, 
                total_wagered = total_wagered + ?, 
                games_played = games_played + 1 
            WHERE id = ?
        """, (amount, amount, user_id))
        await db.commit()
    
    return True

async def log_game_session(user_id: int, game_type: str, bet_amount: int, win_amount: int, result: str):
    """Log game session"""
    session_id = str(uuid.uuid4())
    current_time = datetime.now().isoformat()
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO game_sessions 
            (id, user_id, game_type, bet_amount, win_amount, result, timestamp) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, game_type, bet_amount, win_amount, result, current_time))
        await db.commit()

# --- Game Functions ---
async def play_slots(user_id: int, bet_amount: int):
    """Slots game logic"""
    success = await deduct_balance(user_id, bet_amount)
    if not success:
        return {'error': 'Insufficient balance'}
    
    symbols = ['🍒', '🍋', '🍊', '🍇', '🔔', '⭐', '💎']
    reels = [random.choice(symbols) for _ in range(3)]
    
    win_amount = 0
    win = False
    
    if reels[0] == reels[1] == reels[2]:
        if reels[0] == '💎':
            win_amount = bet_amount * 10
        elif reels[0] == '⭐':
            win_amount = bet_amount * 5
        else:
            win_amount = bet_amount * 3
        win = True
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        win_amount = bet_amount * 2
        win = True
    
    if win_amount > 0:
        await update_balance(user_id, win_amount)
    
    await log_game_session(user_id, 'slots', bet_amount, win_amount, f'{"|".join(reels)}')
    
    user = await get_user(user_id)
    
    return {
        'success': True,
        'win': win,
        'symbols': reels,
        'payout': win_amount,
        'bet_amount': bet_amount,
        'new_balance': user['balance']
    }

async def play_coinflip(user_id: int, bet_amount: int, data: dict):
    """Coin flip game logic"""
    choice = data.get('choice', 'heads')
    
    success = await deduct_balance(user_id, bet_amount)
    if not success:
        return {'error': 'Insufficient balance'}
    
    result = random.choice(['heads', 'tails'])
    win = choice == result
    win_amount = bet_amount * 2 if win else 0
    
    if win_amount > 0:
        await update_balance(user_id, win_amount)
    
    await log_game_session(user_id, 'coinflip', bet_amount, win_amount, f'{choice}:{result}')
    
    user = await get_user(user_id)
    
    return {
        'success': True,
        'win': win,
        'result': result,
        'choice': choice,
        'payout': win_amount,
        'bet_amount': bet_amount,
        'new_balance': user['balance']
    }

async def play_dice(user_id: int, bet_amount: int, data: dict):
    """Dice game logic"""
    prediction = data.get('prediction', 'over')
    target_number = data.get('target_number', 1)
    
    success = await deduct_balance(user_id, bet_amount)
    if not success:
        return {'error': 'Insufficient balance'}
    
    roll = random.randint(1, 6)
    win = False
    win_amount = 0
    
    if prediction == 'over' and roll > 3:
        win = True
        win_amount = bet_amount * 2
    elif prediction == 'under' and roll <= 3:
        win = True
        win_amount = bet_amount * 2
    elif prediction == 'exact' and roll == target_number:
        win = True
        win_amount = bet_amount * 6
    
    if win_amount > 0:
        await update_balance(user_id, win_amount)
    
    await log_game_session(user_id, 'dice', bet_amount, win_amount, f'{prediction}:{roll}')
    
    user = await get_user(user_id)
    
    return {
        'success': True,
        'win': win,
        'roll': roll,
        'prediction': prediction,
        'payout': win_amount,
        'bet_amount': bet_amount,
        'new_balance': user['balance']
    }

async def play_plinko(user_id: int, bet_amount: int, data: dict):
    """Plinko game logic"""
    risk = data.get('risk', 'medium')
    
    success = await deduct_balance(user_id, bet_amount)
    if not success:
        return {'error': 'Insufficient balance'}
    
    # Define multipliers based on risk level
    multipliers = {
        'low': [0.5, 1.0, 1.2, 1.5, 1.2, 1.0, 0.5],
        'medium': [0.2, 0.8, 1.5, 2.0, 1.5, 0.8, 0.2],
        'high': [0.1, 0.5, 1.0, 5.0, 1.0, 0.5, 0.1]
    }
    
    # Simulate ball drop
    slot_multipliers = multipliers.get(risk, multipliers['medium'])
    slot = random.randint(0, len(slot_multipliers) - 1)
    multiplier = slot_multipliers[slot]
    
    win_amount = int(bet_amount * multiplier)
    win = multiplier >= 1.0
    
    if win_amount > 0:
        await update_balance(user_id, win_amount)
    
    await log_game_session(user_id, 'plinko', bet_amount, win_amount, f'{risk}:{slot}:{multiplier}')
    
    user = await get_user(user_id)
    
    return {
        'success': True,
        'win': win,
        'slot': slot,
        'multiplier': f'{multiplier}x',
        'payout': win_amount,
        'bet_amount': bet_amount,
        'new_balance': user['balance']
    }

# --- API Handlers ---
async def handle_game_action(request):
    """Handle game actions from WebApp"""
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        game_type = data.get('game_type')
        bet_amount = int(data.get('bet_amount', 0))
        
        # Create user if doesn't exist (for testing)
        user = await get_user(user_id)
        if not user:
            user = await create_user(user_id, f"TestUser_{user_id}")
        
        # Validate bet amount
        if bet_amount > user['balance']:
            return web.json_response({'error': 'Insufficient balance'}, status=400)
        
        if bet_amount <= 0:
            return web.json_response({'error': 'Invalid bet amount'}, status=400)
        
        # Process game based on type
        if game_type == 'slots':
            result = await play_slots(user_id, bet_amount)
        elif game_type == 'coinflip':
            result = await play_coinflip(user_id, bet_amount, data)
        elif game_type == 'dice':
            result = await play_dice(user_id, bet_amount, data)
        elif game_type == 'plinko':
            result = await play_plinko(user_id, bet_amount, data)
        else:
            return web.json_response({'error': f'{game_type} not implemented in test server'}, status=400)
        
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"Game action error: {e}")
        return web.json_response({'error': 'Internal server error'}, status=500)

async def get_user_balance(request):
    """Get user balance API endpoint"""
    try:
        user_id = int(request.query.get('user_id'))
        user = await get_user(user_id)
        if not user:
            # Create user for testing
            user = await create_user(user_id, f"TestUser_{user_id}")
        
        return web.json_response({
            'success': True,
            'balance': user['balance'],
            'username': user['username']
        })
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def casino_webapp(request):
    """Serve the casino WebApp"""
    user_id = request.query.get('user_id', '12345')  # Default test user
    balance = request.query.get('balance', '1000')
    
    try:
        with open('casino_webapp_new.html', 'r', encoding='utf-8') as f:
            html = f.read()
        
        # Replace placeholders
        html = html.replace('{BALANCE}', str(balance))
        html = html.replace('{USER_ID}', str(user_id))
        
        return web.Response(text=html, content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="Casino WebApp not found", status=404)

async def health_check(request):
    """Health check endpoint"""
    return web.json_response({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "casino-api-test"
    })

async def main():
    """Main test server"""
    try:
        # Initialize database
        await init_db()
        
        # Create web app
        app = web.Application()
        app.router.add_get('/health', health_check)
        app.router.add_get('/', casino_webapp)
        app.router.add_get('/casino', casino_webapp)
        app.router.add_post('/api/game', handle_game_action)
        app.router.add_get('/api/balance', get_user_balance)
        
        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        
        logger.info(f"🚀 Casino API test server started!")
        logger.info(f"🌐 WebApp: http://localhost:{PORT}/casino")
        logger.info(f"🎮 Game API: http://localhost:{PORT}/api/game")
        logger.info(f"💰 Balance API: http://localhost:{PORT}/api/balance")
        logger.info(f"❤️ Health: http://localhost:{PORT}/health")
        logger.info("Press Ctrl+C to stop")
        
        # Keep running
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        
if __name__ == "__main__":
    asyncio.run(main())
