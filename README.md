# 🎰 Axis Casino Bot - Telegram Casino Bot

A feature-rich Telegram casino bot with multiple games, crypto payments, referral system, and admin panel.

## 🎮 Features

### Games
- **🎰 Slots** - Classic slot machine with 10x-100x multipliers
- **🃏 Blackjack** - Standard blackjack with 3:2 payout
- **🎲 Dice** - High/Low/Lucky7 betting with up to 5x payout
- **🎯 Roulette** - European roulette (coming soon)

### Financial System
- **💰 Deposits** - LTC via CryptoBot API
- **🏦 Withdrawals** - LTC with 2% fee (min $1)
- **🎁 Weekly Bonus** - $5 every 7 days
- **👥 Referrals** - 20% commission on referral losses

### User Experience
- **Direct Commands** - `/slots`, `/blackjack`, `/dice`, `/games`
- **⚡ Commands Menu** - Preview all available commands
- **📊 Statistics** - Track games, wagered, won, streaks
- **🎨 Modern UI** - Clean inline keyboards and navigation

### Administration
- **Admin Panel** - User management, transactions, analytics
- **House Balance** - Real-time casino statistics
- **Logging** - Comprehensive error and event logging

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- (Optional) CryptoBot API token for real payments

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Ahmed010x/AxisCasino.git
cd AxisCasino
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env and set your BOT_TOKEN
```

4. **Run the bot**
```bash
python main.py
```

## 📝 Configuration

### Required Environment Variables
```bash
BOT_TOKEN=your_telegram_bot_token_here
CASINO_DB=casino.db
```

### Optional Environment Variables
```bash
# Payments
CRYPTOBOT_API_TOKEN=your_cryptobot_token
DEMO_MODE=false  # Set to true for testing

# Admin
OWNER_USER_ID=your_telegram_user_id
ADMIN_USER_IDS=comma,separated,user,ids

# Server
PORT=8000  # Auto-set by deployment platforms
```

## 🌐 Deployment

### Render
1. Connect your GitHub repository
2. Set environment variables in dashboard
3. Deploy automatically

### Railway/Heroku
Same process - set environment variables and deploy

### Local Testing
```bash
export BOT_TOKEN="your_bot_token"
python main.py
```

## 🎯 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Main user panel with balance & stats |
| `/games` | Show all available games |
| `/slots` | Play slots directly |
| `/blackjack` | Play blackjack directly |
| `/dice` | Play dice directly |
| `/roulette` | Roulette game menu |
| `/deposit` | Deposit funds via LTC |
| `/referral` | View referral program |
| `/help` | Help and support |

## 📊 Game Mechanics

### Slots
- 5 symbols with weighted randomness
- Payouts: 🍒(10x), 🍋(20x), 🍊(30x), 🔔(50x), 💎(100x)
- Two matching symbols: 0.5x consolation prize

### Blackjack
- Standard rules with auto-play
- Blackjack pays 3:2
- Dealer must hit on 16, stand on 17

### Dice
- Roll two dice (2-12 total)
- High (8-12): 2x payout
- Low (2-7): 2x payout
- Lucky 7: 5x payout

## 🔧 Project Structure

```
AxisCasino/
├── main.py              # Main bot application
├── casino.db            # SQLite database
├── requirements.txt     # Python dependencies
├── render.yaml          # Render deployment config
├── runtime.txt          # Python version
├── .env                 # Environment variables (local)
└── README.md            # This file
```

## 💾 Database Schema

The bot uses SQLite with comprehensive tables:
- `users` - User accounts and balances
- `game_sessions` - Game history and results
- `transactions` - Deposits and withdrawals
- `referrals` - Referral tracking
- `house_balance` - Casino financial data

## 🛠️ Development

### Testing
```bash
python -m pytest  # Run tests (if implemented)
python main.py    # Run bot locally
```

### Code Style
- PEP 8 compliant
- Async/await patterns throughout
- Type hints for function parameters
- Comprehensive error handling

## 📜 License

This project is licensed under the MIT License.

## 🤝 Support

For support, contact [@casino_support](https://t.me/casino_support)

## ⚠️ Disclaimer

This is a casino bot for entertainment purposes. Ensure compliance with local gambling laws and regulations before deployment.

---

**Made with ❤️ by GitHub Copilot**
