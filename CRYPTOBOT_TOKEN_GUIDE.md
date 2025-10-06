# CryptoBot API Token Configuration Guide

## Issue
You're seeing this error in your bot logs:
```
CRYPTOBOT_API_TOKEN not configured - unable to fetch live rates
```

## Explanation

This error occurs when the bot tries to fetch cryptocurrency exchange rates but the CryptoBot API token is not configured. This is **not a critical error** and depends on your use case:

### ✅ **Safe to Ignore If:**
1. You're running in **DEMO_MODE** (testing/development)
2. You're not accepting real crypto payments
3. You haven't set up CryptoBot payment integration yet

### ⚠️ **Needs Attention If:**
1. You want to accept **real Litecoin (LTC) deposits**
2. You're running in **production mode** with live payments
3. You need real-time cryptocurrency exchange rates

---

## Solution Options

### Option 1: Enable Demo Mode (Quick Fix for Testing)

If you're just testing the bot, edit your `.env` file:

```bash
# Set demo mode to true
DEMO_MODE=true

# CryptoBot can be disabled
CRYPTOBOT_ENABLED=false
```

This will suppress the error and allow you to test the bot without real payments.

---

### Option 2: Get CryptoBot API Token (For Production)

If you want to accept real cryptocurrency payments:

#### Step 1: Create CryptoBot Account
1. Open Telegram and search for `@CryptoBot`
2. Start a conversation with the bot
3. Follow the setup instructions

#### Step 2: Get API Token
1. In CryptoBot, go to **"My Apps"** or send `/myapps`
2. Create a new app or select existing one
3. Get your **API Token**

#### Step 3: Configure Your .env File
Edit `/Users/ahmed/Telegram Axis/.env` and add:

```bash
# CryptoBot Pay Integration
CRYPTOBOT_API_TOKEN=your_actual_api_token_here
CRYPTOBOT_ENABLED=true
CRYPTOBOT_USD_ASSET=LTC
CRYPTOBOT_WEBHOOK_SECRET=your_webhook_secret_here

# Set demo mode to false for production
DEMO_MODE=false
```

#### Step 4: Restart Your Bot
```bash
# Stop the bot (Ctrl+C if running)
# Then restart it
python main.py
```

---

### Option 3: Use Fallback Rates (Temporary)

You can modify the code to use fallback exchange rates when the API is unavailable. This is useful during development:

**Edit main.py around line 463:**

```python
async def get_crypto_usd_rate(asset: str) -> float:
    """
    Fetch the real-time USD/crypto rate for the given asset from CryptoBot API.
    Returns the price of 1 unit of the asset in USD, or 0.0 on error.
    Includes retry logic for better reliability.
    """
    # Fallback rates for demo/development (updated periodically)
    FALLBACK_RATES = {
        'LTC': 65.0,   # Litecoin ~ $65
        'TON': 2.5,    # Toncoin ~ $2.50
        'SOL': 145.0,  # Solana ~ $145
        'BTC': 62000.0,# Bitcoin ~ $62,000
        'ETH': 2400.0, # Ethereum ~ $2,400
    }
    
    # Check if API token is configured
    if not CRYPTOBOT_API_TOKEN:
        logger.warning(f"CRYPTOBOT_API_TOKEN not configured - using fallback rate for {asset}")
        return FALLBACK_RATES.get(asset, 0.0)
    
    # ... rest of the function stays the same
```

**Note:** Fallback rates should only be used for testing. For production, always use real-time rates.

---

## Current Status Check

Run this command to check your current configuration:

```bash
cd "/Users/ahmed/Telegram Axis"
grep -E "DEMO_MODE|CRYPTOBOT" .env
```

Expected output will show your current settings.

---

## Recommended Setup for Different Scenarios

### 🧪 **Testing/Development:**
```bash
DEMO_MODE=true
CRYPTOBOT_ENABLED=false
```
Result: No API token needed, deposits simulated

### 🚀 **Production (Real Payments):**
```bash
DEMO_MODE=false
CRYPTOBOT_ENABLED=true
CRYPTOBOT_API_TOKEN=<your_token>
```
Result: Real crypto payments accepted

### 🏗️ **Staging (Testing with Real API):**
```bash
DEMO_MODE=false
CRYPTOBOT_ENABLED=true
CRYPTOBOT_API_TOKEN=<test_token>
```
Result: Real API, but test environment

---

## Verify Configuration

After making changes, verify the bot loads correctly:

```bash
cd "/Users/ahmed/Telegram Axis"
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

print('Configuration Status:')
print(f'DEMO_MODE: {os.getenv(\"DEMO_MODE\", \"not set\")}')
print(f'CRYPTOBOT_ENABLED: {os.getenv(\"CRYPTOBOT_ENABLED\", \"not set\")}')
print(f'CRYPTOBOT_API_TOKEN: {\"SET\" if os.getenv(\"CRYPTOBOT_API_TOKEN\") else \"NOT SET\"}')
"
```

---

## Impact on Bot Features

| Feature | Without Token | With Token |
|---------|--------------|------------|
| Bot Startup | ✅ Works | ✅ Works |
| Demo Deposits | ✅ Works | ✅ Works |
| Real Crypto Deposits | ❌ Won't work | ✅ Works |
| Games | ✅ Works | ✅ Works |
| Withdrawals | ⚠️ Simulated only | ✅ Real |
| Balance Display | ✅ Works | ✅ Works |

---

## Quick Fix Commands

### Enable Demo Mode (Suppress Error):
```bash
cd "/Users/ahmed/Telegram Axis"
# Backup current .env
cp .env .env.backup

# Update DEMO_MODE
sed -i '' 's/DEMO_MODE=false/DEMO_MODE=true/' .env

# Restart bot
# (Stop with Ctrl+C, then run: python main.py)
```

### Check Logs After Restart:
```bash
tail -f casino_bot.log | grep -i "cryptobot\|demo\|mode"
```

---

## Next Steps

1. **Decide your use case**: Testing or Production?
2. **Configure accordingly**: Demo mode or real API token
3. **Restart the bot**: Apply the changes
4. **Monitor logs**: Ensure error is resolved

---

## Support

If you need help getting a CryptoBot API token:
- Visit: https://t.me/CryptoBot
- Documentation: Check CryptoBot's official docs
- Support: Message @CryptoBot in Telegram

---

**Last Updated**: 2025-10-06
**Status**: Configuration guide for CryptoBot API token issue
