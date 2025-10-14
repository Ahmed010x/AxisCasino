"""
Cryptocurrency service for handling rates, invoices, and transactions
"""

import re
import time
import uuid
import hashlib
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from ..core.config import config

logger = logging.getLogger(__name__)

class CryptoService:
    """Service for handling cryptocurrency operations"""
    
    SUPPORTED_ASSETS = ["LTC", "TON", "SOL"]
    
    ADDRESS_PATTERNS = {
        'LTC': r'^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$|^ltc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{39,59}$',
        'TON': r'^UQ[a-zA-Z0-9_-]{46,}$',
        'SOL': r'^[1-9A-HJ-NP-Za-km-z]{32,44}$',
    }
    
    def __init__(self):
        self.api_token = config.CRYPTOBOT_API_TOKEN
        self.demo_mode = config.DEMO_MODE
    
    def validate_address(self, asset: str, address: str) -> bool:
        """Validate cryptocurrency address format"""
        if asset not in self.ADDRESS_PATTERNS:
            return False
        
        pattern = self.ADDRESS_PATTERNS[asset]
        return bool(re.match(pattern, address))
    
    async def get_usd_rate(self, asset: str) -> float:
        """Get real-time USD/crypto rate from CryptoBot API"""
        if not self.api_token:
            logger.error("CRYPTOBOT_API_TOKEN not configured")
            return 0.0
        
        url = "https://pay.crypt.bot/api/getExchangeRates"
        headers = {"Crypto-Pay-API-Token": self.api_token}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("ok"):
                            rates = data.get("result", [])
                            for rate in rates:
                                if rate.get("source") == asset and rate.get("target") == "USD":
                                    price = float(rate.get("rate", 0))
                                    if price > 0:
                                        logger.info(f"CryptoBot API: {asset}/USD rate = ${price:.6f}")
                                        return price
                            logger.warning(f"No rate found for {asset}/USD")
                        else:
                            logger.error(f"CryptoBot API error: {data.get('error', {})}")
                    else:
                        logger.error(f"HTTP error {resp.status} fetching rates")
        except Exception as e:
            logger.error(f"Error fetching {asset} rate: {e}")
        
        return 0.0
    
    async def create_invoice(self, asset: str, amount: float, user_id: int, payload: Dict = None) -> Dict:
        """Create a crypto invoice using CryptoBot API"""
        if not self.api_token:
            return {"ok": False, "error": "CryptoBot API token not configured"}
        
        try:
            headers = {
                'Crypto-Pay-API-Token': self.api_token,
                'Content-Type': 'application/json'
            }
            
            # Get USD amount for description
            usd_rate = await self.get_usd_rate(asset)
            usd_amount = amount * usd_rate if usd_rate > 0 else amount
            
            data = {
                'asset': asset,
                'amount': f"{amount:.8f}",
                'description': f'Casino deposit - ${usd_amount:.2f} USD',
                'hidden_message': str(user_id),
                'expires_in': 3600,  # 1 hour
                'allow_comments': False,
                'allow_anonymous': False,
            }
            
            if payload:
                data.update(payload)
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.post('https://pay.crypt.bot/api/createInvoice', 
                                      headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('ok'):
                            logger.info(f"CryptoBot invoice created: {result.get('result', {}).get('invoice_id')}")
                            return result
                        else:
                            logger.error(f"CryptoBot API error: {result}")
                            return result
                    else:
                        error_text = await response.text()
                        logger.error(f"CryptoBot API error {response.status}: {error_text}")
                        return {"ok": False, "error": f"API error {response.status}"}
                        
        except asyncio.TimeoutError:
            logger.error("Timeout creating crypto invoice")
            return {"ok": False, "error": "Request timeout - please try again"}
        except Exception as e:
            logger.error(f"Error creating crypto invoice: {e}")
            return {"ok": False, "error": str(e)}
    
    async def send_crypto(self, address: str, amount: float, comment: str, asset: str = 'LTC') -> Dict:
        """Send crypto using CryptoBot API (or simulate for demo)"""
        try:
            if self.demo_mode:
                # Demo mode - simulate successful transaction
                fake_hash = hashlib.sha256(f"{address}{amount}{time.time()}".encode()).hexdigest()
                logger.info(f"DEMO: Simulated crypto send: {amount} {asset} to {address}")
                return {
                    "ok": True,
                    "result": {
                        "transaction_hash": fake_hash,
                        "amount": amount,
                        "asset": asset,
                        "status": "completed"
                    }
                }
            
            if not self.api_token:
                return {"ok": False, "error": "API token not configured"}
            
            headers = {
                'Crypto-Pay-API-Token': self.api_token,
                'Content-Type': 'application/json'
            }
            
            data = {
                'user_id': address,
                'asset': asset,
                'amount': f"{amount:.8f}",
                'spend_id': str(uuid.uuid4()),
                'comment': comment
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post('https://pay.crypt.bot/api/transfer', 
                                      headers=headers, json=data) as response:
                    result = await response.json()
                    logger.info(f"CryptoBot transfer result: {result}")
                    return result
                    
        except Exception as e:
            logger.error(f"Error sending crypto: {e}")
            return {"ok": False, "error": str(e)}

# Global crypto service instance
crypto_service = CryptoService()
