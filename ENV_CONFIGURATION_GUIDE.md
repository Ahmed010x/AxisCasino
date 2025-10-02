# Environment Configuration Guide

This guide explains all environment variables used in the Telegram Casino Bot and how to configure them for different deployment scenarios.

## Quick Start

1. Copy `env.example` to `.env`
2. Set required variables: `BOT_TOKEN`, `WEBAPP_SECRET_KEY`, `ADMIN_USER_IDS`
3. Update `WEBAPP_URL` and `RENDER_EXTERNAL_URL` for production
4. Set `DEMO_MODE=false` for production

## Configuration Sections

### 1. Core Bot Configuration

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `BOT_TOKEN` | ✅ | Telegram bot token from @BotFather | `1234567890:ABCDEF...` |
| `DEMO_MODE` | ✅ | Enable demo mode for testing | `false` |
| `ENVIRONMENT` | ✅ | Environment identifier | `production` |

### 2. Database Configuration

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `CASINO_DB` | ✅ | SQLite database file path | `casino.db` |
| `DB_BACKUP_ENABLED` | ❌ | Enable automatic backups | `true` |
| `DB_BACKUP_INTERVAL` | ❌ | Backup interval in seconds | `3600` |
| `DB_MAX_BACKUPS` | ❌ | Maximum backup files to keep | `24` |

### 3. Web Application

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `WEBAPP_ENABLED` | ✅ | Enable web interface | `true` |
| `WEBAPP_SECRET_KEY` | ✅ | Flask session secret | Generate random string |
| `PORT` | ✅ | Server port | `10000` |
| `WEBAPP_URL` | ✅ | External webapp URL | `https://app.onrender.com` |

### 4. Game Configuration

#### Game Limits
All monetary values are in USD.

| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_BET_PER_GAME` | Maximum single bet | `1000` |
| `MAX_DAILY_LOSSES` | Maximum daily losses per user | `5000` |
| `MIN_*_BET` | Minimum bet per game | Varies by game |
| `MAX_*_BET` | Maximum bet per game | Varies by game |

#### House Edge
Configure fair house edge percentages:

| Variable | Game | Default % |
|----------|------|-----------|
| `HOUSE_EDGE_SLOTS` | Slot machines | `3.5` |
| `HOUSE_EDGE_BLACKJACK` | Blackjack | `1.5` |
| `HOUSE_EDGE_ROULETTE` | Roulette | `2.7` |
| `HOUSE_EDGE_DICE` | Dice | `2.0` |
| `HOUSE_EDGE_POKER` | Poker | `3.0` |
| `HOUSE_EDGE_COINFLIP` | Coin flip | `2.0` |

### 5. Payment & Economy System

#### Withdrawals
| Variable | Description | Default |
|----------|-------------|---------|
| `MIN_WITHDRAWAL_USD` | Minimum withdrawal | `10.00` |
| `MAX_WITHDRAWAL_USD` | Maximum single withdrawal | `5000.00` |
| `MAX_WITHDRAWAL_USD_DAILY` | Daily withdrawal limit | `5000.00` |
| `WITHDRAWAL_FEE_PERCENT` | Withdrawal fee percentage | `0.02` |

#### CryptoBot Integration
Optional integration with @CryptoBot for real crypto payments:

| Variable | Required | Description |
|----------|----------|-------------|
| `CRYPTOBOT_API_TOKEN` | ❌ | API token from @CryptoBot |
| `CRYPTOBOT_USD_ASSET` | ❌ | Cryptocurrency asset |
| `CRYPTOBOT_WEBHOOK_SECRET` | ❌ | Webhook verification secret |

#### Bonus System
| Variable | Description | Default |
|----------|-------------|---------|
| `WEEKLY_BONUS_AMOUNT` | Weekly bonus amount | `50.0` |
| `DAILY_BONUS_AMOUNT` | Daily bonus amount | `10.0` |
| `WELCOME_BONUS_AMOUNT` | New user bonus | `25.0` |

#### Referral System
| Variable | Description | Default |
|----------|-------------|---------|
| `REFERRAL_COMMISSION_PERCENT` | Commission percentage | `0.20` (20%) |
| `REFERRAL_BONUS_REFEREE` | Referee welcome bonus | `5.0` |
| `REFERRAL_LINK_BASE` | Base URL for referral links | Bot username required |

#### VIP System
| Variable | Description | Default |
|----------|-------------|---------|
| `VIP_SILVER_REQUIRED` | Silver tier requirement | `1000` |
| `VIP_GOLD_REQUIRED` | Gold tier requirement | `5000` |
| `VIP_DIAMOND_REQUIRED` | Diamond tier requirement | `10000` |

### 6. User Management & Security

#### Admin Configuration
| Variable | Required | Description |
|----------|----------|-------------|
| `ADMIN_USER_IDS` | ✅ | Comma-separated admin user IDs |
| `OWNER_USER_ID` | ✅ | Super admin user ID |
| `SUPPORT_CHANNEL` | ❌ | Support channel username |

#### Rate Limiting
| Variable | Description | Default |
|----------|-------------|---------|
| `ANTI_SPAM_WINDOW` | Command spam window (seconds) | `10` |
| `MAX_COMMANDS_PER_WINDOW` | Max commands per window | `20` |
| `RATE_LIMIT_REQUESTS` | General rate limit | `100` |
| `RATE_LIMIT_WINDOW` | Rate limit window (seconds) | `60` |

### 7. Deployment & Operations

#### Server Configuration
| Variable | Required | Description |
|----------|----------|-------------|
| `RENDER_EXTERNAL_URL` | ✅ | External URL for deployment |
| `HEARTBEAT_INTERVAL` | ❌ | Health check interval |
| `WEBHOOK_ENABLED` | ❌ | Enable webhook mode |

#### Logging
| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_TO_FILE` | Enable file logging | `true` |
| `LOG_FILE_PATH` | Log file path | `logs/casino_bot.log` |

