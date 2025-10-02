# ✅ Test Deposit Flow - CryptoBot Invoice

## How the Deposit System Works

### Flow Overview
1. User clicks **"💳 Deposit"** button
2. User selects **"🪙 Deposit Litecoin (LTC)"**
3. User types deposit amount in USD (e.g., `50`)
4. Bot creates CryptoBot invoice
5. User gets invoice with payment URL
6. User clicks **"💳 Pay with CryptoBot"** button
7. CryptoBot opens with payment interface
8. User completes payment
9. Bot receives webhook notification
10. Balance updates automatically

---

## Test Instructions

### Test 1: Demo Mode (No Real Money)

**Setup:**
```bash
# Set in .env
DEMO_MODE=true
```

**Steps:**
1. Start bot: `/start`
2. Click: **"💳 Deposit"**
3. Click: **"🪙 Deposit Litecoin (LTC)"**
4. Type: `10` (for $10 USD)
5. **Expected:** Instant balance credit of $10.00

**Result:** ✅ Demo deposit adds balance immediately

---

### Test 2: Real Mode with CryptoBot

**Setup:**
```bash
# Set in .env
DEMO_MODE=false
CRYPTOBOT_API_TOKEN=your_real_token_here
```

**Steps:**
1. Start bot: `/start`
2. Click: **"💳 Deposit"**
3. Click: **"🪙 Deposit Litecoin (LTC)"**
4. **Expected:** See current LTC/USD rate
5. Type: `5` (for $5 USD)
6. **Expected:** Receive invoice message with:
   - Amount in USD: $5.00
   - Amount in LTC: 0.xxxxx LTC
   - Rate: $xx.xxxx per LTC
   - Invoice ID
   - **"💳 Pay with CryptoBot"** button
   - **"🔄 Check Payment Status"** button

**Result:** ✅ Invoice created successfully

---

## Example Invoice Message

After entering deposit amount, you should see:

```
💰 CRYPTO PAY INVOICE READY 💰

📊 Payment Details:
• Amount: $5.00 USD
• Crypto: 0.05432100 LTC
• Rate: $92.0450 per LTC
• Invoice ID: INVOICE_123456

💳 Pay with CryptoBot:
Click the button below to open the secure payment interface.

⏰ Expires in 1 hour
🔔 You'll be notified instantly when payment is confirmed!

[💳 Pay with CryptoBot] [🔄 Check Payment Status] [🔙 Back to Deposit]
```

---

## Code Flow

### 1. deposit_crypto_callback()
```python
# Sets flag and shows amount input prompt
context.user_data['awaiting_deposit_amount'] = 'LTC'
```

### 2. handle_text_input_main()
```python
# Detects flag and routes to handler
if 'awaiting_deposit_amount' in context.user_data:
    await handle_deposit_amount_input(update, context)
```

### 3. handle_deposit_amount_input()
```python
# Validates amount (min $1, max $10,000)
# Calls process_deposit_payment()
```

### 4. process_deposit_payment()
```python
# Fetches live LTC rate
rate = await get_crypto_usd_rate('LTC')

# Calculates crypto amount
crypto_amount = amount_usd / rate

# Creates CryptoBot invoice
invoice_data = await create_crypto_invoice('LTC', crypto_amount, user_id)

# Sends invoice with payment button
payment_url = invoice['mini_app_invoice_url']
```

### 5. create_crypto_invoice()
```python
# Calls CryptoBot API
POST https://pay.crypt.bot/api/createInvoice
Headers: Crypto-Pay-API-Token: YOUR_TOKEN

Body:
{
    "asset": "LTC",
    "amount": "0.05432100",
    "description": "Casino deposit - $5.00 USD",
    "hidden_message": "123456789",  // user_id
    "expires_in": 3600,
    "allow_comments": false,
    "allow_anonymous": false
}

Response:
{
    "ok": true,
    "result": {
        "invoice_id": "INVOICE_123456",
        "mini_app_invoice_url": "https://t.me/CryptoBot/app?...",
        "web_app_invoice_url": "https://app.crypt.bot/...",
        "bot_invoice_url": "https://t.me/CryptoBot?start=..."
    }
}
```

