# bot.py
"""
Enhanced Telegram Casino Bot v2.0
Professional-grade casino with security, anti-fraud, and comprehensive features.
Stake-style interface with advanced game mechanics and user protection.
"""

import os
import random
import asyncio
import logging
import hashlib
import hmac
import time
import json
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv
import aiohttp
import signal
import sys
from datetime import datetime, timedelta
from collections import defaultdict, deque

import aiosqlite
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User as TelegramUser
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
import nest_asyncio
from telegram.error import TelegramError, BadRequest, Forbidden

# --- Config ---
load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_PATH = os.environ.get("CASINO_DB", "casino.db")

# Render hosting configuration
PORT = int(os.environ.get("PORT", "8000"))
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

# Security Classes and Enums
class SecurityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"

class GameResult(Enum):
    WIN = "win"
    LOSS = "loss"
    PUSH = "push"

@dataclass
class GameSession:
    user_id: int
    game_type: str
    bet_amount: int
    result: GameResult
    multiplier: float
    timestamp: datetime
    session_id: str

@dataclass
class SecurityAlert:
    user_id: int
    alert_type: str
    severity: SecurityLevel
    details: str
    timestamp: datetime

# Security and Anti-Fraud Systems
class SecurityManager:
    def __init__(self):
        self.suspicious_activities: Dict[int, List[SecurityAlert]] = defaultdict(list)
        self.rate_limits: Dict[int, deque] = defaultdict(lambda: deque(maxlen=MAX_COMMANDS_PER_WINDOW))
        self.daily_losses: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
    def check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limits"""
        now = time.time()
        user_requests = self.rate_limits[user_id]
        
        # Remove old requests
        while user_requests and user_requests[0] < now - ANTI_SPAM_WINDOW:
            user_requests.popleft()
        
        if len(user_requests) >= MAX_COMMANDS_PER_WINDOW:
            return False
        
        user_requests.append(now)
        return True
    
    def add_security_alert(self, user_id: int, alert_type: str, severity: SecurityLevel, details: str):
        """Add a security alert for a user"""
        alert = SecurityAlert(
            user_id=user_id,
            alert_type=alert_type,
            severity=severity,
            details=details,
            timestamp=datetime.now()
        )
        self.suspicious_activities[user_id].append(alert)
        
        # Keep only recent alerts (last 24 hours)
        cutoff = datetime.now() - timedelta(hours=24)
        self.suspicious_activities[user_id] = [
            a for a in self.suspicious_activities[user_id] 
            if a.timestamp > cutoff
        ]
    
    def check_daily_loss_limit(self, user_id: int, amount: int) -> bool:
        """Check if user hasn't exceeded daily loss limit"""
        today = datetime.now().strftime("%Y-%m-%d")
        current_losses = self.daily_losses[user_id][today]
        
        if current_losses + amount > MAX_DAILY_LOSSES:
            return False
        
        return True
    
    def record_loss(self, user_id: int, amount: int):
        """Record a loss for daily tracking"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.daily_losses[user_id][today] += amount
    
    def is_user_flagged(self, user_id: int) -> bool:
        """Check if user has been flagged for suspicious activity"""
        alerts = self.suspicious_activities.get(user_id, [])
        high_severity_alerts = [a for a in alerts if a.severity in [SecurityLevel.HIGH, SecurityLevel.MAXIMUM]]
        return len(high_severity_alerts) >= 3

# Initialize security manager
security_manager = SecurityManager()

# Game Configuration from Environment Variables
DAILY_BONUS_MIN = int(os.environ.get("DAILY_BONUS_MIN", "40"))
DAILY_BONUS_MAX = int(os.environ.get("DAILY_BONUS_MAX", "60"))
MIN_SLOTS_BET = int(os.environ.get("MIN_SLOTS_BET", "10"))
MIN_BLACKJACK_BET = int(os.environ.get("MIN_BLACKJACK_BET", "20"))

# Bet Amounts
BET_AMOUNT_SMALL = int(os.environ.get("BET_AMOUNT_SMALL", "10"))
BET_AMOUNT_MEDIUM = int(os.environ.get("BET_AMOUNT_MEDIUM", "25"))
BET_AMOUNT_LARGE = int(os.environ.get("BET_AMOUNT_LARGE", "50"))
BET_AMOUNT_XLARGE = int(os.environ.get("BET_AMOUNT_XLARGE", "100"))

# VIP Level Requirements
VIP_SILVER_REQUIRED = int(os.environ.get("VIP_SILVER_REQUIRED", "1000"))
VIP_GOLD_REQUIRED = int(os.environ.get("VIP_GOLD_REQUIRED", "5000"))
VIP_DIAMOND_REQUIRED = int(os.environ.get("VIP_DIAMOND_REQUIRED", "10000"))

# Referral System
REFERRAL_BONUS = int(os.environ.get("REFERRAL_BONUS", "100"))
FRIEND_SIGNUP_BONUS = int(os.environ.get("FRIEND_SIGNUP_BONUS", "50"))
FIRST_GAME_BONUS = int(os.environ.get("FIRST_GAME_BONUS", "25"))

# Hi-Lo Game
HILO_PAYOUT_MULTIPLIER = float(os.environ.get("HILO_PAYOUT_MULTIPLIER", "1.8"))

# Plinko Payouts
PLINKO_PAYOUT_HIGH = int(os.environ.get("PLINKO_PAYOUT_HIGH", "130"))
PLINKO_PAYOUT_GOOD = int(os.environ.get("PLINKO_PAYOUT_GOOD", "43"))
PLINKO_PAYOUT_MEDIUM = int(os.environ.get("PLINKO_PAYOUT_MEDIUM", "10"))
PLINKO_PAYOUT_LOW = int(os.environ.get("PLINKO_PAYOUT_LOW", "5"))

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Keep-Alive System for Render Hosting ---
heartbeat_task = None

async def keep_alive_heartbeat():
    """
    Keep-alive heartbeat to prevent Render from sleeping the service.
    Makes periodic HTTP requests to keep the service active.
    """
    import aiohttp
    
    if not RENDER_EXTERNAL_URL:
        logger.info("No RENDER_EXTERNAL_URL set, skipping heartbeat")
        return
    
    logger.info(f"Starting heartbeat every {HEARTBEAT_INTERVAL} seconds")
    
    async with aiohttp.ClientSession() as session:
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
                # Continue the loop even if there's an error
                continue

async def start_heartbeat():
    """Start the heartbeat task"""
    global heartbeat_task
    if RENDER_EXTERNAL_URL and not heartbeat_task:
        heartbeat_task = asyncio.create_task(keep_alive_heartbeat())
        logger.info("Heartbeat task started")

async def stop_heartbeat():
    """Stop the heartbeat task"""
    global heartbeat_task
    if heartbeat_task:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        heartbeat_task = None
        logger.info("Heartbeat task stopped")

# Health check endpoint simulation
async def health_check_response():
    """Simple health check response"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "service": "telegram-casino-bot"
    }

