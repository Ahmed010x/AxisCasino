# Deposit & Withdrawal System Guide

## ✅ System Status
The deposit and withdrawal system is **FULLY IMPLEMENTED** and ready for production use!

## 🚀 Features Implemented

### 💳 Deposit System
- **Multi-crypto support**: BTC, LTC, ETH, TON, USDT
- **Real-time rates**: Fetches live cryptocurrency rates from CryptoBot API
- **Instant processing**: Automatic balance updates upon payment confirmation
- **User-friendly interface**: Quick amount buttons and custom input
- **Secure invoices**: CryptoBot integration for secure payment processing

### 🏦 Withdrawal System  
- **Multi-crypto support**: Same assets as deposits
- **Smart fee calculation**: Configurable percentage fee with minimum threshold
- **Security limits**: Daily, per-transaction, and user-based limits
- **Address validation**: Regex validation for crypto addresses
- **Transaction logging**: Complete audit trail of all withdrawals
- **Status tracking**: Real-time withdrawal status updates

### 🔒 Security Features
- **Balance validation**: Prevents overdrafts and negative balances
- **Anti-fraud protection**: Rate limiting and withdrawal cooldowns
- **Address verification**: Format validation for all supported crypto addresses
- **Transaction atomicity**: Database transactions prevent partial operations
- **Demo mode**: Safe testing without real money

## 🛠️ Setup Instructions

### 1. Environment Configuration
Copy `env.example` to `.env` and configure:

```bash
cp env.example .env
```

### 2. CryptoBot API Setup
1. Go to https://pay.crypt.bot/
2. Create an account and get your API token
3. Add to your `.env` file:
```
CRYPTOBOT_API_TOKEN=your_token_here
CRYPTOBOT_WEBHOOK_SECRET=your_webhook_secret
```

### 3. Owner Configuration
Create `.env.owner` file:
```
OWNER_USER_ID=your_telegram_user_id
```

### 4. Database Setup
The database is automatically initialized on first run. Tables created:
- `users` - User accounts and balances
- `withdrawals` - Withdrawal transaction log
- `referrals` - Referral system tracking

## 🧪 Testing

### Demo Mode Testing
1. Set `DEMO_MODE=true` in your `.env`
2. Run the test script:
```bash
python test_deposit_withdrawal.py
```

### Live Testing
1. Set `DEMO_MODE=false`
2. Configure your CryptoBot API token
3. Start the bot and test with small amounts

## 📱 User Flow

### Deposit Flow
1. User clicks "💳 Deposit" button
2. Selects cryptocurrency (BTC, LTC, ETH, TON, USDT)
3. Enters amount in USD or uses quick buttons
4. System creates CryptoBot invoice with live rates
5. User pays via CryptoBot interface
6. Balance automatically updated upon payment

### Withdrawal Flow
1. User clicks "🏦 Withdraw" button
2. System checks minimum balance and limits
3. User selects cryptocurrency
4. Enters withdrawal amount (with fee calculation)
5. Provides wallet address (validated)
6. Confirms withdrawal details
7. System deducts balance and processes payout
8. Transaction logged with status tracking

## ⚙️ Configuration Options

### Withdrawal Limits
```env
MIN_WITHDRAWAL_USD=1.00          # Minimum withdrawal amount
MAX_WITHDRAWAL_USD=10000.00      # Maximum per transaction
MAX_WITHDRAWAL_USD_DAILY=10000.00 # Daily limit per user
WITHDRAWAL_FEE_PERCENT=2.0       # Fee percentage (2%)
WITHDRAWAL_COOLDOWN_SECONDS=300   # Cooldown between withdrawals
```

### Security Settings
```env
MAX_BET_PER_GAME=1000           # Anti-addiction limit
MAX_DAILY_LOSSES=5000           # Daily loss protection
ANTI_SPAM_WINDOW=10             # Rate limiting window
MAX_COMMANDS_PER_WINDOW=20      # Commands per window
```

## 🔧 Handler Registration
All handlers are properly registered:

### Callback Handlers
- `deposit` - Main deposit menu
- `deposit_BTC|LTC|ETH|TON|USDT` - Crypto selection
- `deposit_amount_*` - Amount selection
- `withdraw` - Main withdrawal menu  
- `withdraw_BTC|LTC|ETH|TON|USDT` - Crypto selection
- `withdraw_amount_*` - Amount selection
- `confirm_withdrawal` - Final confirmation

### Message Handlers
- Text input for custom amounts
- Address input for withdrawals
- Automatic state management

## 📊 Monitoring & Logging
- Complete transaction logging
- Error tracking with detailed messages
- Balance change auditing  
- Withdrawal status monitoring
- Real-time rate fetching logs

## 🚨 Production Checklist
- [ ] CryptoBot API token configured
- [ ] Withdrawal limits set appropriately
- [ ] Owner user ID configured
- [ ] Database backup strategy in place
- [ ] Demo mode disabled (`DEMO_MODE=false`)
- [ ] Support channel configured
- [ ] Error monitoring set up

## 💡 Advanced Features
- **Referral Integration**: Deposit triggers referral bonuses
- **Weekly Bonus**: Automatic bonus system
- **Multi-language Support**: Ready for internationalization
- **Mobile Optimized**: Works perfectly on mobile devices
- **Real-time Updates**: Live balance and rate updates

## 🛡️ Error Handling
- Graceful failure handling for API errors
- User-friendly error messages
- Automatic retries for rate fetching
- Transaction rollback on failures
- Comprehensive logging for debugging

## 📈 Scaling Considerations
- Database indexes for performance
- Connection pooling for high load
- Rate limiting to prevent abuse
- Caching for frequently accessed data
- Horizontal scaling support

---

**✅ The deposit and withdrawal system is production-ready!**

Start the bot with:
```bash
python main.py
```

Test the flows by interacting with the bot and using the deposit/withdrawal buttons.
