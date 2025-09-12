# 🚀 Casino Bot Deployment Guide for Render

## 📋 Pre-Deployment Checklist

### ✅ Required Environment Variables
Set these in your Render dashboard:

1. **BOT_TOKEN** - Your Telegram bot token from @BotFather
2. **WEBAPP_URL** - URL of your casino web app (e.g., https://your-casino.vercel.app)
3. **WEBAPP_SECRET_KEY** - Secret key for WebApp authentication
4. **RENDER_EXTERNAL_URL** - Your Render app URL (for keep-alive)

### 🔧 Optional Configuration
- **WEBAPP_ENABLED** - true/false (default: true)
- **PORT** - Port number (default: 10000)
- **HEARTBEAT_INTERVAL** - Keep-alive interval in seconds (default: 300)

## 🎯 Deployment Steps

### 1. Prepare Your Repository
```bash
# Ensure all files are in place
ls -la
# Should show: main.py, requirements.txt, render.yaml, README.md
```

### 2. Deploy to Render
1. Go to [render.com](https://render.com)
2. Connect your GitHub repository
3. Choose "Web Service"
4. Configure:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: Free (or paid for production)

### 3. Set Environment Variables
In Render dashboard → Environment:
```
BOT_TOKEN=1234567890:ABCDEF...
WEBAPP_URL=https://your-casino-webapp.vercel.app
WEBAPP_SECRET_KEY=your-secret-key-here
RENDER_EXTERNAL_URL=https://your-app.onrender.com
```

### 4. Deploy
- Click "Create Web Service"
- Wait for build and deployment (3-5 minutes)
- Check logs for "🎰 Casino Bot is running!"

## 🎮 Mini App Integration

### WebApp Features
- **🚀 PLAY IN WEBAPP** button in Mini App Centre
- Direct `/webapp` command access
- Menu button integration (if enabled)
- Real-time balance sync

### WebApp URL Parameters
Your WebApp will receive:
- `user_id` - Telegram user ID
- `balance` - Current user balance
- `timestamp` - Request timestamp

### Example WebApp URL
```
https://your-casino.vercel.app?user_id=123456789&balance=1000
```

## 🔍 Health Monitoring

### Health Check Endpoints
- `GET /health` - Health status
- `GET /` - Root endpoint (also health check)

### Response Format
```json
{
  "status": "healthy",
  "timestamp": "2025-09-12T10:30:00",
  "service": "telegram-casino-bot",
  "version": "2.0.1"
}
```

### Keep-Alive System
- Automatic heartbeat every 5 minutes
- Prevents Render free tier sleeping
- Self-pinging to maintain uptime

## 🎰 Bot Commands

### User Commands
- `/start` - Main casino panel
- `/app` - Mini App Centre
- `/webapp` - Direct WebApp access
- `/casino` - Direct WebApp access
- `/help` - Help and information

### Mini App Features
1. **🔥 STAKE ORIGINALS** - Premium games
2. **🎰 CLASSIC CASINO** - Traditional games (Slots, Blackjack, etc.)
3. **🎮 INLINE GAMES** - Quick mini-games (Coin flip, etc.)
4. **🏆 TOURNAMENTS** - Competitive events
5. **💎 VIP GAMES** - High-stakes exclusive games

## 🛠️ Troubleshooting

### Common Issues

#### Bot Not Responding
1. Check BOT_TOKEN is correct
2. Verify logs in Render dashboard
3. Ensure bot is not stopped by @BotFather

#### WebApp Not Working
1. Verify WEBAPP_URL is accessible
2. Check WEBAPP_ENABLED=true
3. Test WebApp independently

#### Database Issues
1. SQLite file is created automatically
2. Check file permissions
3. Verify disk space

#### Keep-Alive Issues
1. Ensure RENDER_EXTERNAL_URL is set
2. Check heartbeat logs
3. Verify health endpoint responds

### Log Messages to Watch For
```
✅ Database initialized
✅ WebApp URL: https://...
✅ WebApp Enabled: True
✅ Health check server started on port 10000
🎰 Casino Bot is running!
✓ Heartbeat ping successful
```

## 📊 Performance Optimization

### Free Tier Considerations
- Bot sleeps after 15 minutes of inactivity
- Keep-alive system maintains uptime
- Health checks ensure responsiveness

### Database Optimization
- Automatic indexing on user balance
- Session logging for analytics
- Efficient query patterns

### Memory Management
- Lightweight async operations
- Minimal memory footprint
- Automatic cleanup on shutdown

## 🔐 Security Features

### Bot Security
- Input validation on all commands
- Balance verification before transactions
- Secure callback data handling

### WebApp Security
- Secret key authentication
- User ID validation
- Balance verification

### Database Security
- Parameterized queries (SQL injection prevention)
- Transaction logging
- User data protection

## 📈 Monitoring and Analytics

### Built-in Metrics
- User registration tracking
- Game session logging
- Balance change tracking
- Error logging

### Health Monitoring
- Service uptime tracking
- Heartbeat monitoring
- Database connectivity

## 🎉 Success Indicators

### Deployment Success
- [ ] Bot responds to `/start`
- [ ] Mini App Centre loads
- [ ] WebApp button works
- [ ] Games function correctly
- [ ] Database saves user data
- [ ] Health endpoint responds
- [ ] Logs show no errors

### Production Ready
- [ ] Keep-alive system active
- [ ] WebApp integration working
- [ ] All games playable
- [ ] Balance system functional
- [ ] Error handling robust
- [ ] Monitoring in place

---

## 🚀 Quick Start Commands

After deployment, test with:
```
/start - Should show casino panel
/webapp - Should offer WebApp button
/app - Should show Mini App Centre
```

## 📞 Support

If you encounter issues:
1. Check Render logs
2. Verify environment variables
3. Test health endpoint
4. Review bot permissions with @BotFather

---

🎰 **Your Casino Bot is now ready for production!** 🎰
