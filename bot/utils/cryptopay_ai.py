# bot/utils/cryptopay_ai.py
"""
CryptoPay AI Invoice System for Enhanced Litecoin Deposits
Provides intelligent invoice creation with AI-powered features
"""
import os
import json
import asyncio
import aiohttp
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# CryptoPay AI Configuration
CRYPTOPAY_API_TOKEN = os.environ.get("CRYPTOBOT_API_TOKEN")
CRYPTOPAY_API_URL = "https://pay.crypt.bot/api"
LITECOIN_ASSET = os.environ.get("CRYPTOBOT_LITECOIN_ASSET", "LTCTRC20")

class CryptoPayAI:
    """AI-Enhanced CryptoPay Invoice System"""
    
    def __init__(self):
        self.api_token = CRYPTOPAY_API_TOKEN
        self.api_url = CRYPTOPAY_API_URL
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers"""
        return {
            "Crypto-Pay-API-Token": self.api_token,
            "Content-Type": "application/json"
        }
    
    async def create_ai_invoice(
        self, 
        amount: float, 
        user_id: int, 
        user_data: Dict = None,
        preferences: Dict = None
    ) -> Dict:
        """
        Create an AI-enhanced invoice with intelligent features
        
        Args:
            amount: LTC amount to deposit
            user_id: Telegram user ID
            user_data: User profile data for personalization
            preferences: User preferences for invoice customization
        """
        try:
            # AI-enhanced invoice data
            invoice_data = await self._build_ai_invoice_data(
                amount, user_id, user_data, preferences
            )
            
            headers = self._get_headers()
            
            async with self.session.post(
                f"{self.api_url}/createInvoice",
                headers=headers,
                json=invoice_data
            ) as response:
                result = await response.json()
                
                if result.get("ok"):
                    # Enhance response with AI features
                    enhanced_result = await self._enhance_invoice_response(
                        result, amount, user_id, user_data
                    )
                    return enhanced_result
                else:
                    logger.error(f"CryptoPay AI invoice creation failed: {result}")
                    return result
                    
        except Exception as e:
            logger.error(f"AI invoice creation error: {e}")
            return {"ok": False, "error": str(e)}
    
    async def _build_ai_invoice_data(
        self, 
        amount: float, 
        user_id: int, 
        user_data: Dict = None,
        preferences: Dict = None
    ) -> Dict:
        """Build AI-enhanced invoice data"""
        
        # Base invoice data
        data = {
            "asset": LITECOIN_ASSET,
            "amount": str(amount),
            "description": self._generate_smart_description(amount, user_data),
            "hidden_message": str(user_id),
            "address": True,  # Always request unique address
        }
        
        # AI enhancements based on user data
        if user_data:
            data.update(await self._apply_ai_enhancements(user_data, amount))
        
        # User preferences
        if preferences:
            data.update(await self._apply_user_preferences(preferences))
        
        return data
    
    def _generate_smart_description(self, amount: float, user_data: Dict = None) -> str:
        """Generate intelligent invoice description"""
        if not user_data:
            return f"Casino Deposit: {amount} LTC"
        
        username = user_data.get('username', 'Player')
        games_played = user_data.get('games_played', 0)
        
        if games_played == 0:
            return f"Welcome Deposit for {username}: {amount} LTC"
        elif games_played < 10:
            return f"New Player Deposit for {username}: {amount} LTC"
        elif games_played < 100:
            return f"Regular Player Deposit for {username}: {amount} LTC"
        else:
            return f"VIP Player Deposit for {username}: {amount} LTC"
    
    async def _apply_ai_enhancements(self, user_data: Dict, amount: float) -> Dict:
        """Apply AI-based enhancements to invoice"""
        enhancements = {}
        
        # Smart expiration based on amount
        if amount >= 1.0:
            # Larger deposits get longer expiration
            enhancements["expires_in"] = 3600  # 1 hour
        elif amount >= 0.1:
            enhancements["expires_in"] = 1800  # 30 minutes
        else:
            enhancements["expires_in"] = 900   # 15 minutes
        
        # VIP treatment for high-value users
        total_deposited = user_data.get('total_deposited', 0)
        if total_deposited > 10.0:  # VIP threshold
            enhancements["paid_btn_name"] = "viewChannel"
            enhancements["paid_btn_url"] = "https://t.me/casino_vip_channel"
        else:
            enhancements["paid_btn_name"] = "openChannel"
            enhancements["paid_btn_url"] = "https://t.me/casino_channel"
        
        return enhancements
    
    async def _apply_user_preferences(self, preferences: Dict) -> Dict:
        """Apply user-specific preferences"""
        prefs = {}
        
        # Notification preferences
        if preferences.get('instant_notifications', True):
            prefs["allow_comments"] = True
            prefs["allow_anonymous"] = False
        
        return prefs
    
    async def _enhance_invoice_response(
        self, 
        result: Dict, 
        amount: float, 
        user_id: int,
        user_data: Dict = None
    ) -> Dict:
        """Enhance the invoice response with AI features"""
        
        if not result.get("ok"):
            return result
        
        invoice = result["result"]
        
        # Add AI enhancements to response
        ai_features = {
            "ai_enhanced": True,
            "smart_notifications": True,
            "personalized": bool(user_data),
            "deposit_tier": self._classify_deposit_tier(amount),
            "estimated_confirmation_time": self._estimate_confirmation_time(amount),
            "smart_qr_code": f"bitcoin:{invoice.get('address', '')}?amount={amount}&label=Casino+Deposit",
            "user_friendly_amount": f"{amount:.8f} LTC (${amount * 65:.2f} USD)",  # Approximate USD value
        }
        
        # Add AI features to result
        result["ai_features"] = ai_features
        
        # Enhanced invoice data
        if "result" in result:
            result["result"]["ai_enhanced"] = True
            result["result"]["smart_features"] = ai_features
        
        return result
    
    def _classify_deposit_tier(self, amount: float) -> str:
        """Classify deposit into tiers for different treatment"""
        if amount >= 5.0:
            return "whale"
        elif amount >= 1.0:
            return "high_roller"
        elif amount >= 0.1:
            return "regular"
        else:
            return "micro"
    
    def _estimate_confirmation_time(self, amount: float) -> str:
        """Estimate confirmation time based on amount"""
        if amount >= 1.0:
            return "1-3 minutes (priority processing)"
        elif amount >= 0.1:
            return "2-5 minutes (standard processing)"
        else:
            return "5-10 minutes (standard processing)"
    
    async def get_ai_invoice_status(self, invoice_id: str) -> Dict:
        """Get invoice status with AI enhancements"""
        try:
            headers = self._get_headers()
            params = {"invoice_ids": invoice_id}
            
            async with self.session.get(
                f"{self.api_url}/getInvoices",
                headers=headers,
                params=params
            ) as response:
                result = await response.json()
                
                if result.get("ok") and result.get("result"):
                    # Enhance status with AI insights
                    invoice = result["result"][0] if result["result"] else {}
                    result["ai_insights"] = await self._generate_status_insights(invoice)
                
                return result
                
        except Exception as e:
            logger.error(f"AI invoice status error: {e}")
            return {"ok": False, "error": str(e)}
    
    async def _generate_status_insights(self, invoice: Dict) -> Dict:
        """Generate AI insights about invoice status"""
        status = invoice.get("status", "unknown")
        created_at = invoice.get("created_at")
        
        insights = {
            "status_description": self._get_status_description(status),
            "next_action": self._get_next_action(status),
            "estimated_completion": self._estimate_completion_time(status, created_at)
        }
        
        return insights
    
    def _get_status_description(self, status: str) -> str:
        """Get human-friendly status description"""
        descriptions = {
            "active": "Waiting for payment - invoice is ready to receive funds",
            "paid": "Payment received and confirmed - processing deposit",
            "expired": "Invoice expired - please create a new deposit",
            "cancelled": "Invoice cancelled - no payment required"
        }
        return descriptions.get(status, f"Status: {status}")
    
    def _get_next_action(self, status: str) -> str:
        """Get recommended next action for user"""
        actions = {
            "active": "Send LTC to the provided address",
            "paid": "Your deposit is being processed - funds will appear shortly",
            "expired": "Create a new deposit invoice",
            "cancelled": "Start a new deposit if needed"
        }
        return actions.get(status, "Contact support if needed")
    
    def _estimate_completion_time(self, status: str, created_at: str) -> str:
        """Estimate when the invoice will be completed"""
        if status == "paid":
            return "Processing - usually completes within 1-2 minutes"
        elif status == "active":
            return "Waiting for payment - no time limit"
        else:
            return "N/A"

# Convenience functions for easy integration
async def create_ai_enhanced_invoice(
    amount: float, 
    user_id: int, 
    user_data: Dict = None,
    preferences: Dict = None
) -> Dict:
    """Create an AI-enhanced Litecoin deposit invoice"""
    async with CryptoPayAI() as crypto_ai:
        return await crypto_ai.create_ai_invoice(amount, user_id, user_data, preferences)

async def get_ai_invoice_status(invoice_id: str) -> Dict:
    """Get invoice status with AI insights"""
    async with CryptoPayAI() as crypto_ai:
        return await crypto_ai.get_ai_invoice_status(invoice_id)
