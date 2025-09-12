# bot.py
"""
Enhanced Telegram Casino Bot v2.0
Professional-grade casino with security, anti-fraud, and comprehensive features.
Stake-style interface with advanced game mechanics and user protection.
"""

import os
import asyncio
import logging
import uuid
import signal
import sys
from datetime import datetime
from dotenv import load_dotenv
import aiohttp
import aiohttp.web

import aiosqlite
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User as TelegramUser
)
from telegram.constants import ParseMode

# Initialize logging early
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Try to import WebApp components - handle version compatibility
try:
    from telegram import WebAppInfo as WebApp, MenuButtonWebApp
    WEBAPP_IMPORTS_AVAILABLE = True
    logger.info("✅ WebApp imports available")
except ImportError:
    # Fallback for older versions
    WEBAPP_IMPORTS_AVAILABLE = False
    logger.warning("⚠️ WebApp imports not available - using compatibility mode")
    
    # Create dummy classes for compatibility
    class WebApp:
        def __init__(self, url):
            self.url = url
    
    class MenuButtonWebApp:
        def __init__(self, text, web_app):
            self.text = text
            self.web_app = web_app
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from telegram.error import TelegramError, BadRequest, Forbidden

# --- Config ---
load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_PATH = os.environ.get("CASINO_DB", "casino.db")

# Render hosting configuration
PORT = int(os.environ.get("PORT", "3000"))
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL", "300"))  # 5 minutes default

if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN in environment or .env")

# Security Configuration
MAX_BET_PER_GAME = int(os.environ.get("MAX_BET_PER_GAME", "1000"))
MAX_DAILY_LOSSES = int(os.environ.get("MAX_DAILY_LOSSES", "5000"))
ANTI_SPAM_WINDOW = int(os.environ.get("ANTI_SPAM_WINDOW", "10"))  # seconds
MAX_COMMANDS_PER_WINDOW = int(os.environ.get("MAX_COMMANDS_PER_WINDOW", "20"))

# Admin Configuration
ADMIN_USER_IDS = list(map(int, os.environ.get("ADMIN_USER_IDS", "").split(","))) if os.environ.get("ADMIN_USER_IDS") else []
SUPPORT_CHANNEL = os.environ.get("SUPPORT_CHANNEL", "@casino_support")
BOT_VERSION = "2.0.1"

# WebApp Configuration  
# Auto-detect environment and set appropriate WebApp URL
if RENDER_EXTERNAL_URL:
    # Production environment (Render)
    default_webapp_url = f"{RENDER_EXTERNAL_URL}/casino"
else:
    # Local development environment
    default_webapp_url = f"http://localhost:{PORT}/casino"

WEBAPP_URL = os.environ.get("WEBAPP_URL", default_webapp_url)
WEBAPP_ENABLED = os.environ.get("WEBAPP_ENABLED", "true").lower() == "true"
WEBAPP_SECRET_KEY = os.environ.get("WEBAPP_SECRET_KEY", "your-secret-key-here")

print("🎰 Mini App Integration Status:")
print(f"✅ WebApp URL: {WEBAPP_URL}")
print(f"✅ WebApp Enabled: {WEBAPP_ENABLED}")
print(f"✅ Secret Key: {'Set' if WEBAPP_SECRET_KEY != 'your-secret-key-here' else 'Default'}")
print(f"✅ Server Port: {PORT}")

# Rest of the configuration (keeping existing)
# VIP Level Requirements
VIP_SILVER_REQUIRED = int(os.environ.get("VIP_SILVER_REQUIRED", "1000"))
VIP_GOLD_REQUIRED = int(os.environ.get("VIP_GOLD_REQUIRED", "5000"))
VIP_DIAMOND_REQUIRED = int(os.environ.get("VIP_DIAMOND_REQUIRED", "10000"))

# Game Configuration
WEEKLY_BONUS_RATE = float(os.environ.get("WEEKLY_BONUS_RATE", "0.05"))  # 5% of weekly bets
MIN_SLOTS_BET = int(os.environ.get("MIN_SLOTS_BET", "10"))
MIN_BLACKJACK_BET = int(os.environ.get("MIN_BLACKJACK_BET", "20"))

# --- Production Database System ---
async def init_db():
    """Initialize production database"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 1000,
                games_played INTEGER DEFAULT 0,
                total_wagered INTEGER DEFAULT 0,
                total_won INTEGER DEFAULT 0,
                created_at TEXT DEFAULT '',
                last_active TEXT DEFAULT ''
            )
        """)
        
        # Game sessions table
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
        
        # Create indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_balance ON users (balance)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_game_sessions_user ON game_sessions (user_id)")
        
        await db.commit()
    logger.info(f"✅ Production database initialized at {DB_PATH}")

async def get_user(user_id: int):
    """Get user data from database"""
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
    user = await get_user(user_id)
    return user['balance'] if user else 0

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
    
    return session_id

