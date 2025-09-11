"""
Payment system for the Telegram Casino Bot.

Handles deposits, withdrawals, and payment processing.
"""

import uuid
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import aiosqlite

from bot.database.db import get_db
from bot.database.user import get_user, update_balance

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """Payment-related errors."""
    pass


class PaymentProcessor:
    """Main payment processing class."""
    
    @staticmethod
    async def create_transaction(
        user_id: int,
        transaction_type: str,
        amount: int,
        payment_method: str,
        description: str = ""
    ) -> str:
        """Create a new transaction record."""
        transaction_id = str(uuid.uuid4())
        
        async with aiosqlite.connect("casino.db") as db:
            await db.execute("""
                INSERT INTO transactions 
                (user_id, transaction_type, amount, payment_method, transaction_id, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, transaction_type, amount, payment_method, transaction_id, description))
            await db.commit()
        
        logger.info(f"Created transaction {transaction_id} for user {user_id}: {transaction_type} {amount}")
        return transaction_id
    
    @staticmethod
    async def complete_transaction(transaction_id: str) -> bool:
        """Mark a transaction as completed."""
        async with aiosqlite.connect("casino.db") as db:
            cursor = await db.execute("""
                UPDATE transactions 
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE transaction_id = ? AND status = 'pending'
            """, (transaction_id,))
            await db.commit()
            
            return cursor.rowcount > 0
    
    @staticmethod
    async def fail_transaction(transaction_id: str, reason: str = "") -> bool:
        """Mark a transaction as failed."""
        async with aiosqlite.connect("casino.db") as db:
            cursor = await db.execute("""
                UPDATE transactions 
                SET status = 'failed', description = ?
                WHERE transaction_id = ? AND status = 'pending'
            """, (reason, transaction_id))
            await db.commit()
            
            return cursor.rowcount > 0
    
    @staticmethod
    async def get_transaction(transaction_id: str) -> Optional[Dict]:
        """Get transaction details."""
        async with aiosqlite.connect("casino.db") as db:
            cursor = await db.execute("""
                SELECT * FROM transactions WHERE transaction_id = ?
            """, (transaction_id,))
            row = await cursor.fetchone()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
    
    @staticmethod
    async def get_user_transactions(user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's recent transactions."""
        async with aiosqlite.connect("casino.db") as db:
            cursor = await db.execute("""
                SELECT * FROM transactions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]


class DepositProcessor:
    """Handle deposit operations."""
    
    @staticmethod
    async def process_deposit(
        user_id: int,
        amount: int,
        payment_method: str,
        payment_data: Dict = None
    ) -> Tuple[bool, str]:
        """Process a deposit request."""
        if amount < 100:  # Minimum deposit 100 coins
            return False, "Minimum deposit amount is 100 coins"
        
        if amount > 100000:  # Maximum deposit 100,000 coins
            return False, "Maximum deposit amount is 100,000 coins"
        
        try:
            # Create transaction record
            transaction_id = await PaymentProcessor.create_transaction(
                user_id, "deposit", amount, payment_method, 
                f"Deposit via {payment_method}"
            )
            
            # Simulate payment processing based on method
            success = await DepositProcessor._process_payment_method(
                payment_method, amount, payment_data
            )
            
            if success:
                # Update user balance
                await update_balance(user_id, amount)
                await PaymentProcessor.complete_transaction(transaction_id)
                
                # Record as bonus transaction for tracking
                await PaymentProcessor.create_transaction(
                    user_id, "bonus", amount, "deposit_bonus",
                    f"Deposit completed: {transaction_id}"
                )
                
                return True, f"Deposit successful! Transaction ID: {transaction_id[:8]}"
            else:
                await PaymentProcessor.fail_transaction(
                    transaction_id, "Payment processing failed"
                )
                return False, "Payment processing failed. Please try again."
                
        except Exception as e:
            logger.error(f"Deposit processing error: {e}")
            return False, "An error occurred while processing your deposit"
    
    @staticmethod
    async def _process_payment_method(method: str, amount: int, data: Dict) -> bool:
        """Simulate payment processing for different methods."""
        # In a real implementation, this would integrate with actual payment providers
        
        if method == "telegram_stars":
            # Telegram Stars payment (simplified)
            return True  # Always succeed for demo
        
        elif method == "crypto":
            # Cryptocurrency payment
            # Would integrate with crypto payment processor
            return True  # Always succeed for demo
        
        elif method == "card":
            # Credit/debit card payment
            # Would integrate with Stripe, PayPal, etc.
            return True  # Always succeed for demo
        
        elif method == "demo":
            # Demo payment for testing
            return True
        
        return False


class WithdrawalProcessor:
    """Handle withdrawal operations."""
    
    @staticmethod
    async def process_withdrawal(
        user_id: int,
        amount: int,
        payment_method: str,
        payment_data: Dict = None
    ) -> Tuple[bool, str]:
        """Process a withdrawal request."""
        user = await get_user(user_id)
        if not user:
            return False, "User not found"
        
        if amount < 500:  # Minimum withdrawal 500 coins
            return False, "Minimum withdrawal amount is 500 coins"
        
        if amount > user['balance']:
            return False, "Insufficient balance"
        
        # Check for minimum balance after withdrawal
        if user['balance'] - amount < 100:
            return False, "You must keep at least 100 coins in your account"
        
        try:
            # Create transaction record
            transaction_id = await PaymentProcessor.create_transaction(
                user_id, "withdrawal", amount, payment_method,
                f"Withdrawal via {payment_method}"
            )
            
            # Deduct from user balance immediately (will be refunded if withdrawal fails)
            await update_balance(user_id, -amount)
            
            # Simulate withdrawal processing
            success = await WithdrawalProcessor._process_withdrawal_method(
                payment_method, amount, payment_data
            )
            
            if success:
                await PaymentProcessor.complete_transaction(transaction_id)
                return True, f"Withdrawal request submitted! Transaction ID: {transaction_id[:8]}\nProcessing time: 1-3 business days"
            else:
                # Refund the amount
                await update_balance(user_id, amount)
                await PaymentProcessor.fail_transaction(
                    transaction_id, "Withdrawal processing failed"
                )
                return False, "Withdrawal processing failed. Amount refunded."
                
        except Exception as e:
            logger.error(f"Withdrawal processing error: {e}")
            # Ensure amount is refunded on error
            await update_balance(user_id, amount)
            return False, "An error occurred while processing your withdrawal"
    
    @staticmethod
    async def _process_withdrawal_method(method: str, amount: int, data: Dict) -> bool:
        """Simulate withdrawal processing for different methods."""
        # In a real implementation, this would integrate with actual payment providers
        
        if method == "crypto":
            # Cryptocurrency withdrawal
            return True  # Always succeed for demo
        
        elif method == "card":
            # Bank card withdrawal
            return True  # Always succeed for demo
        
        elif method == "paypal":
            # PayPal withdrawal
            return True  # Always succeed for demo
        
        return False


class PaymentMethodManager:
    """Manage user payment methods."""
    
    @staticmethod
    async def add_payment_method(
        user_id: int,
        method_type: str,
        method_data: Dict
    ) -> bool:
        """Add a new payment method for user."""
        try:
            async with aiosqlite.connect("casino.db") as db:
                await db.execute("""
                    INSERT INTO payment_methods (user_id, method_type, method_data)
                    VALUES (?, ?, ?)
                """, (user_id, method_type, json.dumps(method_data)))
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding payment method: {e}")
            return False
    
    @staticmethod
    async def get_user_payment_methods(user_id: int) -> List[Dict]:
        """Get all payment methods for a user."""
        async with aiosqlite.connect("casino.db") as db:
            cursor = await db.execute("""
                SELECT * FROM payment_methods 
                WHERE user_id = ? AND is_active = 1
                ORDER BY created_at DESC
            """, (user_id,))
            rows = await cursor.fetchall()
            
            columns = [desc[0] for desc in cursor.description]
            methods = []
            for row in rows:
                method = dict(zip(columns, row))
                method['method_data'] = json.loads(method['method_data'])
                methods.append(method)
            
            return methods
    
    @staticmethod
    async def remove_payment_method(user_id: int, method_id: int) -> bool:
        """Remove a payment method."""
        try:
            async with aiosqlite.connect("casino.db") as db:
                cursor = await db.execute("""
                    UPDATE payment_methods 
                    SET is_active = 0 
                    WHERE id = ? AND user_id = ?
                """, (method_id, user_id))
                await db.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing payment method: {e}")
            return False
