# 🎰 Telegram Casino Bot - Deployment Guide

A professional Telegram casino bot with WebApp integration, built with Python and aiohttp.

## ✅ Pre-Deployment Checklist

- [x] Bot code completed (`main.py`)
- [x] Dependencies specified (`requirements.txt`)
- [x] Python runtime specified (`runtime.txt`)
- [x] Render configuration ready (`render.yaml`)
- [x] WebApp files included (`casino_webapp_new.html`, `balance_sync.js`)
- [ ] **BOT_TOKEN obtained from @BotFather**

## 🚀 Quick Deploy to Render

### 1. Get Bot Token
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the bot token (format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### 2. Deploy to Render
1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Use the following settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python3 main.py`
   - **Environment**: `python`

### 3. Set Environment Variables
In Render Dashboard > Environment:
```
BOT_TOKEN=your_actual_bot_token_here
WEBAPP_ENABLED=true
WEBAPP_SECRET_KEY=your_random_secret_key
PORT=10000
```

### 4. Advanced Configuration (Optional)
```
VIP_SILVER_REQUIRED=1000
VIP_GOLD_REQUIRED=5000  
VIP_DIAMOND_REQUIRED=10000
MAX_BET_PER_GAME=1000
MAX_DAILY_LOSSES=5000
```

## 🔧 Local Development

### Setup
```bash
# Clone repository
git clone <your-repo-url>
cd telegram-casino-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp env.example .env
# Edit .env with your BOT_TOKEN
```

### Run Locally
```bash
# Set bot token
export BOT_TOKEN="your_bot_token_here"

# Start bot
python3 main.py
```

### Test Deployment Readiness
```bash
python3 deploy_check_fixed.py
```

## 🎮 Features

### ✅ Implemented
- 🤖 **Telegram Bot** - Full bot with commands and callbacks
- 🎰 **Casino WebApp** - Modern web interface with games
- 💰 **Balance System** - User accounts, chips, transactions
- 🎁 **Bonus System** - Daily bonuses, referrals, achievements
- 📊 **Statistics** - User stats, leaderboards, rankings
- 🎲 **Animated Games** - Dice, basketball, soccer with Telegram emojis
- 💾 **Database** - SQLite with aiosqlite for async operations
- 🌐 **Web Server** - aiohttp server for WebApp and health checks
- 🔄 **Balance Sync** - Real-time balance synchronization across games
- 🛡️ **Security** - Input validation, rate limiting, error handling

### 🚧 Planned (Coming Soon)
- 💳 **Crypto Payments** - Real cryptocurrency integration
- 🎮 **More Games** - Slots, Blackjack, Roulette, Poker implementations  
- 🏆 **Tournaments** - Competitive gaming events
- 🔗 **Multi-platform** - Discord, web portal integration

## 📁 Project Structure

```
telegram-casino-bot/
├── main.py                    # Main bot application
├── requirements.txt           # Python dependencies
├── runtime.txt               # Python version for Render
├── render.yaml               # Render deployment config
├── casino_webapp_new.html    # Main WebApp interface
├── balance_sync.js           # Real-time balance sync
├── game_*.html              # Individual game pages
├── env.example              # Environment variables template
├── test_bot_startup.py      # Startup testing script
├── deploy_check_fixed.py    # Deployment readiness check
└── README_DEPLOY.md         # This file
```

## 🎯 Bot Commands

- `/start` - Main casino panel
- `/app` - Mini App Centre
- `/webapp` - Open casino WebApp
- `/casino` - Open casino WebApp (alias)
- `/help` - Help and information
- `/dice` - Play dice game
- `/basketball` - Play basketball game
- `/soccer` - Play soccer game

## 🎰 WebApp Features

- 🎮 **Game Hub** - Access all casino games
- 📱 **Mobile Optimized** - Perfect for Telegram mobile app
- 🎨 **Modern UI** - Dark theme with glassmorphism effects
- ⚡ **Real-time Updates** - Balance syncs instantly
- 🔄 **Cross-tab Sync** - Balance updates across all open tabs

## 🛠️ Technical Details

### Architecture
- **Backend**: Python 3.11+ with aiohttp
- **Database**: SQLite with aiosqlite (async)
- **Frontend**: HTML5 + CSS3 + Vanilla JavaScript
- **Bot Framework**: python-telegram-bot v20.3
- **Hosting**: Render (or any Python hosting platform)

### Database Schema
- **users**: id, username, balance, games_played, total_wagered, total_won
- **game_sessions**: session_id, user_id, game_type, bet_amount, win_amount, result

### API Endpoints
- `GET /health` - Health check
- `GET /casino` - Main WebApp
- `GET /api/balance` - Get user balance
- `POST /api/update_balance` - Update user balance

## 🐛 Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check BOT_TOKEN is set correctly
   - Verify bot is not already running elsewhere
   - Check Render logs for errors

2. **WebApp not loading**
   - Ensure WEBAPP_ENABLED=true
   - Check casino_webapp_new.html exists
   - Verify HTTPS URL for production

3. **Database errors**
   - Check write permissions for casino.db
   - Verify aiosqlite installation
   - Check database initialization logs

### Logs and Debugging
```bash
# View Render logs
# Go to Render Dashboard > Your Service > Logs

# Local debugging
python3 main.py  # Will show detailed logs
```

## 🎉 Success Indicators

When deployment is successful, you should see:
```
🎰 Mini App Integration Status:
✅ WebApp URL: https://your-app.onrender.com/casino
✅ WebApp Enabled: True
✅ Secret Key: Set
✅ Server Port: 10000
🤖 Starting Telegram Casino Bot v2.0...
✅ Production database initialized at casino.db
✅ Health check server started on port 10000
🚀 Starting bot polling...
✅ Bot is running!
```

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Run `python3 deploy_check_fixed.py` to verify setup
3. Check Render logs for specific errors
4. Ensure all environment variables are set correctly

---

**Ready to deploy?** 🚀 Just set your BOT_TOKEN and deploy to Render!