# --- Progressive Jackpot System ---
class JackpotManager:
    def __init__(self):
        self.jackpots = {
            'mega_slots': {'amount': 50000, 'min_bet': 100, 'contribution_rate': 0.01},
            'diamond_roulette': {'amount': 25000, 'min_bet': 50, 'contribution_rate': 0.005},
            'blackjack_royal': {'amount': 15000, 'min_bet': 25, 'contribution_rate': 0.002}
        }
    
    def add_to_jackpot(self, game_type: str, bet_amount: int):
        """Add contribution to jackpot based on bet"""
        if game_type in self.jackpots:
            contribution = bet_amount * self.jackpots[game_type]['contribution_rate']
            self.jackpots[game_type]['amount'] += int(contribution)
    
    def check_jackpot_win(self, game_type: str, bet_amount: int) -> bool:
        """Check if player wins jackpot (very rare)"""
        if game_type not in self.jackpots:
            return False
        
        min_bet = self.jackpots[game_type]['min_bet']
        if bet_amount < min_bet:
            return False
        
        # Higher bets have slightly better jackpot odds
        base_chance = 0.0001  # 0.01% base chance
        bet_multiplier = min(bet_amount / min_bet, 5)  # Cap at 5x
        final_chance = base_chance * bet_multiplier
        
        return random.random() < final_chance
    
    def claim_jackpot(self, game_type: str) -> int:
        """Claim jackpot and reset to minimum"""
        if game_type in self.jackpots:
            amount = self.jackpots[game_type]['amount']
            self.jackpots[game_type]['amount'] = 10000  # Reset to base amount
            return amount
        return 0

# Initialize jackpot manager
jackpot_manager = JackpotManager()