---

## Verification Checklist

### Before Testing
- [ ] `BOT_TOKEN` set in `.env`
- [ ] `CRYPTOBOT_API_TOKEN` set (for real mode)
- [ ] Bot running without errors
- [ ] Database initialized (`casino.db` exists)

### During Test (Demo Mode)
- [ ] Deposit button shows deposit options
- [ ] LTC option prompts for amount
- [ ] Amount input validates min/max
- [ ] Balance updates immediately
- [ ] User can see new balance

### During Test (Real Mode)
- [ ] Rate fetched from CryptoBot API
- [ ] Invoice created successfully
- [ ] Payment URL is valid
- [ ] Invoice expires in 1 hour
- [ ] Check status button works

### After Payment (Real Mode)
- [ ] Webhook received (if configured)
- [ ] Balance updates automatically
- [ ] Transaction logged to database
- [ ] User notified of successful deposit

---

## Troubleshooting

### Issue: No invoice received
**Check:**
```bash
# View logs
tail -f casino_bot.log | grep "invoice"

# Test CryptoBot API token
curl -H "Crypto-Pay-API-Token: YOUR_TOKEN" \
  https://pay.crypt.bot/api/getMe
```

### Issue: Invalid amount error
**Possible causes:**
- Amount < $1.00 (minimum)
- Amount > $10,000.00 (maximum)
- Non-numeric input

### Issue: Rate fetch fails
**Check:**
```bash
# Verify API token
echo $CRYPTOBOT_API_TOKEN

# Test rate endpoint
curl -H "Crypto-Pay-API-Token: YOUR_TOKEN" \
  https://pay.crypt.bot/api/getExchangeRates
```

### Issue: Demo mode not working
**Check:**
```bash
# Verify env variable
echo $DEMO_MODE  # Should be "true"

# Check logs
grep "DEMO" casino_bot.log
```

---

## API Endpoints Used

### Get Exchange Rates
```
GET https://pay.crypt.bot/api/getExchangeRates
Returns: Current crypto/USD rates
```

### Create Invoice
```
POST https://pay.crypt.bot/api/createInvoice
Returns: Invoice with payment URLs
```

### Get Invoice Status
```
GET https://pay.crypt.bot/api/getInvoices?invoice_ids=INVOICE_ID
Returns: Invoice payment status
```

---

## Environment Variables

```bash
# Required for deposits
BOT_TOKEN=123456:ABC-DEF...
CRYPTOBOT_API_TOKEN=12345:AA...

# Optional
DEMO_MODE=false                    # true = instant credit, false = real payments
MIN_DEPOSIT_USD=1.00              # Minimum deposit
MAX_DEPOSIT_USD=10000.00          # Maximum deposit
```

---

## Expected Behavior

### ✅ Success Flow
1. User types valid amount
2. Bot fetches live rate
3. Bot creates invoice
4. Invoice message sent with buttons
5. User clicks "Pay with CryptoBot"
6. CryptoBot app opens
7. User completes payment
8. Balance updates (via webhook or manual check)

### ❌ Error Flows

**Invalid amount:**
```
User types: abc
Response: ❌ Invalid amount. Please enter a valid number (e.g., 10 or 25.50)
```

**Amount too small:**
```
User types: 0.50
Response: ❌ Minimum deposit is $1.00 USD.
```

**Amount too large:**
```
User types: 20000
Response: ❌ Maximum deposit is $10,000.00 USD per transaction.
```

**API error:**
```
Response: ❌ Error creating invoice: Request timeout - please try again
```

---

## Success Indicators

✅ **All working if you see:**
- LTC rate displays correctly
- Invoice ID generated
- Payment URL button appears
- URL opens in CryptoBot
- Payment interface loads

---

## Next Steps After Testing

1. **If demo mode works:** Set `DEMO_MODE=false`
2. **If real mode works:** Configure webhook for auto-balance updates
3. **If everything works:** Deploy to production!

---

*Test Date: October 2, 2025*  
*Status: System Complete & Ready* ✅
