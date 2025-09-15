# Litecoin Payment Integration for Telegram Casino Bot
# Handles Litecoin deposits and withdrawals

import os
import asyncio
import logging
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import aiohttp
import json

logger = logging.getLogger(__name__)

# Litecoin Configuration
LTC_TESTNET = os.environ.get("LTC_TESTNET", "false").lower() == "true"
LTC_API_KEY = os.environ.get("LTC_API_KEY", "")
LTC_WEBHOOK_SECRET = os.environ.get("LTC_WEBHOOK_SECRET", "")
LTC_MIN_DEPOSIT = float(os.environ.get("LTC_MIN_DEPOSIT", "0.001"))  # 0.001 LTC minimum
LTC_MIN_WITHDRAWAL = float(os.environ.get("LTC_MIN_WITHDRAWAL", "0.002"))  # 0.002 LTC minimum
LTC_TO_CHIPS_RATE = float(os.environ.get("LTC_TO_CHIPS_RATE", "5000"))  # 1 LTC = 5000 chips

# BlockCypher API endpoints for Litecoin
if LTC_TESTNET:
    BLOCKCYPHER_BASE = "https://api.blockcypher.com/v1/ltc/test3"
else:
    BLOCKCYPHER_BASE = "https://api.blockcypher.com/v1/ltc/main"

