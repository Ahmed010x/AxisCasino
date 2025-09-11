# Environment Variables Configuration

This document describes all the environment variables used by the Telegram Casino Bot for configuration.

## Required Variables

### Bot Configuration
- `BOT_TOKEN` - Your Telegram bot token from @BotFather (Required)
- `CASINO_DB` - Path to the SQLite database file (Default: "casino.db")

### Render Hosting Configuration
- `PORT=8000` - HTTP server port for health checks (automatically set by Render)
- `RENDER_EXTERNAL_URL` - Your Render app URL for keep-alive heartbeat (e.g., https://your-app.onrender.com)
- `HEARTBEAT_INTERVAL=300` - Keep-alive ping interval in seconds (5 minutes default)

## Game Configuration Variables

### Daily Bonus Settings
- `DAILY_BONUS_MIN=40` - Minimum daily bonus amount in chips
- `DAILY_BONUS_MAX=60` - Maximum daily bonus amount in chips

### Minimum Bet Requirements
- `MIN_SLOTS_BET=10` - Minimum chips required to play slots
- `MIN_BLACKJACK_BET=20` - Minimum chips required to play blackjack

### Standard Bet Amounts
- `BET_AMOUNT_SMALL=10` - Small bet amount for various games
- `BET_AMOUNT_MEDIUM=25` - Medium bet amount for various games  
- `BET_AMOUNT_LARGE=50` - Large bet amount for various games
- `BET_AMOUNT_XLARGE=100` - Extra large bet amount for various games

### VIP System Configuration
- `VIP_SILVER_REQUIRED=1000` - Chips needed for Silver VIP status
- `VIP_GOLD_REQUIRED=5000` - Chips needed for Gold VIP status
- `VIP_DIAMOND_REQUIRED=10000` - Chips needed for Diamond VIP status

### Referral System
- `REFERRAL_BONUS=100` - Chips earned per successful referral
- `FRIEND_SIGNUP_BONUS=50` - Chips new friends get when joining
- `FIRST_GAME_BONUS=25` - Bonus chips when friends play their first game

### Slots Game Configuration

#### Symbol Weights (probability)
- `SLOTS_CHERRY_WEIGHT=50` - Weight for cherry symbol (higher = more common)
- `SLOTS_LEMON_WEIGHT=30` - Weight for lemon symbol
- `SLOTS_ORANGE_WEIGHT=10` - Weight for orange symbol
- `SLOTS_BELL_WEIGHT=7` - Weight for bell symbol
- `SLOTS_DIAMOND_WEIGHT=3` - Weight for diamond symbol (lowest = rarest)

#### Payout Multipliers
- `SLOTS_CHERRY_PAYOUT=10` - Multiplier for cherry jackpot
- `SLOTS_LEMON_PAYOUT=20` - Multiplier for lemon jackpot
- `SLOTS_ORANGE_PAYOUT=30` - Multiplier for orange jackpot
- `SLOTS_BELL_PAYOUT=50` - Multiplier for bell jackpot
- `SLOTS_DIAMOND_PAYOUT=100` - Multiplier for diamond jackpot

### Other Game Settings
- `HILO_PAYOUT_MULTIPLIER=1.8` - Payout multiplier for Hi-Lo card game
- `PLINKO_PAYOUT_HIGH=130` - High payout multiplier for Plinko
- `PLINKO_PAYOUT_GOOD=43` - Good payout multiplier for Plinko
- `PLINKO_PAYOUT_MEDIUM=10` - Medium payout multiplier for Plinko
- `PLINKO_PAYOUT_LOW=5` - Low payout multiplier for Plinko

## Example .env File

```env
# Bot Configuration (Required)
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
CASINO_DB=casino.db

# Render Hosting Configuration
PORT=8000
RENDER_EXTERNAL_URL=https://your-app-name.onrender.com
HEARTBEAT_INTERVAL=300

# Game Configuration
DAILY_BONUS_MIN=40
DAILY_BONUS_MAX=60
MIN_SLOTS_BET=10
MIN_BLACKJACK_BET=20

# Bet Amounts
BET_AMOUNT_SMALL=10
BET_AMOUNT_MEDIUM=25
BET_AMOUNT_LARGE=50
BET_AMOUNT_XLARGE=100

# VIP Level Requirements
VIP_SILVER_REQUIRED=1000
VIP_GOLD_REQUIRED=5000
VIP_DIAMOND_REQUIRED=10000

# Referral System
REFERRAL_BONUS=100
FRIEND_SIGNUP_BONUS=50
FIRST_GAME_BONUS=25

# Slots Payout Multipliers
SLOTS_CHERRY_PAYOUT=10
SLOTS_LEMON_PAYOUT=20
SLOTS_ORANGE_PAYOUT=30
SLOTS_BELL_PAYOUT=50
SLOTS_DIAMOND_PAYOUT=100

# Slots Symbol Weights
SLOTS_CHERRY_WEIGHT=50
SLOTS_LEMON_WEIGHT=30
SLOTS_ORANGE_WEIGHT=10
SLOTS_BELL_WEIGHT=7
SLOTS_DIAMOND_WEIGHT=3

# Hi-Lo Game
HILO_PAYOUT_MULTIPLIER=1.8

# Plinko Payouts
PLINKO_PAYOUT_HIGH=130
PLINKO_PAYOUT_GOOD=43
PLINKO_PAYOUT_MEDIUM=10
PLINKO_PAYOUT_LOW=5
```

## Usage Notes

1. **Backup your .env file** - It contains sensitive configuration data
2. **Never commit .env to version control** - Add it to .gitignore
3. **Restart the bot** after changing environment variables
4. **Test changes** in a development environment first
5. **All values are case-sensitive**

## Security Considerations

- Keep your `BOT_TOKEN` secret and never share it
- Use environment variables for all sensitive configuration
- Regularly rotate bot tokens if compromised
- Monitor usage and set appropriate rate limits

## Customization Tips

- **Higher symbol weights** = more common (lower payouts recommended)
- **Lower symbol weights** = rarer (higher payouts recommended) 
- **Adjust VIP thresholds** based on your game economy
- **Balance daily bonuses** to maintain engagement without inflation
- **Test payout changes** with small user groups first