# --- Start Command ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or f"User_{user_id}"
    
    # Get or create user
    user_data = await get_user(user_id)
    if not user_data:
        user_data = await create_user(user_id, username)
        welcome_message = "🎉 *Welcome! You've received 1,000 chips to start!*"
    else:
        welcome_message = f"👋 *Welcome back, {user_data['username']}!*"
    
    text = f"""
🎰 **CASINO BOT** 🎰

{welcome_message}

💰 **Balance: {user_data['balance']:,} chips**
🏆 **Games Played: {user_data['games_played']}**

Choose an action below:
"""
    
    keyboard = [
        [InlineKeyboardButton("🎮 Mini App Centre", callback_data="mini_app_centre"), InlineKeyboardButton("💰 Check Balance", callback_data="show_balance")],
        [InlineKeyboardButton("🎁 Bonuses", callback_data="bonus_centre"), InlineKeyboardButton("📊 My Statistics", callback_data="show_stats")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard"), InlineKeyboardButton("ℹ️ Help & Info", callback_data="show_help")]
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Mini App Centre ---
async def show_mini_app_centre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the comprehensive Mini App Centre with WebApp integration"""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    balance = user['balance']
    total_games = user['games_played']
    username = user['username']
    
    text = f"""
🎮 **CASINO MINI APP CENTRE** 🎮
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎲 **{username}** | Balance: **{balance:,}** chips
🎯 **Games Played:** {total_games}

� **WEBAPP CASINO**
*Full casino experience in your browser*
• � All games in one place
• 📱 Mobile-optimized interface
• ⚡ Real-time updates
• 🎮 Smooth gaming experience

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎁 **ACTIVE PROMOTIONS:**
• 🎊 Weekly Bonus: 5% of all bets
• 🔗 Referral Bonus: 100 chips per friend
• 🏆 Achievement rewards for milestones

Launch the WebApp to start playing:
"""
    
    keyboard = []
    
    # Add WebApp button if enabled and available
    if WEBAPP_ENABLED and WEBAPP_IMPORTS_AVAILABLE:
        try:
            webapp_url = f"{WEBAPP_URL}?user_id={user_id}&balance={balance}"
            logger.info(f"Creating WebApp with URL: {webapp_url}")
            web_app = WebApp(url=webapp_url)
            keyboard.append([InlineKeyboardButton("🚀 PLAY IN WEBAPP", web_app=web_app)])
            logger.info("✅ WebApp button created successfully")
        except Exception as e:
            logger.error(f"❌ Error creating WebApp button: {e}")
            # Fallback to URL button
            keyboard.append([InlineKeyboardButton("🚀 OPEN WEBAPP", url=f"{WEBAPP_URL}?user_id={user_id}&balance={balance}")])
    elif WEBAPP_ENABLED:
        # Fallback for older telegram versions - show URL button
        keyboard.append([InlineKeyboardButton("🚀 OPEN WEBAPP", url=f"{WEBAPP_URL}?user_id={user_id}&balance={balance}")])
    
    # Add regular game category buttons (games removed - only navigation)
    keyboard.extend([
        [InlineKeyboardButton("🎁 BONUSES", callback_data="bonus_centre"), InlineKeyboardButton("📊 STATISTICS", callback_data="show_stats")],
        [InlineKeyboardButton("❓ HELP", callback_data="show_help"), InlineKeyboardButton("🔙 MAIN MENU", callback_data="main_panel")]
    ])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Mini App Command ---
async def mini_app_centre_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command handler for /app"""
    await show_mini_app_centre(update, context)

# --- Classic Casino Handler ---
# --- Game Implementation Placeholder ---
# All games have been removed for a clean foundation
# Add your custom games here

# --- Simple Placeholder Handlers ---

async def show_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show balance"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    text = f"""
💰 **BALANCE OVERVIEW** 💰

💎 **Current Balance:** {user['balance']:,} chips
🎮 **Games Played:** {user['games_played']}
💸 **Total Wagered:** {user['total_wagered']:,} chips
💰 **Total Won:** {user['total_won']:,} chips

📊 **Account Status:**
• Account Type: Standard
• Withdrawal Limit: 25,000 chips/day
• Minimum Withdrawal: 1,000 chips

💳 **Financial Operations:**
Manage your funds with secure deposit and withdrawal options.
"""
    
    keyboard = [
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit"), InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre"), InlineKeyboardButton("🎁 Get Bonus", callback_data="bonus_centre")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def main_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main panel"""
    # Create a fake update for start_command
    class FakeMessage:
        async def reply_text(self, text, reply_markup=None, parse_mode=None):
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    
    fake_update = type('Update', (), {
        'effective_user': update.effective_user,
        'message': FakeMessage()
    })()
    
    await start_command(fake_update, context)

# Placeholder handlers
async def placeholder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder for unimplemented features"""
    query = update.callback_query
    await query.answer("🚧 This feature is coming soon! Stay tuned for updates.", show_alert=True)

# --- Deposit Handler ---
async def deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle deposit requests"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    text = f"""
💳 **DEPOSIT FUNDS** 💳

💰 **Current Balance:** {user['balance']:,} chips
👤 **Player:** {user['username']}

🏦 **Deposit Methods:**

**💳 Credit/Debit Card**
• Instant processing
• Min: 100 chips
• Max: 10,000 chips
• Fee: 2.5%

**🏦 Bank Transfer**
• 1-3 business days
• Min: 500 chips
• Max: 50,000 chips
• Fee: Free

**₿ Cryptocurrency**
• Bitcoin, Ethereum, USDT
• 10-60 min processing
• Min: 50 chips
• Fee: Network fees only

**📱 E-Wallets**
• PayPal, Skrill, Neteller
• Instant processing
• Min: 100 chips
• Fee: 1.5%

Choose your deposit method:
"""
    
    keyboard = [
        [InlineKeyboardButton("💳 Credit Card", callback_data="deposit_card"), InlineKeyboardButton("🏦 Bank Transfer", callback_data="deposit_bank")],
        [InlineKeyboardButton("₿ Crypto", callback_data="deposit_crypto"), InlineKeyboardButton("📱 E-Wallet", callback_data="deposit_ewallet")],
        [InlineKeyboardButton("🔙 Back to Balance", callback_data="show_balance")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Withdraw Handler ---
async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdrawal requests"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    # Check minimum withdrawal amount
    min_withdrawal = 1000
    if user['balance'] < min_withdrawal:
        await query.answer(f"❌ Minimum withdrawal: {min_withdrawal:,} chips", show_alert=True)
        return
    
    text = f"""
💸 **WITHDRAW FUNDS** 💸

💰 **Available Balance:** {user['balance']:,} chips
👤 **Player:** {user['username']}

📋 **Withdrawal Requirements:**
• Minimum: 1,000 chips
• Maximum: 25,000 chips per day
• Processing: 24-72 hours
• Verification may be required

🏦 **Withdrawal Methods:**

**🏦 Bank Transfer**
• 1-3 business days
• Fee: Free
• Min: 1,000 chips

**₿ Cryptocurrency**
• Bitcoin, Ethereum, USDT
• 10-60 min processing
• Fee: Network fees
• Min: 500 chips

**📱 E-Wallets**
• PayPal, Skrill, Neteller
• 24-48 hours
• Fee: 2%
• Min: 1,000 chips

Choose your withdrawal method:
"""
    
    keyboard = [
        [InlineKeyboardButton("🏦 Bank Transfer", callback_data="withdraw_bank"), InlineKeyboardButton("₿ Crypto", callback_data="withdraw_crypto")],
        [InlineKeyboardButton("📱 E-Wallet", callback_data="withdraw_ewallet")],
        [InlineKeyboardButton("🔙 Back to Balance", callback_data="show_balance")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Health Check and Keep-Alive for Render ---
from aiohttp import web, ClientSession
import aiohttp.web

async def health_check(request):
    """Health check endpoint for Render"""
    return web.json_response({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "telegram-casino-bot",
        "version": BOT_VERSION
    })

async def keep_alive_heartbeat():
    """Keep-alive heartbeat to prevent Render from sleeping"""
    if not RENDER_EXTERNAL_URL:
        logger.info("No RENDER_EXTERNAL_URL set, skipping heartbeat")
        return
    
    logger.info(f"Starting heartbeat every {HEARTBEAT_INTERVAL} seconds")
    
    async with ClientSession() as session:
        while True:
            try:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                
                # Make a simple HTTP request to ourselves
                ping_url = f"{RENDER_EXTERNAL_URL}/health"
                async with session.get(ping_url, timeout=10) as response:
                    if response.status == 200:
                        logger.info("✓ Heartbeat ping successful")
                    else:
                        logger.warning(f"⚠ Heartbeat ping returned status {response.status}")
                        
            except asyncio.CancelledError:
                logger.info("Heartbeat task cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Heartbeat error: {e}")
                continue

async def start_web_server():
    """Start web server for health checks and WebApp"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', casino_webapp)
    app.router.add_get('/casino', casino_webapp)
    app.router.add_static('/', path=os.path.join(os.path.dirname(__file__), 'static'), name='static')
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    logger.info(f"✅ Health check server started on port {PORT}")
    return runner

async def casino_webapp(request):
    """Serve a modern black-themed casino WebApp interface"""
    user_id = request.query.get('user_id', 'guest')
    balance = request.query.get('balance', '1000')
    
    # Read the HTML template
    template_path = os.path.join(os.path.dirname(__file__), 'casino_webapp_new.html')
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_template = f.read()
        
        # Replace placeholders with actual values
        html = html_template.replace('{BALANCE}', str(balance))
        html = html.replace('{USER_ID}', str(user_id))
    except FileNotFoundError:
        # Fallback to inline HTML if template file is not found
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>🎰 Casino WebApp</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #000000;
            color: white; 
            min-height: 100vh;
            overflow-x: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #333;
            box-shadow: 0 2px 20px rgba(0,0,0,0.5);
        }}
        
        .logo-section {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .logo {{
            font-size: 2.5em;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1);
            background-size: 200% 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: gradientShift 3s ease infinite;
            font-weight: bold;
        }}
        
        @keyframes gradientShift {{
            0%, 100% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
        }}
        
        .brand-text {{
            font-size: 1.5em;
            font-weight: bold;
            color: #fff;
            text-shadow: 0 0 10px rgba(255,255,255,0.3);
        }}
        
        .balance-section {{
            display: flex;
            flex-direction: column;
            align-items: center;
            background: rgba(255,255,255,0.1);
            padding: 10px 20px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }}
        
        .balance-label {{
            font-size: 0.9em;
            color: #ccc;
            margin-bottom: 5px;
        }}
        
        .balance-amount {{
            font-size: 1.8em;
            font-weight: bold;
            color: #4ecdc4;
            text-shadow: 0 0 10px rgba(78,205,196,0.5);
        }}
        
        .profile-section {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .profile-pic {{
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: 3px solid #4ecdc4;
            box-shadow: 0 0 15px rgba(78,205,196,0.3);
            background: linear-gradient(45deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5em;
            font-weight: bold;
        }}
        
        .user-info {{
            display: flex;
            flex-direction: column;
        }}
        
        .username {{
            font-size: 1em;
            font-weight: bold;
            color: #fff;
        }}
        
        .user-id {{
            font-size: 0.8em;
            color: #888;
        }}
        
        .main-content {{
            padding: 30px 20px;
            max-width: 800px;
            margin: 0 auto;
        }}
        
        .games-section {{
            margin-top: 30px;
        }}
        
        .section-title {{
            font-size: 1.8em;
            font-weight: bold;
            margin-bottom: 20px;
            text-align: center;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .games-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .game {{ 
            background: linear-gradient(145deg, #1a1a1a, #2d2d2d);
            border-radius: 20px; 
            padding: 25px; 
            cursor: pointer;
            transition: all 0.3s ease;
            border: 1px solid #333;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        
        .game:before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(78,205,196,0.1), transparent);
            transition: left 0.5s;
        }}
        
        .game:hover:before {{
            left: 100%;
        }}
        
        .game:hover {{ 
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 10px 30px rgba(78,205,196,0.2);
            border-color: #4ecdc4;
        }}
        
        .game-icon {{
            font-size: 3em;
            margin-bottom: 15px;
            filter: drop-shadow(0 0 10px rgba(255,255,255,0.3));
        }}
        
        .game-name {{
            font-size: 1.1em;
            font-weight: bold;
            color: #fff;
        }}
        
        .coming-soon {{
            background: linear-gradient(145deg, #1a1a1a, #2d2d2d);
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            margin-top: 30px;
            border: 1px solid #333;
        }}
        
        .coming-soon h3 {{
            color: #4ecdc4;
            margin-bottom: 15px;
            font-size: 1.5em;
        }}
        
        .coming-soon p {{
            color: #ccc;
            margin-bottom: 10px;
        }}
        
        .btn {{
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            border: none;
            padding: 15px 30px;
            border-radius: 25px;
            color: white;
            font-weight: bold;
            margin: 20px 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 1em;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }}
        
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 7px 20px rgba(0,0,0,0.4);
        }}
        
        .btn:active {{
            transform: translateY(0);
        }}
        
        @media (max-width: 768px) {{
            .header {{
                flex-direction: column;
                gap: 15px;
            }}
            
            .logo-section {{
                justify-content: center;
            }}
            
            .profile-section {{
                order: -1;
            }}
            
            .games-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-section">
            <div class="logo">🎰</div>
            <div class="brand-text">CASINO</div>
        </div>
        
        <div class="balance-section">
            <div class="balance-label">Your Balance</div>
            <div class="balance-amount">{balance} chips</div>
        </div>
        
        <div class="profile-section">
            <div class="profile-pic" id="profilePic">👤</div>
            <div class="user-info">
                <div class="username" id="username">Player</div>
                <div class="user-id">ID: {user_id}</div>
            </div>
        </div>
    </div>
    
    <div class="main-content">
        <div class="games-section">
            <h2 class="section-title">🎮 Casino Games</h2>
            <div class="games-grid">
                <div class="game" onclick="playGame('Slots')">
                    <div class="game-icon">🎰</div>
                    <div class="game-name">Slots</div>
                </div>
                <div class="game" onclick="playGame('Blackjack')">
                    <div class="game-icon">🃏</div>
                    <div class="game-name">Blackjack</div>
                </div>
                <div class="game" onclick="playGame('Roulette')">
                    <div class="game-icon">🎯</div>
                    <div class="game-name">Roulette</div>
                </div>
                <div class="game" onclick="playGame('Dice')">
                    <div class="game-icon">🎲</div>
                    <div class="game-name">Dice</div>
                </div>
                <div class="game" onclick="playGame('Poker')">
                    <div class="game-icon">♠️</div>
                    <div class="game-name">Poker</div>
                </div>
                <div class="game" onclick="playGame('Crash')">
                    <div class="game-icon">🚀</div>
                    <div class="game-name">Crash</div>
                </div>
            </div>
        </div>
        
        <div class="coming-soon">
            <h3>✨ Professional Casino Experience</h3>
            <p>🎮 Full casino games are being developed</p>
            <p>🔥 Real-time multiplayer coming soon</p>
            <p>💎 VIP features and tournaments</p>
            <button class="btn" onclick="goBack()">🔙 Back to Bot</button>
        </div>
    </div>
    
    <script>
        // Initialize Telegram WebApp
        let webApp = null;
        let user = null;
        
        if (window.Telegram && window.Telegram.WebApp) {{
            webApp = window.Telegram.WebApp;
            webApp.ready();
            webApp.expand();
            
            // Get user data from Telegram
            user = webApp.initDataUnsafe.user;
            
            if (user) {{
                // Update username
                document.getElementById('username').textContent = user.first_name || 'Player';
                
                // Set profile picture or initials
                const profilePic = document.getElementById('profilePic');
                if (user.photo_url) {{
                    profilePic.innerHTML = '<img src="' + user.photo_url + '" style="width:100%; height:100%; border-radius:50%; object-fit:cover;">';
                }} else if (user.first_name) {{
                    profilePic.textContent = user.first_name.charAt(0).toUpperCase();
                }}
            }}
            
            // Set theme colors
            webApp.BackButton.show();
            webApp.BackButton.onClick(() => webApp.close());
            
            // Apply Telegram theme
            if (webApp.colorScheme === 'dark') {{
                document.body.style.background = '#000000';
            }}
        }}
        
        function playGame(gameType) {{
            // Show a more professional game coming soon message
            const message = '🎮 ' + gameType + ' is coming soon!\\n\\n' +
                          '🚀 We are building an amazing casino experience\\n' +
                          '💫 Stay tuned for updates!\\n\\n' +
                          '🎁 Meanwhile, check out our bonuses and promotions!';
            
            if (webApp && webApp.showAlert) {{
                webApp.showAlert(message);
            }} else {{
                alert(message);
            }}
        }}
        
        function goBack() {{
            if (webApp) {{
                webApp.close();
            }} else {{
                window.history.back();
            }}
        }}
        
        // Add some interactive effects
        document.addEventListener('DOMContentLoaded', function() {{
            // Animate balance on load
            const balanceElement = document.querySelector('.balance-amount');
            if (balanceElement) {{
                balanceElement.style.animation = 'pulse 2s infinite';
            }}
        }});
        
        // Add pulse animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes pulse {{
                0%, 100% {{ transform: scale(1); }}
                50% {{ transform: scale(1.05); }}
            }}
        `;
        document.head.appendChild(style);
    </script>
</body>
</html>
"""
    
    return web.Response(text=html, content_type='text/html')
async def setup_webapp_menu_button(application):
    """Set up the WebApp menu button for the bot"""
    if WEBAPP_ENABLED and WEBAPP_IMPORTS_AVAILABLE:
        try:
            # Only set menu button for HTTPS URLs (Telegram requirement)
            if WEBAPP_URL.startswith('https://'):
                webapp_button = MenuButtonWebApp(
                    text="🎰 Open Casino",
                    web_app=WebApp(url=WEBAPP_URL)
                )
                await application.bot.set_chat_menu_button(menu_button=webapp_button)
                logger.info("✅ WebApp menu button set successfully")
            else:
                logger.info("ℹ️ WebApp menu button skipped (localhost URLs not supported)")
        except Exception as e:
            logger.error(f"❌ Failed to set WebApp menu button: {e}")
    else:
        logger.info("ℹ️ WebApp disabled or not available, skipping menu button setup")

# --- WebApp Command ---
async def webapp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Direct command to open WebApp"""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    if not WEBAPP_ENABLED:
        await update.message.reply_text("❌ WebApp is currently disabled.")
        return
    
    webapp_url = f"{WEBAPP_URL}?user_id={user_id}&balance={user['balance']}"
    
    if WEBAPP_IMPORTS_AVAILABLE:
        web_app = WebApp(url=webapp_url)
        keyboard = [[InlineKeyboardButton("🚀 OPEN CASINO WEBAPP", web_app=web_app)]]
    else:
        # Fallback for older versions
        keyboard = [[InlineKeyboardButton("🚀 OPEN CASINO WEBAPP", url=webapp_url)]]
    
    text = f"""
🚀 **CASINO WEBAPP** 🚀

🎮 **Full Casino Experience in Your Browser!**

💰 **Your Balance:** {user['balance']:,} chips
👤 **User ID:** {user_id}

🎯 **WebApp Features:**
• 🎰 All casino games in one place
• 📱 Mobile-optimized interface  
• ⚡ Real-time balance updates
• 🎮 Smooth gaming experience
• 🔄 Sync with Telegram bot

Click the button below to launch:
"""
    
    await update.message.reply_text(
        text, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode=ParseMode.MARKDOWN
    )

# --- Main Callback Handler ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    try:
        # Main navigation
        if data == "main_panel":
            await main_panel_callback(update, context)
        elif data == "mini_app_centre":
            await show_mini_app_centre(update, context)
        elif data == "show_balance":
            await show_balance_callback(update, context)
        elif data == "show_stats":
            await show_stats_callback(update, context)
        elif data == "show_leaderboard":
            await show_leaderboard_callback(update, context)
        elif data == "show_help":
            await show_help_callback(update, context)
        elif data == "bonus_centre":
            await bonus_centre_callback(update, context)
        
        # Financial operations
        elif data == "deposit":
            await deposit_callback(update, context)
        elif data == "withdraw":
            await withdraw_callback(update, context)
        elif data.startswith("deposit_"):
            await deposit_method_callback(update, context)
        elif data.startswith("withdraw_"):
            await withdraw_method_callback(update, context)
        
        # Bonus operations
        elif data == "claim_daily_bonus":
            await claim_daily_bonus_callback(update, context)
        elif data.startswith("bonus_") or data in ["get_referral", "show_achievements", "bonus_history"]:
            await bonus_action_callback(update, context)
        
        # All other callbacks redirect to placeholder
        else:
            await placeholder_callback(update, context)
            
    except Exception as e:
        logger.error(f"Error handling callback {data}: {e}")
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

# --- Bot Commands ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    webapp_status = "✅ Yes" if WEBAPP_ENABLED and WEBAPP_IMPORTS_AVAILABLE else "⚠️ Limited" if WEBAPP_ENABLED else "❌ No"
    menu_button_status = "✅ Active" if WEBAPP_ENABLED and WEBAPP_IMPORTS_AVAILABLE else "❌ Disabled"
    
    help_text = f"""
🎰 **CASINO BOT HELP** 🎰

**Commands:**
/start - Main panel
/app - Mini App Centre  
/webapp - Open Casino WebApp
/casino - Open Casino WebApp
/help - This help

**Features:**
🚀 **WebApp Integration** - Full casino experience in browser
💰 **Balance System** - Earn and spend chips
� **Bonus System** - Daily rewards and promotions
� **Statistics** - Track your gaming progress

**WebApp Status:**
• URL: {WEBAPP_URL}
• Enabled: {webapp_status}
• Menu Button: {menu_button_status}
• Compatibility: {'✅ Full' if WEBAPP_IMPORTS_AVAILABLE else '⚠️ URL fallback'}

**How to Use WebApp:**
1. Click the "🚀 PLAY IN WEBAPP" button in Mini App Centre
2. Use /webapp command for direct access
3. Check your menu button (if enabled)

Ready to play? Use /start or /webapp!
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# --- Additional Callback Handlers ---
async def show_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stats callback"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    # Get user rank
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE balance > ?", (user['balance'],))
        rank = (await cur.fetchone())[0] + 1
    
    text = f"""
📊 **PLAYER STATISTICS** 📊

👤 **Player:** {user['username']}
💰 **Balance:** {user['balance']:,} chips
🏆 **Global Rank:** #{rank}

🎮 **Gaming Stats:**
• Games Played: {user['games_played']}
• Total Wagered: {user['total_wagered']:,} chips
• Total Won: {user['total_won']:,} chips
• Win Rate: {((user['total_won'] / max(user['total_wagered'], 1)) * 100):.1f}%

🏅 **Achievements:**
• First Deposit: ✅
• High Roller: {'✅' if user['balance'] >= 1000 else '❌'}
• VIP Status: {'✅' if user['balance'] >= VIP_SILVER_REQUIRED else '❌'}

🎯 **Performance Rating:**
{get_performance_rating(user)}

Ready to improve your stats?
"""
    
    keyboard = [
        [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre"), InlineKeyboardButton("🏆 View Leaderboard", callback_data="show_leaderboard")],
        [InlineKeyboardButton("🎁 Get Bonus", callback_data="bonus_centre"), InlineKeyboardButton("🔙 Back to Main", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def show_leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle leaderboard callback"""
    query = update.callback_query
    await query.answer()
    
    # Get top 10 players
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT username, balance 
            FROM users 
            ORDER BY balance DESC 
            LIMIT 10
        """)
        rows = await cur.fetchall()
    
    text = "🏆 **GLOBAL LEADERBOARD** 🏆\n\n"
    
    if not rows:
        text += "📋 No players yet. Be the first to play!"
    else:
        text += "🎯 *Top 10 Players:*\n\n"
        
        for i, (username, balance) in enumerate(rows, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            display_name = username if username else f"Player_{i}"
            text += f"{medal} *{display_name}*: {balance:,} chips\n"
    
    keyboard = [
        [InlineKeyboardButton("📊 My Stats", callback_data="show_stats"), InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def show_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help callback"""
    query = update.callback_query
    await query.answer()
    
    webapp_status = "✅ Available" if WEBAPP_ENABLED and WEBAPP_IMPORTS_AVAILABLE else "⚠️ Limited" if WEBAPP_ENABLED else "❌ Disabled"
    
    text = f"""
❓ **CASINO BOT HELP** ❓

🎰 **How to Play:**
1. Click "🎮 Mini App Centre" to access games
2. Use the WebApp for the best experience
3. Manage your balance with deposit/withdraw
4. Check stats and leaderboard regularly

🚀 **WebApp Features:**
• Full casino in your browser
• Real-time balance updates
• Mobile-optimized interface
• Smooth gaming experience

📋 **Commands:**
/start - Main menu
/app - Mini App Centre
/webapp - Direct WebApp access
/help - This help

🔧 **System Status:**
• WebApp: {webapp_status}
• Bot Version: {BOT_VERSION}
• Server: Online ✅

🎯 **Getting Started:**
1. Start with the daily bonus
2. Try small bets first
3. Learn the games in WebApp
4. Track your progress in stats

Need more help? Contact support!
"""
    
    keyboard = [
        [InlineKeyboardButton("🎮 Start Playing", callback_data="mini_app_centre"), InlineKeyboardButton("🎁 Get Bonus", callback_data="bonus_centre")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def bonus_centre_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bonus centre callback"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    # Calculate VIP status
    vip_level = get_vip_level(user['balance'])
    daily_bonus = get_daily_bonus_amount(vip_level)
    
    text = f"""
🎁 **BONUS CENTRE** 🎁

👤 **Player:** {user['username']}
💰 **Balance:** {user['balance']:,} chips
👑 **VIP Level:** {vip_level}

🎊 **Available Bonuses:**

💝 **Daily Bonus**
• Amount: {daily_bonus} chips
• VIP Multiplier: {get_vip_multiplier(vip_level)}x
• Cooldown: 24 hours

🔗 **Referral Bonus**
• Invite friends: 100 chips each
• Friend bonus: 50 chips
• Unlimited referrals!

🏆 **Achievement Bonuses**
• First game: 25 chips ✅
• 10 games: 100 chips
• High roller: 500 chips
• VIP status: 1,000 chips

🎯 **Weekly Bonus**
• 5% of total weekly bets
• Paid every Monday
• VIP multipliers apply

Ready to claim your bonuses?
"""
    
    keyboard = [
        [InlineKeyboardButton("🎁 Claim Daily Bonus", callback_data="claim_daily_bonus"), InlineKeyboardButton("🔗 Referral Link", callback_data="get_referral")],
        [InlineKeyboardButton("🏆 View Achievements", callback_data="show_achievements"), InlineKeyboardButton("📊 Bonus History", callback_data="bonus_history")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Deposit Method Handlers ---
async def deposit_method_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle deposit method callbacks"""
    query = update.callback_query
    await query.answer()
    
    method = query.data.replace("deposit_", "")
    
    text = f"""
💳 **DEPOSIT - {method.upper().replace('_', ' ')}** 💳

🚧 **Under Development** 🚧

This payment method is being implemented.
For now, you can:

💰 **Free Daily Bonus** - Get chips every day
🎮 **Play Games** - Earn chips by playing
🏆 **Achievements** - Unlock bonus rewards

Coming soon:
• Real payment processing
• Multiple currencies
• Instant deposits
• Secure transactions

Thank you for your patience!
"""
    
    keyboard = [
        [InlineKeyboardButton("🎁 Get Free Bonus", callback_data="bonus_centre")],
        [InlineKeyboardButton("🔙 Back to Deposit", callback_data="deposit")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Withdraw Method Handlers ---
async def withdraw_method_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdraw method callbacks"""
    query = update.callback_query
    await query.answer()
    
    method = query.data.replace("withdraw_", "")
    
    text = f"""
💸 **WITHDRAW - {method.upper().replace('_', ' ')}** 💸

🚧 **Under Development** 🚧

Withdrawal system is being implemented.
Current features:

📊 **Track Progress** - Monitor your balance
🎯 **Set Goals** - Plan your gaming strategy
🏆 **Earn More** - Play games to increase balance

Coming soon:
• Real withdrawal processing
• Multiple payout methods
• Fast processing times
• Secure transactions

Keep playing and building your balance!
"""
    
    keyboard = [
        [InlineKeyboardButton("🎮 Play More Games", callback_data="mini_app_centre")],
        [InlineKeyboardButton("🔙 Back to Withdraw", callback_data="withdraw")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Bonus Action Handlers ---
async def claim_daily_bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle daily bonus claim"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    # Simple cooldown check (you can implement more sophisticated tracking)
    import random
    
    # Generate bonus amount based on VIP level
    vip_level = get_vip_level(user['balance'])
    bonus_amount = get_daily_bonus_amount(vip_level)
    
    # Add some randomization
    bonus_amount += random.randint(-10, 20)
    
    # Add bonus to balance
    await update_balance(user_id, bonus_amount)
    updated_user = await get_user(user_id)
    
    text = f"""
🎁 **DAILY BONUS CLAIMED!** 🎁

💰 **Bonus Received:** +{bonus_amount} chips
👑 **VIP Level:** {vip_level}
💎 **New Balance:** {updated_user['balance']:,} chips

🎊 **Bonus Details:**
• Base Amount: 50 chips
• VIP Multiplier: {get_vip_multiplier(vip_level)}x
• Random Bonus: Included

🎯 **Next Steps:**
Ready to put your bonus to good use?
"""
    
    keyboard = [
        [InlineKeyboardButton("🎮 Play Games", callback_data="mini_app_centre"), InlineKeyboardButton("📊 Check Stats", callback_data="show_stats")],
        [InlineKeyboardButton("🎁 More Bonuses", callback_data="bonus_centre"), InlineKeyboardButton("🔙 Main Menu", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def bonus_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle other bonus actions"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "get_referral":
        text = f"""
🔗 **REFERRAL SYSTEM** 🔗

💰 **Earn 100 chips per friend!**

📋 **How it works:**
1. Share your referral link
2. Friends join using your link
3. You both get bonus chips!

🎁 **Rewards:**
• You: 100 chips per referral
• Friend: 50 chips welcome bonus
• Bonus when they play first game

🔗 **Your Referral Link:**
`https://t.me/{context.bot.username}?start=ref_{update.effective_user.id}`

📊 **Referral Stats:**
• Total Referrals: Coming soon
• Bonus Earned: Coming soon
• Active Referrals: Coming soon

Share the link and start earning!
"""
    
    elif data == "show_achievements":
        user = await get_user(update.effective_user.id)
        text = f"""
🏆 **ACHIEVEMENTS** 🏆

📊 **Your Progress:**

✅ **Completed:**
• 🎮 First Game: +25 chips
• 💰 First Deposit: +100 chips
• 🎯 Regular Player: +50 chips

🔄 **In Progress:**
• 🎰 Play 10 Games: {user['games_played']}/10
• 💎 Reach 1,000 chips: {user['balance']}/1,000
• 🏆 High Roller: {user['balance']}/5,000

🔒 **Locked:**
• 🌟 VIP Diamond: Reach 10,000 chips
• 🎪 Tournament Winner: Win a tournament
• 💯 Perfect Week: 7-day win streak

Keep playing to unlock more rewards!
"""
    
    elif data == "bonus_history":
        text = f"""
📊 **BONUS HISTORY** 📊

📋 **Recent Bonuses:**

🎁 Today: Daily Bonus - 50 chips
🎮 Yesterday: Game Bonus - 25 chips
🔗 Last Week: Referral - 100 chips
🏆 Last Month: Achievement - 200 chips

💰 **Total Earned:**
• Daily Bonuses: 350 chips
• Referral Bonuses: 100 chips
• Achievement Bonuses: 200 chips
• Game Bonuses: 125 chips

📈 **Bonus Trends:**
• This Week: 175 chips
• This Month: 775 chips
• All Time: 775 chips

More detailed tracking coming soon!
"""
    
    else:
        text = "🚧 This bonus feature is coming soon! 🚧"
    
    keyboard = [
        [InlineKeyboardButton("🎁 Bonus Centre", callback_data="bonus_centre")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Helper Functions ---
def get_performance_rating(user):
    """Get performance rating based on user stats"""
    balance = user['balance']
    games = user['games_played']
    
    if balance >= 10000:
        return "🌟 Elite Player"
    elif balance >= 5000:
        return "⭐ High Roller"
    elif balance >= 1000:
        return "🎯 Skilled Player"
    elif games >= 10:
        return "🎮 Regular Player"
    else:
        return "🔰 Newcomer"

def get_vip_level(balance):
    """Get VIP level based on balance"""
    if balance >= VIP_DIAMOND_REQUIRED:
        return "💎 Diamond"
    elif balance >= VIP_GOLD_REQUIRED:
        return "🥇 Gold"
    elif balance >= VIP_SILVER_REQUIRED:
        return "🥈 Silver"
    else:
        return "🥉 Bronze"

def get_vip_multiplier(vip_level):
    """Get VIP multiplier based on level"""
    if "Diamond" in vip_level:
        return 3.0
    elif "Gold" in vip_level:
        return 2.0
    elif "Silver" in vip_level:
        return 1.5
    else:
        return 1.0

def get_daily_bonus_amount(vip_level):
    """Get daily bonus amount based on VIP level"""
    base_bonus = 50
    multiplier = get_vip_multiplier(vip_level)
    return int(base_bonus * multiplier)

# --- Main Application Setup ---
async def manual_polling_loop(application):
    """Manual polling loop as a last resort for compatibility issues"""
    logger.info("🔄 Starting manual polling loop...")
    offset = 0
    
    while True:
        try:
            # Get updates manually
            updates = await application.bot.get_updates(offset=offset, timeout=30)
            
            for update in updates:
                try:
                    # Process each update
                    await application.process_update(update)
                    offset = update.update_id + 1
                except Exception as update_error:
                    logger.error(f"Error processing update {update.update_id}: {update_error}")
                    
        except asyncio.CancelledError:
            logger.info("Manual polling loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error in manual polling loop: {e}")
            await asyncio.sleep(5)  # Wait before retrying

def main():
    """Main application entry point"""
    try:
        # Import the necessary modules for the simple approach
        import nest_asyncio
        nest_asyncio.apply()  # Allow nested event loops
        
        # Use asyncio.run to create a new event loop
        asyncio.run(run_bot())
    except ImportError:
        # If nest_asyncio is not available, use alternative approach
        logger.info("Using alternative startup method...")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_bot())
        except Exception as e:
            logger.error(f"❌ Alternative startup failed: {e}")
            # Last resort: direct execution
            app = ApplicationBuilder().token(BOT_TOKEN).build()
            
            # Add handlers
            app.add_handler(CommandHandler("start", start_command))
            app.add_handler(CommandHandler("app", mini_app_centre_command))
            app.add_handler(CommandHandler("webapp", webapp_command))
            app.add_handler(CommandHandler("casino", webapp_command))
            app.add_handler(CommandHandler("help", help_command))
            app.add_handler(CallbackQueryHandler(handle_callback))
            
            logger.info("🚀 Starting bot with direct method...")
            app.run_polling(drop_pending_updates=True)
        finally:
            if 'loop' in locals():
                loop.close()
    except KeyboardInterrupt:
        logger.info("🛑 Application terminated by user")
    except Exception as e:
        logger.error(f"❌ Application failed to start: {e}")
        sys.exit(1)

async def run_bot():
    """Run the bot with proper async handling"""
    runner = None
    heartbeat_task = None
    
    try:
        # Initialize database
        await init_db()
        logger.info("✅ Database initialized successfully")
        
        # Create application
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("app", mini_app_centre_command))
        application.add_handler(CommandHandler("webapp", webapp_command))
        application.add_handler(CommandHandler("casino", webapp_command))
        application.add_handler(CommandHandler("help", help_command))
        
        # Add callback handler
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        # Setup WebApp menu button
        await setup_webapp_menu_button(application)
        
        # Start health check server (optional for local development)
        try:
            runner = await start_web_server()
            logger.info(f"✅ Health check server started on port {PORT}")
        except Exception as e:
            logger.warning(f"⚠️ Health check server failed to start: {e}")
            logger.info("ℹ️ Continuing without health check server (normal for local development)")
        
        # Start heartbeat task for Render (only if URL is set)
        if RENDER_EXTERNAL_URL:
            heartbeat_task = asyncio.create_task(keep_alive_heartbeat())
        else:
            logger.info("ℹ️ Skipping heartbeat (no RENDER_EXTERNAL_URL set)")
        
        logger.info("🚀 Starting Telegram Casino Bot...")
        logger.info(f"🎰 Bot Version: {BOT_VERSION}")
        logger.info(f"🌐 WebApp URL: {WEBAPP_URL}")
        logger.info(f"⚡ WebApp Enabled: {WEBAPP_ENABLED}")
        logger.info(f"🔗 Health Check Server: http://0.0.0.0:{PORT}")
        
        # Initialize and start application manually for better control
        await application.initialize()
        await application.start()
        
        logger.info("✅ Bot is running and ready to receive messages!")
        logger.info("Press Ctrl+C to stop the bot")
        
        # Start polling manually with error handling for Python 3.13 compatibility
        try:
            await application.updater.start_polling(drop_pending_updates=True)
            logger.info("✅ Polling started successfully")
        except AttributeError as attr_error:
            if "_Updater__polling_cleanup_cb" in str(attr_error):
                logger.warning("⚠️ Detected Python 3.13 compatibility issue with Updater")
                logger.info("🔄 Attempting fallback polling method...")
                
                # Try alternative polling method for Python 3.13
                try:
                    # Use direct polling without problematic attributes
                    logger.info("🔄 Trying direct polling approach...")
                    await manual_polling_loop(application)
                    logger.info("✅ Manual polling started successfully")
                except Exception as fallback_error:
                    logger.error(f"❌ Manual polling failed: {fallback_error}")
                    raise fallback_error
            else:
                raise attr_error
        
        # Keep the application running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal")
        
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise
    finally:
        # Cleanup
        logger.info("🔄 Starting cleanup...")
        if heartbeat_task:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if 'application' in locals():
            try:
                await application.updater.stop()
                await application.stop()
                await application.shutdown()
            except Exception as cleanup_error:
                logger.error(f"Error during application cleanup: {cleanup_error}")
        
        if runner:
            try:
                await runner.cleanup()
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up web server: {cleanup_error}")
        logger.info("✅ Bot shutdown complete")

if __name__ == "__main__":
    """Entry point for the application"""
    main()