class LitecoinPayment:
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def generate_deposit_address(self, user_id: int) -> Dict[str, Any]:
        """Generate a unique Litecoin deposit address for a user"""
        try:
            # Use BlockCypher to generate address
            url = f"{BLOCKCYPHER_BASE}/addrs"
            params = {"token": LTC_API_KEY} if LTC_API_KEY else {}
            
            async with self.session.post(url, params=params) as response:
                if response.status == 201:
                    data = await response.json()
                    address = data.get("address")
                    private_key = data.get("private")
                    
                    # Store address mapping (implement your own storage)
                    await self._store_address_mapping(user_id, address, private_key)
                    
                    return {
                        "success": True,
                        "address": address,
                        "network": "testnet" if LTC_TESTNET else "mainnet",
                        "min_amount": LTC_MIN_DEPOSIT,
                        "rate": f"1 LTC = {LTC_TO_CHIPS_RATE:,} chips"
                    }
                else:
                    error_data = await response.text()
                    logger.error(f"Failed to generate LTC address: {error_data}")
                    return {"success": False, "error": "Failed to generate address"}
                    
        except Exception as e:
            logger.error(f"Error generating LTC address: {e}")
            return {"success": False, "error": str(e)}
    
    async def check_address_balance(self, address: str) -> Dict[str, Any]:
        """Check the balance of a Litecoin address"""
        try:
            url = f"{BLOCKCYPHER_BASE}/addrs/{address}/balance"
            params = {"token": LTC_API_KEY} if LTC_API_KEY else {}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    balance_satoshi = data.get("balance", 0)
                    unconfirmed_balance = data.get("unconfirmed_balance", 0)
                    
                    # Convert from satoshi to LTC (1 LTC = 100,000,000 satoshi)
                    balance_ltc = balance_satoshi / 100000000
                    unconfirmed_ltc = unconfirmed_balance / 100000000
                    
                    return {
                        "success": True,
                        "balance": balance_ltc,
                        "unconfirmed": unconfirmed_ltc,
                        "total": balance_ltc + unconfirmed_ltc
                    }
                else:
                    return {"success": False, "error": "Failed to check balance"}
                    
        except Exception as e:
            logger.error(f"Error checking LTC balance: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_deposit(self, user_id: int, address: str, amount_ltc: float) -> Dict[str, Any]:
        """Process a Litecoin deposit and convert to chips"""
        try:
            if amount_ltc < LTC_MIN_DEPOSIT:
                return {
                    "success": False, 
                    "error": f"Minimum deposit is {LTC_MIN_DEPOSIT} LTC"
                }
            
            # Convert LTC to chips
            chips_amount = int(amount_ltc * LTC_TO_CHIPS_RATE)
            
            # Update user balance (implement your database update)
            success = await self._update_user_balance(user_id, chips_amount)
            
            if success:
                # Log transaction
                await self._log_crypto_transaction(
                    user_id=user_id,
                    transaction_type="deposit",
                    crypto_amount=amount_ltc,
                    crypto_currency="LTC",
                    chips_amount=chips_amount,
                    address=address
                )
                
                return {
                    "success": True,
                    "amount_ltc": amount_ltc,
                    "chips_received": chips_amount,
                    "rate": LTC_TO_CHIPS_RATE
                }
            else:
                return {"success": False, "error": "Failed to update balance"}
                
        except Exception as e:
            logger.error(f"Error processing LTC deposit: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_withdrawal(self, user_id: int, ltc_address: str, amount_ltc: float) -> Dict[str, Any]:
        """Create a Litecoin withdrawal transaction"""
        try:
            if amount_ltc < LTC_MIN_WITHDRAWAL:
                return {
                    "success": False,
                    "error": f"Minimum withdrawal is {LTC_MIN_WITHDRAWAL} LTC"
                }
            
            # Calculate chips needed
            chips_needed = int(amount_ltc * LTC_TO_CHIPS_RATE)
            
            # Check user balance (implement your balance check)
            user_balance = await self._get_user_balance(user_id)
            if user_balance < chips_needed:
                return {
                    "success": False,
                    "error": "Insufficient balance"
                }
            
            # Get user's stored private key for withdrawal
            private_key = await self._get_user_private_key(user_id)
            if not private_key:
                return {
                    "success": False,
                    "error": "No withdrawal address configured"
                }
            
            # Create withdrawal transaction using BlockCypher
            tx_data = {
                "inputs": [{"addresses": [await self._get_user_deposit_address(user_id)]}],
                "outputs": [{"addresses": [ltc_address], "value": int(amount_ltc * 100000000)}]
            }
            
            url = f"{BLOCKCYPHER_BASE}/txs/new"
            params = {"token": LTC_API_KEY} if LTC_API_KEY else {}
            
            async with self.session.post(url, json=tx_data, params=params) as response:
                if response.status == 201:
                    unsigned_tx = await response.json()
                    
                    # Sign and send transaction (simplified - implement proper signing)
                    tx_hash = await self._sign_and_send_transaction(unsigned_tx, private_key)
                    
                    if tx_hash:
                        # Deduct chips from user balance
                        await self._update_user_balance(user_id, -chips_needed)
                        
                        # Log transaction
                        await self._log_crypto_transaction(
                            user_id=user_id,
                            transaction_type="withdrawal",
                            crypto_amount=amount_ltc,
                            crypto_currency="LTC",
                            chips_amount=-chips_needed,
                            address=ltc_address,
                            tx_hash=tx_hash
                        )
                        
                        return {
                            "success": True,
                            "tx_hash": tx_hash,
                            "amount_ltc": amount_ltc,
                            "chips_deducted": chips_needed
                        }
                    else:
                        return {"success": False, "error": "Failed to send transaction"}
                else:
                    return {"success": False, "error": "Failed to create transaction"}
                    
        except Exception as e:
            logger.error(f"Error creating LTC withdrawal: {e}")
            return {"success": False, "error": str(e)}
    
    async def _store_address_mapping(self, user_id: int, address: str, private_key: str):
        """Store user address mapping (implement with your database)"""
        # TODO: Implement secure storage of address mappings
        # This should store in your database with proper encryption for private keys
        pass
    
    async def _update_user_balance(self, user_id: int, chips_amount: int) -> bool:
        """Update user balance (implement with your database)"""
        # TODO: Implement balance update using your existing database functions
        try:
            from main import update_balance
            await update_balance(user_id, chips_amount)
            return True
        except Exception as e:
            logger.error(f"Failed to update balance: {e}")
            return False
    
    async def _get_user_balance(self, user_id: int) -> int:
        """Get user balance (implement with your database)"""
        # TODO: Implement balance check using your existing database functions
        try:
            from main import get_user
            user = await get_user(user_id)
            return user['balance'] if user else 0
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return 0
    
    async def _get_user_private_key(self, user_id: int) -> Optional[str]:
        """Get user's private key for withdrawals (implement with your database)"""
        # TODO: Implement secure private key retrieval
        # This should be encrypted in your database
        pass
    
    async def _get_user_deposit_address(self, user_id: int) -> Optional[str]:
        """Get user's deposit address (implement with your database)"""
        # TODO: Implement address retrieval
        pass
    
    async def _sign_and_send_transaction(self, unsigned_tx: Dict, private_key: str) -> Optional[str]:
        """Sign and send transaction (implement proper signing)"""
        # TODO: Implement proper transaction signing and broadcasting
        # This is a simplified placeholder
        return "simulated_tx_hash_" + str(int(time.time()))
    
    async def _log_crypto_transaction(self, user_id: int, transaction_type: str, 
                                    crypto_amount: float, crypto_currency: str,
                                    chips_amount: int, address: str, tx_hash: str = None):
        """Log crypto transaction (implement with your database)"""
        # TODO: Implement transaction logging
        logger.info(f"Crypto transaction: {transaction_type} - User {user_id} - "
                   f"{crypto_amount} {crypto_currency} - {chips_amount} chips - {address}")

# Global instance
litecoin_payment = LitecoinPayment()

# Convenience functions for main bot
async def generate_ltc_deposit_address(user_id: int) -> Dict[str, Any]:
    """Generate Litecoin deposit address for user"""
    async with LitecoinPayment() as ltc:
        return await ltc.generate_deposit_address(user_id)

async def process_ltc_deposit(user_id: int, address: str, amount: float) -> Dict[str, Any]:
    """Process Litecoin deposit"""
    async with LitecoinPayment() as ltc:
        return await ltc.process_deposit(user_id, address, amount)

async def create_ltc_withdrawal(user_id: int, address: str, amount: float) -> Dict[str, Any]:
    """Create Litecoin withdrawal"""
    async with LitecoinPayment() as ltc:
        return await ltc.create_withdrawal(user_id, address, amount)

async def check_ltc_balance(address: str) -> Dict[str, Any]:
    """Check Litecoin address balance"""
    async with LitecoinPayment() as ltc:
        return await ltc.check_address_balance(address)