## Deployment Scenarios

### Development Environment
```bash
# Copy example file
cp env.example .env

# Edit required values
BOT_TOKEN=your_test_bot_token
DEMO_MODE=true
DEBUG_MODE=true
WEBAPP_SECRET_KEY=dev-secret-key
```

### Production Environment
```bash
# Set production values
DEMO_MODE=false
DEBUG_MODE=false
ENVIRONMENT=production
WEBAPP_URL=https://your-app.onrender.com
RENDER_EXTERNAL_URL=https://your-app.onrender.com

# Use secure random secret
WEBAPP_SECRET_KEY=generate_random_64_char_string

# Set real admin IDs
ADMIN_USER_IDS=123456789,987654321
OWNER_USER_ID=123456789
```

### Security Considerations

1. **Never commit .env files** to version control
2. **Use strong random secrets** for production
3. **Set appropriate rate limits** based on expected usage
4. **Enable security features** like session timeouts
5. **Monitor logs** for unusual activity
6. **Use HTTPS** for all external URLs

## Feature Flags

Use feature flags to enable/disable functionality:

| Flag | Description |
|------|-------------|
| `GAMES_ENABLED` | Enable all games |
| `PAYMENTS_ENABLED` | Enable payment processing |
| `REFERRALS_ENABLED` | Enable referral system |
| `VIP_SYSTEM_ENABLED` | Enable VIP tiers |
| `WITHDRAWALS_ENABLED` | Enable withdrawal functionality |

## Troubleshooting

### Common Issues

1. **Bot not responding**: Check `BOT_TOKEN` is valid
2. **Web app not loading**: Verify `WEBAPP_URL` and `PORT`
3. **Database errors**: Check `CASINO_DB` file permissions
4. **Payment issues**: Verify CryptoBot configuration

### Validation Script

Create a validation script to check configuration:

```python
import os
from dotenv import load_dotenv

load_dotenv()

required_vars = ['BOT_TOKEN', 'WEBAPP_SECRET_KEY', 'ADMIN_USER_IDS']
for var in required_vars:
    if not os.getenv(var):
        print(f"ERROR: {var} is not set")
    else:
        print(f"✓ {var} is configured")
```

## Updates and Migrations

When updating the bot, check for new environment variables in:
- `env.example` file
- This documentation
- Release notes

Always backup your `.env` file before updates.
