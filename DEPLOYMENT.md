# Render.com Deployment Guide

## 🚀 Deploy Telegram Casino Bot to Render

This guide will help you deploy your Telegram Casino Bot to Render.com with keep-alive functionality.

## Prerequisites

1. **Telegram Bot Token**: Get from [@BotFather](https://t.me/BotFather)
2. **Render Account**: Sign up at [render.com](https://render.com)
3. **GitHub Repository**: Your code should be in a GitHub repo

## Step 1: Prepare Your Repository

Ensure your repository has these files:
- `main.py` - The main bot file
- `requirements.txt` - Python dependencies
- `.env.example` - Example environment variables (don't include your real `.env`)

## Step 2: Create Render Service

1. **Connect GitHub**: Link your GitHub account to Render
2. **Create Web Service**: Choose "Web Service" from dashboard
3. **Select Repository**: Choose your bot repository
4. **Configure Service**:
   - **Name**: `telegram-casino-bot` (or your preferred name)
   - **Language**: `Python 3`
   - **Branch**: `main` (or your default branch)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`

## Step 3: Environment Variables

In Render dashboard, add these environment variables:

### Required Variables
```
BOT_TOKEN=your_actual_telegram_bot_token_here
RENDER_EXTERNAL_URL=https://your-app-name.onrender.com
```

### Optional Variables (use defaults if not set)
```
PORT=8000
CASINO_DB=casino.db
HEARTBEAT_INTERVAL=300
DAILY_BONUS_MIN=40
DAILY_BONUS_MAX=60
MIN_SLOTS_BET=10
MIN_BLACKJACK_BET=20
VIP_SILVER_REQUIRED=1000
VIP_GOLD_REQUIRED=5000
VIP_DIAMOND_REQUIRED=10000
```

**Important**: Replace `your-app-name` in `RENDER_EXTERNAL_URL` with your actual Render service name.

## Step 4: Deploy

1. Click **"Create Web Service"**
2. Wait for the build to complete (usually 2-3 minutes)
3. Check the logs for successful startup
4. Your bot should now be running!

## Step 5: Verify Deployment

### Check Health Endpoints
- `https://your-app-name.onrender.com/health` - Health check
- `https://your-app-name.onrender.com/status` - Service status

### Test Bot
1. Start a conversation with your bot on Telegram
2. Send `/start` command
3. Try some games to ensure everything works

## Keep-Alive Features ❤️

The bot includes several features to prevent Render's free tier from sleeping:

### 🔄 Automatic Heartbeat
- Self-pings every 5 minutes (configurable)
- Keeps the service active 24/7
- Prevents cold starts

### 🏥 Health Check Server  
- HTTP server on port 8000
- Multiple health endpoints
- Service status monitoring

### 🛡️ Graceful Shutdown
- Handles SIGTERM signals properly
- Cleans up resources on shutdown
- Safe database operations

## Render Free Tier Limitations

### ⚠️ Important Notes:
- **Sleep Policy**: Free services sleep after 15 minutes of inactivity
- **Monthly Hours**: 750 hours/month limit (750 hours = ~25 days)
- **Keep-Alive**: Our heartbeat system keeps it awake during peak hours
- **Persistence**: Database persists between deployments

### 💡 Optimization Tips:
- The heartbeat runs every 5 minutes to minimize resource usage
- Health checks are lightweight
- Database operations are optimized for quick responses
- Consider upgrading to paid tier for 24/7 availability

## Troubleshooting

### Common Issues

**1. Build Fails**
```bash
# Check requirements.txt format
# Ensure all packages have version numbers
# Review build logs in Render dashboard
```

**2. Bot Doesn't Respond**
```bash
# Verify BOT_TOKEN is correct
# Check environment variables are set
# Review application logs
```

**3. Database Issues**
```bash
# SQLite database is created automatically
# Check file permissions
# Verify CASINO_DB path
```

### Debug Commands

**Check Service Status**:
```bash
curl https://your-app-name.onrender.com/status
```

**Health Check**:
```bash  
curl https://your-app-name.onrender.com/health
```

**View Logs**:
- Use Render dashboard logs
- Check both build and runtime logs

## Monitoring

### Log Messages to Watch For:
- `✅ All dependencies available`
- `Starting Telegram Casino Bot...`
- `✓ Heartbeat ping successful`
- `Health check server started on port 8000`

### Performance Metrics:
- Response time to Telegram commands
- Database query performance
- Memory usage (check Render dashboard)
- Heartbeat success rate

## Scaling Considerations

### Current Setup:
- **Single Instance**: Optimized for one instance
- **SQLite Database**: Simple but not multi-instance friendly
- **Memory Usage**: ~50-100MB typical

### For High Traffic:
- Consider PostgreSQL for multi-instance deployment
- Implement session management
- Add caching layer (Redis)
- Monitor resource usage

## Security Best Practices

### Environment Variables:
- Never commit `.env` to GitHub
- Use Render's environment variable system
- Rotate bot token periodically
- Monitor access logs

### Database Security:
- Regular backups (manual for SQLite)
- Validate all user inputs
- Rate limiting implemented
- SQL injection protection

## Support

### Getting Help:
1. **Check Logs**: Render dashboard → Your Service → Logs
2. **Health Endpoints**: Use status endpoints for debugging
3. **GitHub Issues**: Report bugs in your repository
4. **Render Docs**: [docs.render.com](https://docs.render.com)

### Useful Resources:
- [Render Python Deployment Guide](https://render.com/docs/deploy-python)
- [Telegram Bot API Docs](https://core.telegram.org/bots/api)
- [aiosqlite Documentation](https://aiosqlite.omnilib.dev/)

---

🎰 **Happy Gaming!** Your Telegram Casino Bot is now running 24/7 on Render! 🎰
