#!/usr/bin/env python3
"""
Flask Backend API for Stake Casino Bot
Provides API endpoints for balance management, game logic, and user data
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from werkzeug.exceptions import BadRequest

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "casino_users.db")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5001))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

class DatabaseManager:
    """Database manager for the Flask API"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    balance REAL DEFAULT 1000.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    balance_before REAL NOT NULL,
                    balance_after REAL NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_telegram_id ON users(telegram_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_telegram_id ON transactions(telegram_id)")
            
            conn.commit()
            logger.info("✅ Database initialized")
    
    @contextmanager
    def get_db_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by telegram ID"""
        with self.get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM users WHERE telegram_id = ?", 
                (telegram_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def create_user(self, telegram_id: int, username: str = None) -> Dict[str, Any]:
        """Create new user"""
        with self.get_db_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO users (telegram_id, username, balance) 
                VALUES (?, ?, ?)
            """, (telegram_id, username, 1000.0))
            conn.commit()
        
        return self.get_user(telegram_id)
    
    def update_balance(self, telegram_id: int, new_balance: float, transaction_type: str = "manual", description: str = "") -> bool:
        """Update user balance with transaction logging"""
        with self.get_db_connection() as conn:
            # Get current balance
            cursor = conn.execute(
                "SELECT balance FROM users WHERE telegram_id = ?", 
                (telegram_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False
            
            old_balance = row['balance']
            
            # Update balance
            conn.execute("""
                UPDATE users 
                SET balance = ?, last_active = CURRENT_TIMESTAMP 
                WHERE telegram_id = ?
            """, (new_balance, telegram_id))
            
            # Log transaction
            conn.execute("""
                INSERT INTO transactions 
                (telegram_id, type, amount, balance_before, balance_after, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (telegram_id, transaction_type, new_balance - old_balance, old_balance, new_balance, description))
            
            conn.commit()
            return True
    
    def get_transactions(self, telegram_id: int, limit: int = 10) -> list:
        """Get user transaction history"""
        with self.get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM transactions 
                WHERE telegram_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (telegram_id, limit))
            return [dict(row) for row in cursor.fetchall()]

# Initialize database manager
db_manager = DatabaseManager(DATABASE_PATH)

# API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/balance/<int:telegram_id>', methods=['GET'])
def get_balance(telegram_id: int):
    """Get user balance"""
    try:
        user = db_manager.get_user(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'telegram_id': telegram_id,
            'balance': user['balance'],
            'username': user['username'],
            'last_active': user['last_active']
        })
    
    except Exception as e:
        logger.error(f"❌ Error getting balance for {telegram_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/user/<int:telegram_id>', methods=['GET'])
def get_user(telegram_id: int):
    """Get user information"""
    try:
        user = db_manager.get_user(telegram_id)
        if not user:
            # Create user if not exists
            user = db_manager.create_user(telegram_id)
        
        # Get recent transactions
        transactions = db_manager.get_transactions(telegram_id, 5)
        
        return jsonify({
            'user': dict(user),
            'transactions': transactions
        })
    
    except Exception as e:
        logger.error(f"❌ Error getting user {telegram_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/bet', methods=['POST'])
def process_bet():
    """Process a game bet"""
    try:
        data = request.get_json()
        
        if not data:
            raise BadRequest("No JSON data provided")
        
        telegram_id = data.get('telegram_id')
        amount = data.get('amount')
        game_type = data.get('game_type', 'unknown')
        
        if not telegram_id or not amount:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if amount <= 0:
            return jsonify({'error': 'Bet amount must be positive'}), 400
        
        # Get user
        user = db_manager.get_user(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        current_balance = user['balance']
        
        # Check if user has enough balance
        if current_balance < amount:
            return jsonify({
                'success': False,
                'error': 'Insufficient balance',
                'balance': current_balance
            }), 400
        
        # Simple game logic (50% win chance for demo)
        import random
        win = random.random() < 0.5
        
        if win:
            # Win: double the bet
            winnings = amount * 2
            new_balance = current_balance + winnings - amount
            result = 'win'
            description = f"Won {winnings:.2f} chips playing {game_type}"
        else:
            # Lose: lose the bet
            new_balance = current_balance - amount
            result = 'lose'
            description = f"Lost {amount:.2f} chips playing {game_type}"
        
        # Update balance
        success = db_manager.update_balance(
            telegram_id, 
            new_balance, 
            f"bet_{result}", 
            description
        )
        
        if not success:
            return jsonify({'error': 'Failed to update balance'}), 500
        
        return jsonify({
            'success': True,
            'result': result,
            'amount_bet': amount,
            'amount_won': winnings if win else 0,
            'balance_before': current_balance,
            'balance_after': new_balance,
            'game_type': game_type
        })
    
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"❌ Error processing bet: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/transactions/<int:telegram_id>', methods=['GET'])
def get_transactions(telegram_id: int):
    """Get user transaction history"""
    try:
        limit = request.args.get('limit', 10, type=int)
        transactions = db_manager.get_transactions(telegram_id, limit)
        
        return jsonify({
            'telegram_id': telegram_id,
            'transactions': transactions,
            'count': len(transactions)
        })
    
    except Exception as e:
        logger.error(f"❌ Error getting transactions for {telegram_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/deposit', methods=['POST'])
def process_deposit():
    """Process a deposit (placeholder)"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        amount = data.get('amount')
        method = data.get('method', 'manual')
        
        if not telegram_id or not amount:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if amount <= 0:
            return jsonify({'error': 'Deposit amount must be positive'}), 400
        
        # Get user
        user = db_manager.get_user(telegram_id)
        if not user:
            user = db_manager.create_user(telegram_id)
        
        current_balance = user['balance']
        new_balance = current_balance + amount
        
        # Update balance
        success = db_manager.update_balance(
            telegram_id, 
            new_balance, 
            "deposit", 
            f"Deposit via {method}: +{amount:.2f} chips"
        )
        
        if not success:
            return jsonify({'error': 'Failed to process deposit'}), 500
        
        return jsonify({
            'success': True,
            'amount': amount,
            'method': method,
            'balance_before': current_balance,
            'balance_after': new_balance
        })
    
    except Exception as e:
        logger.error(f"❌ Error processing deposit: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/withdraw', methods=['POST'])
def process_withdrawal():
    """Process a withdrawal (placeholder)"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        amount = data.get('amount')
        method = data.get('method', 'manual')
        
        if not telegram_id or not amount:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if amount <= 0:
            return jsonify({'error': 'Withdrawal amount must be positive'}), 400
        
        # Get user
        user = db_manager.get_user(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        current_balance = user['balance']
        
        # Check minimum withdrawal
        if amount < 50:
            return jsonify({'error': 'Minimum withdrawal is 50 chips'}), 400
        
        # Check sufficient balance
        if current_balance < amount:
            return jsonify({'error': 'Insufficient balance'}), 400
        
        new_balance = current_balance - amount
        
        # Update balance
        success = db_manager.update_balance(
            telegram_id, 
            new_balance, 
            "withdrawal", 
            f"Withdrawal via {method}: -{amount:.2f} chips"
        )
        
        if not success:
            return jsonify({'error': 'Failed to process withdrawal'}), 500
        
        return jsonify({
            'success': True,
            'amount': amount,
            'method': method,
            'balance_before': current_balance,
            'balance_after': new_balance
        })
    
    except Exception as e:
        logger.error(f"❌ Error processing withdrawal: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Mini App Routes
@app.route('/')
def mini_app():
    """Serve the mini app interface"""
    try:
        # Read the mini app HTML file
        with open('miniapp.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        # Fallback to a simple message if file not found
        return """
        <html>
        <head><title>Stake Casino</title></head>
        <body style="background: #0f0f0f; color: #00ff88; font-family: Arial; text-align: center; padding: 50px;">
            <h1>🎰 Stake Casino</h1>
            <p>Mini app file not found. Please make sure miniapp.html is in the same directory.</p>
        </body>
        </html>
        """, 404

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("🚀 Starting Flask API server...")
    logger.info(f"📁 Database: {DATABASE_PATH}")
    logger.info(f"🌐 Port: {FLASK_PORT}")
    
    app.run(
        host='0.0.0.0',
        port=FLASK_PORT,
        debug=FLASK_DEBUG
    )
