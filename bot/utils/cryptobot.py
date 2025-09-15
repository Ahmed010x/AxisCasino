# utils/cryptobot.py
"""
CryptoBot API integration for Litecoin payments (deposit/withdraw)
"""
import os
import aiohttp

CRYPTOBOT_API_TOKEN = os.environ.get("CRYPTOBOT_API_TOKEN")
CRYPTOBOT_LITECOIN_ASSET = os.environ.get("CRYPTOBOT_LITECOIN_ASSET", "LTCTRC20")
CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"

async def create_litecoin_invoice(amount: float, user_id: int, description: str = "Casino Deposit", address: bool = True) -> dict:
    """Create a Litecoin payment invoice via CryptoBot API, optionally requesting a unique address."""
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_API_TOKEN}
    data = {
        "asset": CRYPTOBOT_LITECOIN_ASSET,
        "amount": str(amount),
        "description": description,
        "hidden_message": str(user_id),
        "paid_btn_name": "openChannel",
        "paid_btn_url": "https://t.me/your_channel_here"
    }
    if address:
        data["address"] = True
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{CRYPTOBOT_API_URL}/createInvoice", headers=headers, data=data) as resp:
            return await resp.json()

async def get_invoice_status(invoice_id: str) -> dict:
    """Check the status of a CryptoBot invoice."""
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_API_TOKEN}
    params = {"invoice_ids": invoice_id}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{CRYPTOBOT_API_URL}/getInvoices", headers=headers, params=params) as resp:
            return await resp.json()

async def send_litecoin(to_address: str, amount: float, comment: str = "Casino Withdraw") -> dict:
    """Send Litecoin to a user via CryptoBot API (withdrawal)."""
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_API_TOKEN}
    data = {
        "asset": CRYPTOBOT_LITECOIN_ASSET,
        "amount": str(amount),
        "to": to_address,
        "comment": comment
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{CRYPTOBOT_API_URL}/transfer", headers=headers, data=data) as resp:
            return await resp.json()
