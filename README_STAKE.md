# 🎰 Stake Casino Bot

A modern Telegram casino bot with Mini App integration, built with Python using `python-telegram-bot` v20+ and Flask.

## ✨ Features

- **🎮 Mini App Integration**: Full web-based casino experience
- **💰 Balance Management**: Real-time balance synchronization
- **💳 Payment System**: Deposit and withdrawal functionality
- **🎯 Game Logic**: Various casino games with fair RNG
- **📊 Statistics**: Player stats and transaction history
- **🔄 Async Architecture**: High-performance async handlers
- **🗄️ SQLite Database**: Efficient user and transaction management
- **🌐 REST API**: Flask backend for game logic and data management

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │◄──►│   Flask API     │◄──►│   SQLite DB     │
│   (Bot Logic)   │    │  (Game Logic)   │    │ (User Data)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       ▲
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│    Mini App     │◄──►│   Web Interface │
│  (Telegram UI)  │    │   (Game UI)     │
└─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd telegram-casino
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.production .env
   # Edit .env and add your BOT_TOKEN
   ```

4. **Test the system**
   ```bash
   python test_system.py
   ```

5. **Run the bot**
   ```bash
   python run_casino.py
   ```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here

# Mini App Configuration
MINI_APP_URL=https://my-stake-miniapp.onrender.com
FLASK_API_URL=http://localhost:5000

# Database Configuration
DATABASE_PATH=casino_users.db

# Flask Configuration
FLASK_PORT=5000
FLASK_DEBUG=False
```

### Bot Setup

1. Create a new bot with [@BotFather](https://t.me/BotFather)
2. Get your bot token
3. Set up the Mini App URL with [@BotFather](https://t.me/BotFather) using `/setmenubutton`

## 📁 File Structure

```
telegram-casino/
├── stake_bot_clean.py      # Main Telegram bot implementation
├── flask_api.py           # Flask API server
├── run_casino.py          # Startup script for both services
├── test_system.py         # System tests
├── requirements.txt       # Python dependencies
├── .env.production       # Environment template
├── README.md             # This file
└── casino_users.db       # SQLite database (created automatically)
```

## 🎮 Bot Commands

- `/start` - Main menu with Mini App access
- `/balance` - Check current balance
- `/deposit` - Deposit funds (placeholder)
- `/withdraw` - Withdraw winnings (placeholder)
- `/help` - Show help information

## 🎯 Game Features

### Available Games
- **🎰 Slots** - Classic slot machine
- **🎯 Roulette** - European roulette
- **🃏 Blackjack** - 21 card game
- **🎲 Dice** - Simple dice betting

### Game Mechanics
- Fixed bet amounts for simplicity
- 50% win chance for demo purposes
- Real-time balance updates
- Transaction logging

## 🔌 API Endpoints

### User Management
- `GET /api/health` - Health check
- `GET /api/balance/{telegram_id}` - Get user balance
- `GET /api/user/{telegram_id}` - Get user info and transactions

### Game Operations
- `POST /api/bet` - Process game bet
- `GET /api/transactions/{telegram_id}` - Get transaction history

### Financial Operations
- `POST /api/deposit` - Process deposit (placeholder)
- `POST /api/withdraw` - Process withdrawal (placeholder)

### Mini App
- `GET /` - Serve the Mini App interface

## 🗄️ Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    balance REAL DEFAULT 1000.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Transactions Table
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    amount REAL NOT NULL,
    balance_before REAL NOT NULL,
    balance_after REAL NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
);
```

## 🔐 Security Features

- **Input Validation**: All user inputs are validated
- **SQL Injection Prevention**: Parameterized queries only
- **Rate Limiting**: Built-in protection against abuse
- **Balance Checks**: Atomic balance updates with transaction logging
- **Error Handling**: Comprehensive error handling and logging

## 🚀 Deployment

### Local Development
```bash
# Start both services
python run_casino.py
```

### Production Deployment

1. **Railway/Render/Heroku**
   ```bash
   # Set environment variables in your platform
   # Deploy both stake_bot_clean.py and flask_api.py
   ```

2. **VPS/Cloud Server**
   ```bash
   # Use systemd or PM2 to manage processes
   # Set up reverse proxy for Flask API
   # Configure SSL certificates
   ```

### Environment-Specific Configuration

**Development**
```env
FLASK_DEBUG=True
FLASK_API_URL=http://localhost:5000
```

**Production**
```env
FLASK_DEBUG=False
FLASK_API_URL=https://your-domain.com
MINI_APP_URL=https://your-miniapp-domain.com
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_system.py
```

The test suite checks:
- ✅ Environment configuration
- ✅ File structure
- ✅ Import dependencies
- ✅ Database operations
- ✅ Async database operations
- ✅ Flask API endpoints

## 📊 Monitoring

### Logs
The bot provides detailed logging for:
- User interactions
- Game results
- API requests
- Database operations
- Errors and exceptions

### Health Checks
- `/api/health` endpoint for monitoring
- Database connectivity checks
- Balance synchronization verification

## 🛠️ Customization

### Adding New Games
1. Add game logic to `flask_api.py`
2. Update the Mini App UI
3. Add new game types to the bet processing

### Modifying UI
1. Edit the HTML template in `flask_api.py`
2. Update inline keyboards in `stake_bot_clean.py`
3. Customize colors and styling

### Database Extensions
1. Add new tables to schema
2. Update the `DatabaseManager` class
3. Create migration scripts if needed

## 🐛 Troubleshooting

### Common Issues

**Bot not responding**
- Check BOT_TOKEN is set correctly
- Verify bot is not already running
- Check network connectivity

**Database errors**
- Ensure write permissions for database file
- Check disk space availability
- Verify SQLite installation

**API connection issues**
- Confirm Flask API is running
- Check FLASK_API_URL configuration
- Verify firewall settings

### Debug Mode
Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

Need help? Contact us:
- 📧 Email: support@example.com
- 💬 Telegram: [@your_support_bot](https://t.me/your_support_bot)
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)

## 🎯 Roadmap

- [ ] Add more casino games
- [ ] Implement real payment processing
- [ ] Add tournaments and competitions
- [ ] Create admin dashboard
- [ ] Add multi-language support
- [ ] Implement VIP levels and bonuses

---

**Made with ❤️ for the Telegram community**