# --- Enhanced Achievement System ---
class AchievementManager:
    def __init__(self):
        self.achievements = {
            'first_win': {'name': 'First Victory', 'reward': 50, 'emoji': '🏆'},
            'big_spender': {'name': 'High Roller', 'reward': 200, 'emoji': '💰'},
            'lucky_streak': {'name': 'Lucky Streak', 'reward': 100, 'emoji': '🍀'},
            'vip_member': {'name': 'VIP Status', 'reward': 500, 'emoji': '👑'},
            'jackpot_winner': {'name': 'Jackpot Winner', 'reward': 1000, 'emoji': '💎'},
            'comeback_king': {'name': 'Comeback King', 'reward': 150, 'emoji': '⚡'},
            'game_master': {'name': 'Game Master', 'reward': 300, 'emoji': '🎮'}
        }
    
    async def check_achievements(self, user_id: int, game_result: dict):
        """Check and award achievements based on game results"""
        user_stats = await get_user_statistics(user_id)
        new_achievements = []
        
        # First win achievement
        if user_stats['user']['games_played'] == 1 and game_result.get('result') == 'win':
            await self.award_achievement(user_id, 'first_win')
            new_achievements.append('first_win')
        
        # Big spender (total wagered > 5000)
        if user_stats['user']['total_wagered'] > 5000:
            if not await self.has_achievement(user_id, 'big_spender'):
                await self.award_achievement(user_id, 'big_spender')
                new_achievements.append('big_spender')
        
        # VIP member achievement
        user = await get_user(user_id)
        if user['balance'] >= VIP_SILVER_REQUIRED:
            if not await self.has_achievement(user_id, 'vip_member'):
                await self.award_achievement(user_id, 'vip_member')
                new_achievements.append('vip_member')
        
        return new_achievements
    
    async def award_achievement(self, user_id: int, achievement_key: str):
        """Award achievement to user"""
        achievement = self.achievements[achievement_key]
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT OR IGNORE INTO achievements 
                (user_id, achievement_type, achievement_name) 
                VALUES (?, ?, ?)
            """, (user_id, achievement_key, achievement['name']))
            
            # Award bonus chips
            await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", 
                           (achievement['reward'], user_id))
            
            await db.commit()
    
    async def has_achievement(self, user_id: int, achievement_key: str) -> bool:
        """Check if user has achievement"""
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT 1 FROM achievements WHERE user_id = ? AND achievement_type = ?",
                (user_id, achievement_key)
            )
            return await cur.fetchone() is not None

# Initialize achievement manager
achievement_manager = AchievementManager()

# --- Enhanced Database System ---
async def init_db():
    """Initialize enhanced database with comprehensive tables"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Users table with enhanced fields
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 0,
                total_wagered INTEGER DEFAULT 0,
                total_won INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                vip_level INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_banned BOOLEAN DEFAULT FALSE,
                referrer_id INTEGER,
                daily_bonus_claimed DATE,
                security_level TEXT DEFAULT 'low'
            )
        """)
        
        # Game sessions table for tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                game_type TEXT NOT NULL,
                bet_amount INTEGER NOT NULL,
                win_amount INTEGER DEFAULT 0,
                multiplier REAL DEFAULT 0,
                result TEXT NOT NULL,
                game_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Transactions table for financial tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Security logs table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Achievements table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_type TEXT NOT NULL,
                achievement_name TEXT NOT NULL,
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Tournament table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tournaments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                entry_fee INTEGER NOT NULL,
                prize_pool INTEGER NOT NULL,
                max_participants INTEGER DEFAULT 100,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'active'
            )
        """)
        
        # Tournament participants
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tournament_participants (
                tournament_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                score INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (tournament_id, user_id),
                FOREIGN KEY (tournament_id) REFERENCES tournaments (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Create indexes for better performance
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_balance ON users (balance)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_game_sessions_user ON game_sessions (user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions (user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_security_logs_user ON security_logs (user_id)")
        
        # Migrate existing users table if needed
        try:
            cur = await db.execute("SELECT total_wagered FROM users LIMIT 1")
            await cur.fetchone()
        except:
            # Add new columns to existing users
            await db.execute("ALTER TABLE users ADD COLUMN total_wagered INTEGER DEFAULT 0")
            await db.execute("ALTER TABLE users ADD COLUMN total_won INTEGER DEFAULT 0")
            await db.execute("ALTER TABLE users ADD COLUMN games_played INTEGER DEFAULT 0")
            await db.execute("ALTER TABLE users ADD COLUMN vip_level INTEGER DEFAULT 0")
            await db.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            await db.execute("ALTER TABLE users ADD COLUMN last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            await db.execute("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT FALSE")
            await db.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER")
            await db.execute("ALTER TABLE users ADD COLUMN daily_bonus_claimed DATE")
            await db.execute("ALTER TABLE users ADD COLUMN security_level TEXT DEFAULT 'low'")
        
        await db.commit()
    logger.info("Enhanced database initialized at %s", DB_PATH)


async def create_user(user_id: int, username: str, referrer_id: int = None):
    """Create a new user with enhanced tracking"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users 
            (id, username, balance, created_at, last_active, referrer_id) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, username, 100, datetime.now(), datetime.now(), referrer_id))
        
        # Log the registration transaction
        transaction_id = str(uuid.uuid4())
        await db.execute("""
            INSERT INTO transactions (id, user_id, transaction_type, amount, description) 
            VALUES (?, ?, ?, ?, ?)
        """, (transaction_id, user_id, "registration_bonus", 100, "Welcome bonus for new user"))
        
        # Award referral bonus if applicable
        if referrer_id:
            referrer = await get_user(referrer_id)
            if referrer:
                await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (REFERRAL_BONUS, referrer_id))
                ref_transaction_id = str(uuid.uuid4())
                await db.execute("""
                    INSERT INTO transactions (id, user_id, transaction_type, amount, description) 
                    VALUES (?, ?, ?, ?, ?)
                """, (ref_transaction_id, referrer_id, "referral_bonus", REFERRAL_BONUS, f"Referral bonus for inviting user {user_id}"))
        
        await db.commit()
    return await get_user(user_id)


async def get_user(user_id: int):
    """Get comprehensive user data"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT id, username, balance, total_wagered, total_won, games_played, 
                   vip_level, created_at, last_active, is_banned, referrer_id, 
                   daily_bonus_claimed, security_level 
            FROM users WHERE id = ?
        """, (user_id,))
        row = await cur.fetchone()
        if row:
            return dict(row)
        return None


async def update_user_activity(user_id: int):
    """Update user's last active timestamp"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_active = ? WHERE id = ?", (datetime.now(), user_id))
        await db.commit()


async def set_balance(user_id: int, new_balance: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
        await db.commit()


async def add_balance(user_id: int, amount: int, transaction_type: str = "game_win", description: str = ""):
    """Add balance with transaction logging"""
    user = await get_user(user_id)
    if not user:
        return None
    
    new_bal = user["balance"] + amount
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Update balance
        await db.execute("UPDATE users SET balance = ? WHERE id = ?", (new_bal, user_id))
        
        # Log transaction
        transaction_id = str(uuid.uuid4())
        await db.execute("""
            INSERT INTO transactions (id, user_id, transaction_type, amount, description) 
            VALUES (?, ?, ?, ?, ?)
        """, (transaction_id, user_id, transaction_type, amount, description))
        
        # Update total won if it's a game win
        if transaction_type == "game_win":
            await db.execute("UPDATE users SET total_won = total_won + ? WHERE id = ?", (amount, user_id))
        
        await db.commit()
    
    return new_bal


async def deduct_balance(user_id: int, amount: int, transaction_type: str = "game_bet", description: str = ""):
    """Deduct balance with comprehensive checks and logging"""
    user = await get_user(user_id)
    if not user:
        return None
    
    if user["balance"] < amount:
        return False
    
    # Security check - prevent excessive betting
    if amount > MAX_BET_PER_GAME:
        security_manager.add_security_alert(
            user_id, "excessive_bet", SecurityLevel.HIGH, 
            f"Attempted bet of {amount} exceeds maximum {MAX_BET_PER_GAME}"
        )
        return False
    
    # Check daily loss limit
    if not security_manager.check_daily_loss_limit(user_id, amount):
        return "daily_limit_exceeded"
    
    new_bal = user["balance"] - amount
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Update balance and statistics
        await db.execute("""
            UPDATE users SET balance = ?, total_wagered = total_wagered + ?, games_played = games_played + 1 
            WHERE id = ?
        """, (new_bal, amount, user_id))
        
        # Log transaction
        transaction_id = str(uuid.uuid4())
        await db.execute("""
            INSERT INTO transactions (id, user_id, transaction_type, amount, description) 
            VALUES (?, ?, ?, ?, ?)
        """, (transaction_id, user_id, transaction_type, -amount, description))
        
        await db.commit()
    
    # Record loss for security tracking
    security_manager.record_loss(user_id, amount)
    
    # Add to jackpot pools
    if transaction_type == "game_bet":
        jackpot_manager.add_to_jackpot("mega_slots", amount)
    
    return new_bal


# --- Cooldown System ---
cooldown_tracker = defaultdict(float)

def is_on_cooldown(user_id: int, cooldown_seconds: int = 2) -> bool:
    """Check if user is on cooldown"""
    current_time = time.time()
    last_action = cooldown_tracker[user_id]
    return (current_time - last_action) < cooldown_seconds

def set_cooldown(user_id: int):
    """Set cooldown for user"""
    cooldown_tracker[user_id] = time.time()

# --- Enhanced Game Engine ---
class GameEngine:
    def __init__(self):
        self.rtp_rates = {  # Return to Player rates for balanced gameplay
            'slots': 0.96,
            'blackjack': 0.985,
            'roulette': 0.973,
            'dice': 0.98,
            'crash': 0.99,
            'mines': 0.97,
            'hilo': 0.98,
            'plinko': 0.975
        }
    
    def calculate_fair_outcome(self, game_type: str, bet_amount: int, user_history: dict) -> dict:
        """Calculate fair game outcome based on RTP and user history"""
        base_rtp = self.rtp_rates.get(game_type, 0.95)
        
        # Adjust RTP based on recent user performance (streak prevention)
        recent_wins = user_history.get('recent_win_streak', 0)
        recent_losses = user_history.get('recent_loss_streak', 0)
        
        # Slight adjustment for balance (max ±5%)
        if recent_wins > 5:
            adjusted_rtp = max(base_rtp - 0.05, 0.90)
        elif recent_losses > 3:
            adjusted_rtp = min(base_rtp + 0.05, 0.99)
        else:
            adjusted_rtp = base_rtp
        
        # Calculate if this should be a win
        win_chance = adjusted_rtp
        is_win = random.random() < win_chance
        
        return {
            'is_win': is_win,
            'adjusted_rtp': adjusted_rtp,
            'win_chance': win_chance
        }
    
    def generate_multiplier(self, game_type: str, is_win: bool) -> float:
        """Generate appropriate multiplier for wins"""
        if not is_win:
            return 0.0
        
        # Base multiplier distribution
        rand = random.random()
        
        if game_type == 'slots':
            if rand < 0.6:  # 60% chance
                return round(random.uniform(1.1, 2.0), 2)
            elif rand < 0.85:  # 25% chance  
                return round(random.uniform(2.0, 5.0), 2)
            elif rand < 0.98:  # 13% chance
                return round(random.uniform(5.0, 20.0), 2)
            else:  # 2% chance - big win
                return round(random.uniform(20.0, 100.0), 2)
        
        elif game_type == 'crash':
            if rand < 0.4:
                return round(random.uniform(1.01, 1.2), 2)
            elif rand < 0.7:
                return round(random.uniform(1.2, 2.0), 2)
            elif rand < 0.9:
                return round(random.uniform(2.0, 5.0), 2)
            else:
                return round(random.uniform(5.0, 50.0), 2)
        
        else:  # Default for other games
            if rand < 0.7:
                return round(random.uniform(1.5, 3.0), 2)
            elif rand < 0.95:
                return round(random.uniform(3.0, 10.0), 2)
            else:
                return round(random.uniform(10.0, 50.0), 2)

# Initialize game engine
game_engine = GameEngine()


async def log_game_session(user_id: int, game_type: str, bet_amount: int, win_amount: int, 
                          multiplier: float, result: GameResult, game_data: dict = None):
    """Log a complete game session"""
    session_id = str(uuid.uuid4())
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO game_sessions 
            (id, user_id, game_type, bet_amount, win_amount, multiplier, result, game_data) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, game_type, bet_amount, win_amount, multiplier, result.value, 
              json.dumps(game_data) if game_data else None))
        await db.commit()
    
    return session_id


async def get_user_statistics(user_id: int) -> dict:
    """Get comprehensive user statistics"""
    user = await get_user(user_id)
    if not user:
        return {}
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Get game statistics
        cur = await db.execute("""
            SELECT game_type, COUNT(*) as games, SUM(bet_amount) as total_bet, 
                   SUM(win_amount) as total_win, AVG(multiplier) as avg_multiplier
            FROM game_sessions WHERE user_id = ? 
            GROUP BY game_type
        """, (user_id,))
        game_stats = await cur.fetchall()
        
        # Get recent transactions
        cur = await db.execute("""
            SELECT transaction_type, amount, description, timestamp 
            FROM transactions WHERE user_id = ? 
            ORDER BY timestamp DESC LIMIT 10
        """, (user_id,))
        recent_transactions = await cur.fetchall()
        
        # Get achievements
        cur = await db.execute("""
            SELECT achievement_name, earned_at 
            FROM achievements WHERE user_id = ? 
            ORDER BY earned_at DESC
        """, (user_id,))
        achievements = await cur.fetchall()
    
    return {
        "user": user,
        "game_stats": [dict(row) for row in game_stats],
        "recent_transactions": [dict(row) for row in recent_transactions],
        "achievements": [dict(row) for row in achievements],
        "profit_loss": user["total_won"] - user["total_wagered"],
        "win_rate": (user["total_won"] / user["total_wagered"] * 100) if user["total_wagered"] > 0 else 0
    }

# --- Slots implementation (full) ---
# Slots Configuration from Environment Variables
SLOTS_CHERRY_WEIGHT = int(os.environ.get("SLOTS_CHERRY_WEIGHT", "50"))
SLOTS_LEMON_WEIGHT = int(os.environ.get("SLOTS_LEMON_WEIGHT", "30"))
SLOTS_ORANGE_WEIGHT = int(os.environ.get("SLOTS_ORANGE_WEIGHT", "10"))
SLOTS_BELL_WEIGHT = int(os.environ.get("SLOTS_BELL_WEIGHT", "7"))
SLOTS_DIAMOND_WEIGHT = int(os.environ.get("SLOTS_DIAMOND_WEIGHT", "3"))

SLOTS_CHERRY_PAYOUT = int(os.environ.get("SLOTS_CHERRY_PAYOUT", "10"))
SLOTS_LEMON_PAYOUT = int(os.environ.get("SLOTS_LEMON_PAYOUT", "20"))
SLOTS_ORANGE_PAYOUT = int(os.environ.get("SLOTS_ORANGE_PAYOUT", "30"))
SLOTS_BELL_PAYOUT = int(os.environ.get("SLOTS_BELL_PAYOUT", "50"))
SLOTS_DIAMOND_PAYOUT = int(os.environ.get("SLOTS_DIAMOND_PAYOUT", "100"))

SYMBOLS = [
    ("🍒", SLOTS_CHERRY_WEIGHT),
    ("🍋", SLOTS_LEMON_WEIGHT),
    ("🍊", SLOTS_ORANGE_WEIGHT),
    ("🔔", SLOTS_BELL_WEIGHT),
    ("💎", SLOTS_DIAMOND_WEIGHT),
]

PAYOUTS = {
    "🍒": SLOTS_CHERRY_PAYOUT,
    "🍋": SLOTS_LEMON_PAYOUT,
    "🍊": SLOTS_ORANGE_PAYOUT,
    "🔔": SLOTS_BELL_PAYOUT,
    "💎": SLOTS_DIAMOND_PAYOUT
}

def weighted_choice():
    items = []
    for sym, weight in SYMBOLS:
        items.extend([sym] * weight)
    return random.choice(items)


async def handle_slots_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback handler for slots bets. callback_data e.g. slots_bet_10"""
    query = update.callback_query
    await query.answer()  # acknowledge
    data = query.data
    user_id = query.from_user.id

    if not data.startswith("slots_bet_"):
        await query.answer("Invalid slots action", show_alert=True)
        return

    try:
        bet = int(data.split("_")[-1])
    except Exception:
        await query.answer("Invalid bet", show_alert=True)
        return

    user = await get_user(user_id)
    if not user:
        await query.answer("Please /start first", show_alert=True)
        return

    if user["balance"] < bet:
        await query.answer("❌ Not enough chips", show_alert=True)
        return

    # deduct immediately
    deduct_res = await deduct_balance(user_id, bet)
    if deduct_res is False:
        await query.answer("❌ Not enough chips", show_alert=True)
        return

    # spin 3 reels
    reel = [weighted_choice() for _ in range(3)]

    # winning logic: all three equal -> payout
    if reel[0] == reel[1] == reel[2]:
        symbol = reel[0]
        multiplier = PAYOUTS.get(symbol, 0)
        win_amount = bet * multiplier
        # credit wins
        await add_balance(user_id, win_amount)
        text = f"🎰 {' '.join(reel)}\n\n🎉 *JACKPOT!* You hit {symbol}{symbol}{symbol} and won *{win_amount:,} chips* (x{multiplier})!"
    else:
        text = f"🎰 {' '.join(reel)}\n\n😢 No match. You lost *{bet:,} chips*."

    user_after = await get_user(user_id)
    keyboard = [
        [
            InlineKeyboardButton("Play 10", callback_data="slots_bet_10"),
            InlineKeyboardButton("Play 25", callback_data="slots_bet_25")
        ],
        [
            InlineKeyboardButton("Play 50", callback_data="slots_bet_50"),
            InlineKeyboardButton("Play 100", callback_data="slots_bet_100")
        ],
        [InlineKeyboardButton("🔙 Back to Mini Casino", callback_data="mini_casino_app")]
    ]
    await query.edit_message_text(
        f"{text}\n\n💰 Balance: *{user_after['balance']:,} chips*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# --- Blackjack placeholder (simple sim) ---
async def handle_blackjack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if not data.startswith("blackjack_bet_"):
        await query.answer("Unknown blackjack action", show_alert=True)
        return
    try:
        bet = int(data.split("_")[-1])
    except Exception:
        await query.answer("Invalid bet", show_alert=True)
        return

    user = await get_user(user_id)
    if not user or user["balance"] < bet:
        await query.answer("Not enough chips", show_alert=True)
        return

    await deduct_balance(user_id, bet)
    r = random.random()
    if r < 0.10:
        win = int(bet * 1.5)
        # return bet + win
        await add_balance(user_id, bet + win)
        result = f"🃏 Blackjack! You win {win:,} chips (3:2)."
    elif r < 0.60:
        # push: return bet
        await add_balance(user_id, bet)
        result = "🤝 Push — your bet was returned."
    else:
        result = "💥 Dealer wins. You lost your bet."

    user_after = await get_user(user_id)
    keyboard = [[InlineKeyboardButton("🔙 Back to Mini Casino", callback_data="mini_casino_app")]]
    await query.edit_message_text(
        f"{result}\n\n💰 Balance: *{user_after['balance']:,} chips*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# --- Roulette placeholder ---
async def show_roulette_menu(update: Update, balance: int):
    keyboard = [
        [InlineKeyboardButton("Bet 15 on Red", callback_data="roulette_bet_red_15")],
        [InlineKeyboardButton("Bet 15 on Black", callback_data="roulette_bet_black_15")],
        [InlineKeyboardButton("🔙 Back to Mini Casino", callback_data="mini_casino_app")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text("🎡 Roulette — choose a simple bet:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("🎡 Roulette — choose a simple bet:", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_roulette_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    if len(parts) != 4:
        await query.answer("Invalid roulette action", show_alert=True)
        return
    _, _, color, amt_s = parts
    bet = int(amt_s)
    user_id = query.from_user.id
    user = await get_user(user_id)
    if not user or user["balance"] < bet:
        await query.answer("Not enough chips", show_alert=True)
        return
    await deduct_balance(user_id, bet)
    number = random.randint(0, 36)
    landed_color = "red" if number % 2 == 0 else "black"
    if color == landed_color:
        await add_balance(user_id, bet * 2)
        result = f"🎉 The wheel landed on {number} ({landed_color}). You win {bet*2:,} chips!"
    else:
        result = f"💥 The wheel landed on {number} ({landed_color}). You lost {bet:,} chips."

    user_after = await get_user(user_id)
    keyboard = [[InlineKeyboardButton("🔙 Back to Mini Casino", callback_data="mini_casino_app")]]
    await query.edit_message_text(
        f"{result}\n\n💰 Balance: *{user_after['balance']:,} chips*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# --- Dice placeholder ---
async def show_dice_menu(update: Update, balance: int):
    keyboard = [
        [InlineKeyboardButton("Bet 10 (guess even)", callback_data="dice_bet_even_10")],
        [InlineKeyboardButton("Bet 10 (guess odd)", callback_data="dice_bet_odd_10")],
        [InlineKeyboardButton("🔙 Back to Mini Casino", callback_data="mini_casino_app")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text("🎲 Dice — choose a bet:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("🎲 Dice — choose a bet:", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_dice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    if len(parts) != 4:
        await query.answer("Invalid dice action", show_alert=True)
        return
    _, _, guess, amt = parts
    bet = int(amt)
    user_id = query.from_user.id
    user = await get_user(user_id)
    if not user or user["balance"] < bet:
        await query.answer("Not enough chips", show_alert=True)
        return
    await deduct_balance(user_id, bet)
    roll = random.randint(1, 6)
    if (roll % 2 == 0 and guess == "even") or (roll % 2 == 1 and guess == "odd"):
        await add_balance(user_id, bet * 2)
        result = f"🎉 Rolled {roll}. You win {bet*2:,} chips!"
    else:
        result = f"💥 Rolled {roll}. You lost {bet:,} chips."
    user_after = await get_user(user_id)
    keyboard = [[InlineKeyboardButton("🔙 Back to Mini Casino", callback_data="mini_casino_app")]]
    await query.edit_message_text(
        f"{result}\n\n💰 Balance: *{user_after['balance']:,} chips*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# --- Poker placeholder ---
async def show_poker_menu(update: Update, balance: int):
    keyboard = [
        [InlineKeyboardButton("Sit & Play (placeholder)", callback_data="poker_bet_25")],
        [InlineKeyboardButton("🔙 Back to Mini Casino", callback_data="mini_casino_app")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text("🃏 Poker — placeholder menu", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("🃏 Poker — placeholder menu", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_poker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Poker is a placeholder in this demo. Coming soon!", show_alert=True)

# --- Achievements simple ---
async def show_achievements_menu(update: Update, user_id: int):
    keyboard = [[InlineKeyboardButton("🔙 Back to Mini Casino", callback_data="mini_casino_app")]]
    text = "🏆 Achievements\n\n- Demo achievement system coming soon!"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# --- Command handlers / Menu ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        await update.message.reply_text("❌ Could not identify user. Please try again.")
        return
    user_id = user.id
    if is_on_cooldown(user_id):
        await update.message.reply_text("⏳ Please wait before using this command again.")
        return
    set_cooldown(user_id)
    username = user.username or (user.full_name if hasattr(user, "full_name") else user.first_name)
    existing = await get_user(user_id)
    if not existing:
        await create_user(user_id, username)
        logger.info(f"User registered: {user_id} ({username})")
        # Show welcome message and then game center directly
        await update.message.reply_text(
            f"🎰 *Welcome to Casino Bot, {user.first_name}!*\n\n"
            f"🎉 You've been registered and awarded *100 starting chips*!\n"
            f"🎮 Ready to play? Choose a game below:",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Returning user - show simple panel first
        pass
    
    # Show simple panel for all users (new and returning)
    await show_simple_panel(update, context)


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_on_cooldown(user_id):
        await update.message.reply_text("⏳ Please wait before using this command again.")
        return
    set_cooldown(user_id)
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Please use /start first to register.")
        return
    await update.message.reply_text(f"💰 Your balance: {user['balance']:,} chips")


async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_on_cooldown(user_id):
        await update.message.reply_text("⏳ Please wait before using this command again.")
        return
    set_cooldown(user_id)
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Please use /start first to register.")
        return
    await add_balance(user_id, 50)
    logger.info(f"User {user_id} received daily chips.")
    await update.message.reply_text("🎁 You received 50 daily chips! Use /balance to see your new amount.")


async def stat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_on_cooldown(user_id):
        await update.message.reply_text("⏳ Please wait before using this command again.")
        return
    set_cooldown(user_id)
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Please use /start first to register.")
        return
    text = f"""
📊 *Your Stats*

ID: `{user['id']}`
Username: `{user['username']}`
Balance: *{user['balance']:,} chips*
"""
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def show_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stats callback from inline keyboard"""
    query = update.callback_query
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await query.answer("Please /start first", show_alert=True)
        return
    
    # Get user rank
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE balance > ?", (user['balance'],))
        rank = (await cur.fetchone())[0] + 1
    
    # Determine VIP status
    vip_status = "💎 VIP" if user['balance'] >= 1000 else "🎰 Premium" if user['balance'] >= 500 else "🎲 Regular"
    
    text = f"""
📊 *Your Detailed Stats*

👤 *Player Info:*
• ID: `{user['id']}`
• Username: `{user['username']}`
• Status: {vip_status}

💰 *Financial Info:*
• Balance: *{user['balance']:,}* chips
• Global Rank: *#{rank}*

🎯 *Performance:*
• Account Created: Recent player
• Last Active: Now
• Games Played: Coming soon

🎰 *Achievements:*
• First Deposit: ✅
• High Roller: {'✅' if user['balance'] >= 1000 else '❌'}
• Lucky Streak: Coming soon

Ready to play more games?
"""
    
    keyboard = [
        [InlineKeyboardButton("🎰 Play Games", callback_data="mini_casino_app")],
        [InlineKeyboardButton("🏆 View Leaderboard", callback_data="show_leaderboard")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)


async def show_leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle leaderboard callback from inline keyboard"""
    query = update.callback_query
    
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10")
        rows = await cur.fetchall()
    
    if not rows:
        await query.answer("No players found yet!", show_alert=True)
        return
    
    # Get current user's rank
    user_id = query.from_user.id
    user = await get_user(user_id)
    user_rank = "Not ranked"
    
    if user:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT COUNT(*) FROM users WHERE balance > ?", (user['balance'],))
            rank = (await cur.fetchone())[0] + 1
            user_rank = f"#{rank}"
    
    text = "🏆 *Casino Leaderboard* 🏆\n\n"
    text += f"*Your Rank:* {user_rank}\n\n"
    text += "🎯 *Top 10 Players:*\n\n"
    
    for i, (username, balance) in enumerate(rows, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        display_name = username if username else f"Player_{i}"
        text += f"{medal} *{display_name}*: {balance:,} chips\n"
    
    keyboard = [
        [InlineKeyboardButton("📊 My Stats", callback_data="show_stats")],
        [InlineKeyboardButton("🎰 Play Games", callback_data="mini_casino_app")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)


async def daily_bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle daily bonus callback from inline keyboard"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if is_on_cooldown(user_id):
        await query.answer("⏳ Please wait before claiming bonus again.", show_alert=True)
        return
    
    set_cooldown(user_id)
    user = await get_user(user_id)
    
    if not user:
        await query.answer("Please /start first", show_alert=True)
        return
    
    # Generate random bonus amount
    bonus_amount = random.randint(DAILY_BONUS_MIN, DAILY_BONUS_MAX)
    await add_balance(user_id, bonus_amount)
    
    text = f"""
🎁 *Daily Bonus Claimed!* 🎁

💰 *You received:* {bonus_amount} chips!

✨ *Bonus Details:*
• Daily bonus range: {DAILY_BONUS_MIN}-{DAILY_BONUS_MAX} chips
• Next bonus: Available anytime (2 sec cooldown)
• VIP players get bonus multipliers!

🎯 *Your Updated Balance:* {user['balance'] + bonus_amount:,} chips

Ready to play some games?
"""
    
    keyboard = [
        [InlineKeyboardButton("🎰 Play Games", callback_data="mini_casino_app")],
        [InlineKeyboardButton("📊 My Stats", callback_data="show_stats")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="main_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)


# --- Stake-Style Category Handlers ---

async def stake_originals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stake's Original Games category"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await query.answer("Please /start first", show_alert=True)
        return
    
    text = f"""
🔥 **STAKE ORIGINALS** 🔥

💰 **Your Balance:** {user['balance']:,} chips

🎮 **Exclusive Stake Games:**
These games are built in-house with the best odds and features!

**🚀 CRASH** - Watch the multiplier climb and cash out before it crashes!
**💣 MINES** - Navigate a minefield for massive multipliers
**🏀 PLINKO** - Drop balls through pegs for random rewards  
**🃏 HI-LO** - Predict higher or lower card values
**🎲 DICE** - Roll for even/odd with custom multipliers
**🎡 WHEEL** - Spin the wheel of fortune for instant wins

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🎯 House Edge: 1% (Industry leading)**
**⚡ Provably Fair: All games verified**
**💎 Max Win: 10,000x your bet**

Select a game to play:
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 CRASH (Most Popular)", callback_data="mini_crash"), InlineKeyboardButton("💣 MINES (High Risk)", callback_data="mini_mines")],
        [InlineKeyboardButton("🏀 PLINKO (Pure Luck)", callback_data="mini_plinko"), InlineKeyboardButton("🃏 HI-LO (Skill Based)", callback_data="mini_hilo")],
        [InlineKeyboardButton("🎲 DICE (Classic)", callback_data="stake_dice"), InlineKeyboardButton("🎡 WHEEL (Instant Win)", callback_data="stake_wheel")],
        [InlineKeyboardButton("📊 Game Stats", callback_data="stake_originals_stats"), InlineKeyboardButton("🎮 Random Game", callback_data="stake_random_original")],
        [InlineKeyboardButton("🔙 Back to Casino", callback_data="mini_casino_app")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def stake_slots_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stake's Slots category"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await query.answer("Please /start first", show_alert=True)
        return
    
    text = f"""
🎰 **SLOT MACHINES** 🎰

💰 **Your Balance:** {user['balance']:,} chips

🎮 **Premium Slot Collection:**
Experience the best slot games with massive jackpots!

**💎 MEGA SLOTS** - Progressive jackpot slots (Current: 1,000,000 chips)
**🔥 FIRE SLOTS** - High volatility, big multipliers
**🎯 CLASSIC SLOTS** - Traditional 3-reel action
**🚀 TURBO SLOTS** - Fast-paced automated spins
**👑 VIP SLOTS** - Exclusive high-limit tables
**🎪 BONUS SLOTS** - Feature-rich bonus rounds

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🎰 RTP: 96.5% average**
**🏆 Max Win: 50,000x bet**
**⚡ Auto Spin Available**
**🎁 Free Spins: Unlock bonus rounds**

Choose your slot experience:
"""
    
    keyboard = [
        [InlineKeyboardButton("💎 MEGA SLOTS (Jackpot)", callback_data="stake_mega_slots"), InlineKeyboardButton("🔥 FIRE SLOTS (High Risk)", callback_data="stake_fire_slots")],
        [InlineKeyboardButton("🎯 CLASSIC SLOTS", callback_data="stake_classic_slots"), InlineKeyboardButton("🚀 TURBO SLOTS", callback_data="stake_turbo_slots")],
        [InlineKeyboardButton("👑 VIP SLOTS (High Limit)", callback_data="stake_vip_slots"), InlineKeyboardButton("🎪 BONUS SLOTS", callback_data="stake_bonus_slots")],
        [InlineKeyboardButton("🎰 Random Slot", callback_data="stake_random_slot"), InlineKeyboardButton("📊 Slot Stats", callback_data="stake_slot_stats")],
        [InlineKeyboardButton("🔙 Back to Casino", callback_data="mini_casino_app")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def stake_live_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stake's Live Casino category"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await query.answer("Please /start first", show_alert=True)
        return
    
    text = f"""
🃏 **LIVE CASINO** 🃏

💰 **Your Balance:** {user['balance']:,} chips

🎮 **Real Dealers, Real Time:**
Play with professional dealers via HD streaming!

**🃏 LIVE BLACKJACK** - Beat the dealer to 21
**🎡 LIVE ROULETTE** - European & American wheels  
**🃄 LIVE BACCARAT** - Player vs Banker
**🎲 LIVE CRAPS** - Roll the dice with live action
**🃏 LIVE POKER** - Texas Hold'em tournaments
**🎰 LIVE GAME SHOWS** - Interactive bonus rounds

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**📹 HD Video Quality**
**💬 Live Chat with dealers**
**🎯 Multiple camera angles**
**⚡ Real-time gameplay**

**🔴 LIVE NOW:** 127 active tables

Select your live game:
"""
    
    keyboard = [
        [InlineKeyboardButton("🃏 LIVE BLACKJACK", callback_data="stake_live_blackjack"), InlineKeyboardButton("🎡 LIVE ROULETTE", callback_data="stake_live_roulette")],
        [InlineKeyboardButton("🃄 LIVE BACCARAT", callback_data="stake_live_baccarat"), InlineKeyboardButton("🎲 LIVE CRAPS", callback_data="stake_live_craps")],
        [InlineKeyboardButton("🃏 LIVE POKER", callback_data="stake_live_poker"), InlineKeyboardButton("🎰 GAME SHOWS", callback_data="stake_game_shows")],
        [InlineKeyboardButton("👥 Join Random Table", callback_data="stake_random_live"), InlineKeyboardButton("📊 Live Stats", callback_data="stake_live_stats")],
        [InlineKeyboardButton("🔙 Back to Casino", callback_data="mini_casino_app")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def stake_tournaments_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stake's Tournaments section"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await query.answer("Please /start first", show_alert=True)
        return
    
    # Get user rank for tournament eligibility
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE balance > ?", (user['balance'],))
        rank = (await cur.fetchone())[0] + 1
    
    text = f"""
🏆 **TOURNAMENTS** 🏆

💰 **Your Balance:** {user['balance']:,} chips
🏆 **Your Rank:** #{rank}

🎮 **Active Tournaments:**

**🔥 WEEKLY CRASH TOURNAMENT**
Prize Pool: 100,000 chips | Entry: 50 chips
Players: 1,247/2,000 | Ends in: 2d 14h

**💎 MEGA SLOTS CHAMPIONSHIP** 
Prize Pool: 250,000 chips | Entry: 100 chips
Players: 89/500 | Ends in: 6d 8h

**⚡ SPEED ROUNDS (Live)**
Prize Pool: 25,000 chips | Entry: 25 chips
Players: 156/200 | Ends in: 45m

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🥇 1st Place:** 40% of prize pool
**🥈 2nd Place:** 25% of prize pool  
**🥉 3rd Place:** 15% of prize pool
**🎯 Top 10:** Share remaining 20%

Your tournament performance:
• Tournaments Joined: 0
• Best Finish: N/A
• Total Winnings: 0 chips
"""
    
    keyboard = [
        [InlineKeyboardButton("🔥 Join Crash Tournament (50)", callback_data="tournament_crash"), InlineKeyboardButton("💎 Join Slots Championship (100)", callback_data="tournament_slots")],
        [InlineKeyboardButton("⚡ Join Speed Rounds (25)", callback_data="tournament_speed"), InlineKeyboardButton("👑 VIP Tournaments", callback_data="tournament_vip")],
        [InlineKeyboardButton("📊 Tournament History", callback_data="tournament_history"), InlineKeyboardButton("🏆 Leaderboard", callback_data="tournament_leaderboard")],
        [InlineKeyboardButton("🔙 Back to Casino", callback_data="mini_casino_app")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def stake_wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stake's Wallet section"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    if not user:
        await query.answer("Please /start first", show_alert=True)
        return
    # Calculate some wallet stats
    balance = user['balance']
    # Simulated transaction history
    transactions = [
        ("🎰 Mega Slots Win", "+2,500", "2 hours ago"),
        ("🚀 Crash Game", "-100", "3 hours ago"),
        ("🎁 Daily Bonus", "+50", "1 day ago"),
        ("💣 Mines Win", "+750", "1 day ago"),
        ("🏆 Tournament Entry", "-25", "2 days ago")
    ]
    text = f"""
💼 *WALLET*

💰 *Balance:* {balance:,} chips

📜 *Recent Transactions:*
"""
    for desc, amt, when in transactions:
        text += f"{desc}: {amt} ({when})\n"
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Casino", callback_data="mini_casino_app")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# --- Global Error Handler ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception: {context.error}")
    try:
        if update and hasattr(update, 'message') and update.message:
            await update.message.reply_text("❌ An unexpected error occurred. Please try again later.")
        elif update and hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer("❌ An error occurred. Please try again.", show_alert=True)
    except Exception:
        pass

# --- /help Command ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🎰 *Casino Bot Help*
/start - Register or open main menu
/balance - Show your chip balance
/daily - Claim daily bonus
/games - Open games menu
/stat - Show your stats
/leaderboard - Top 10 players
/help - Show this help message
/about - About this bot
"""
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# --- /leaderboard Command ---
async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10")
        rows = await cur.fetchall()
    if not rows:
        await update.message.reply_text("🏆 No players found yet!")
        return
    text = "🏆 *Top 10 Players* 🏆\n\n"
    for i, (username, balance) in enumerate(rows, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} {username or 'Anonymous'}: *{balance:,}* chips\n"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# --- /about Command ---
async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"""
🤖 *About Casino Bot*
Version: {BOT_VERSION}
Developer: @casino_support
Stake-style casino for Telegram. Play responsibly!
"""
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# --- Admin Ban/Unban Commands ---
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    ban_id = int(context.args[0])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 1 WHERE id = ?", (ban_id,))
        await db.commit()
    await update.message.reply_text(f"User {ban_id} has been banned.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    unban_id = int(context.args[0])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 0 WHERE id = ?", (unban_id,))
        await db.commit()
    await update.message.reply_text(f"User {unban_id} has been unbanned.")

# --- Fallback Handler ---
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Unknown command. Use /help for a list of commands.")

# --- Health Check Endpoint (for production monitoring) ---
async def health_check_handler(request):
    return aiohttp.web.json_response({"status": "ok", "service": "casino-bot"})

# --- Register Handlers in Main ---
# ...existing code...
async def show_simple_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        user_id = query.from_user.id
    else:
        user_id = update.effective_user.id
    user_data = await get_user(user_id)
    if not user_data:
        if query:
            await query.answer("Please /start first", show_alert=True)
        else:
            await update.message.reply_text("Please /start first")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE balance > ?", (user_data['balance'],))
        rank = (await cur.fetchone())[0] + 1
    balance = user_data['balance']
    if balance >= VIP_DIAMOND_REQUIRED:
        status = "💎 Diamond VIP"
        status_emoji = "💎"
    elif balance >= VIP_GOLD_REQUIRED:
        status = "🥇 Gold VIP"
        status_emoji = "🥇"
    elif balance >= VIP_SILVER_REQUIRED:
        status = "🥈 Silver VIP"
        status_emoji = "🥈"
    else:
        status = "🥉 Bronze Member"
        status_emoji = "🆕"
    keyboard = [
        [InlineKeyboardButton("🎮 Enter Mini Casino", callback_data="mini_casino_app")],
        [InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily_bonus"), InlineKeyboardButton("📊 My Stats", callback_data="show_stats")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard"), InlineKeyboardButton("❓ Help", callback_data="show_help")]
    ]
    text = f"""
{status_emoji} *Welcome to Casino Bot* {status_emoji}

💰 *Balance:* {user_data['balance']:,} chips
🏆 *Rank:* `#{rank}`
👤 *Status:* {status}

🎮 Ready to play? Enter the Mini Casino for all games!
🎁 Don't forget to claim your daily bonus
📊 Check your stats and ranking anytime

Have fun and play responsibly! 🍀
"""
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)