# 🎰 Telegram Casino Bot - Keep-Alive System Documentation

## Overview

The Telegram Casino Bot now includes a comprehensive **keep-alive system** designed to ensure maximum uptime and reliability in production environments. This system includes health monitoring, automatic restarts, Flask-based health endpoints, and robust error handling.

## 🚀 Key Features

### 1. **Flask Keep-Alive Server**
- **HTTP Health Endpoints**: `/health`, `/ping`, `/restart`, `/`
- **Production WSGI Server**: Uses Waitress for production-grade performance
- **Port Fallback**: Automatically tries alternative ports if main port is busy
- **Background Thread**: Runs independently of the bot without blocking

### 2. **Health Monitoring System**
- **Real-time Metrics**: Tracks updates, errors, uptime, and response times
- **Health Status API**: Exposes metrics via HTTP endpoints
- **Automatic Unhealthy Detection**: Flags bot as unhealthy if no updates for 5+ minutes
- **Error Rate Tracking**: Monitors and reports error rates

### 3. **Auto-Restart Mechanism**
- **Exponential Backoff**: Intelligent restart delays to prevent rapid restart loops
- **Maximum Attempts**: Configurable restart limits to prevent infinite loops
- **Signal Handling**: Graceful shutdown on SIGTERM/SIGINT
- **Error Classification**: Different handling for network vs critical errors

### 4. **Production Tools**
- **Production Launcher**: Comprehensive bot manager with dependency checking
- **Health Check Script**: External monitoring integration
- **System Monitor**: Real-time dashboard for bot and system metrics
- **Docker Support**: Container-ready startup scripts

## 📁 File Structure

```
/Users/ahmed/Telegram Axis/
├── main.py                    # Enhanced bot with keep-alive system
├── production_launcher.py     # Production bot manager
├── health_check.py           # External health check script
├── monitor_dashboard.py      # Real-time monitoring dashboard
├── docker-startup.sh         # Container startup script
├── casino-bot.service        # Systemd service file
└── test_keep_alive_system.py # Test suite for keep-alive components
```

## 🔧 Configuration

### Environment Variables

Required variables in `.env` file:
```bash
BOT_TOKEN=your_telegram_bot_token
OWNER_USER_ID=your_telegram_user_id
PORT=8001  # Default port for keep-alive server
```

Optional variables:
```bash
DEMO_MODE=false
ADMIN_USER_IDS=123456789,987654321
CRYPTOBOT_API_TOKEN=your_cryptobot_token
RENDER_EXTERNAL_URL=https://your-domain.com
HEARTBEAT_INTERVAL=300
```

### Health Monitor Settings

The health monitor can be configured by modifying the `BotHealthMonitor` class:
```python
class BotHealthMonitor:
    def __init__(self):
        self.unhealthy_threshold = 300  # 5 minutes
        # ... other settings
```

### Auto-Restart Settings

Auto-restart behavior can be configured in the `BotAutoRestart` class:
```python
class BotAutoRestart:
    def __init__(self):
        self.max_restarts = 10      # Maximum restart attempts
        self.restart_delay = 5      # Initial delay in seconds
        self.max_delay = 300        # Maximum delay (5 minutes)
        # ... other settings
```

## 🚀 Usage

### Development Mode
```bash
# Direct bot execution
python3 main.py

# With monitoring
python3 monitor_dashboard.py
```

### Production Mode
```bash
# Using production launcher (recommended)
python3 production_launcher.py

# Or direct execution
python3 main.py
```

### Docker/Container
```bash
# Use the container startup script
./docker-startup.sh
```

### Systemd Service (Linux)
```bash
# Copy service file
sudo cp casino-bot.service /etc/systemd/system/

# Enable and start
sudo systemctl enable casino-bot
sudo systemctl start casino-bot

# Check status
sudo systemctl status casino-bot
```

## 📊 Health Endpoints

### GET `/health`
Returns detailed health information:
```json
{
  "status": "healthy",
  "uptime_seconds": 3600.5,
  "last_update_ago": 1.2,
  "total_updates": 1500,
  "total_errors": 3,
  "error_rate": 0.002,
  "timestamp": "2025-09-19T16:07:27.123456",
  "bot_version": "2.0.1"
}
```

**Status Codes:**
- `200`: Bot is healthy
- `503`: Bot is unhealthy

### GET `/ping`
Simple ping endpoint:
```json
{
  "pong": true,
  "timestamp": "2025-09-19T16:07:27.123456"
}
```

### GET `/`
Basic bot information:
```json
{
  "status": "online",
  "bot": "Telegram Casino Bot",
  "version": "2.0.1",
  "timestamp": "2025-09-19T16:07:27.123456"
}
```

### GET `/restart`
Emergency restart endpoint:
```json
{
  "message": "Restart signal received",
  "timestamp": "2025-09-19T16:07:27.123456"
}
```

## 🔍 Monitoring

### External Health Checks
```bash
# Simple health check
python3 health_check.py

# Specific port
python3 health_check.py --port 8002
```

### Real-time Dashboard
```bash
# Start monitoring dashboard
python3 monitor_dashboard.py
```

The dashboard shows:
- **Bot Health**: Status, uptime, updates, errors
- **System Resources**: CPU, memory, disk usage
- **Process Information**: Bot processes and resource usage
- **Health Trend**: Historical health status

### External Monitoring Integration

**Prometheus/Grafana**:
```bash
# Health check for Prometheus
curl -s http://localhost:8001/health | jq '.error_rate'
```

**Uptime Robot/Similar**:
- Monitor URL: `http://your-domain.com:8001/ping`
- Expected response: `{"pong": true}`

**Custom Scripts**:
```bash
#!/bin/bash
# Simple monitoring script
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health)
if [ "$response" = "200" ]; then
    echo "Bot is healthy"
else
    echo "Bot is unhealthy (HTTP $response)"
    # Send alert, restart bot, etc.
fi
```

## 🛠️ Troubleshooting

### Common Issues

1. **Port Already in Use**
   - The system automatically tries alternative ports (8002, 8003)
   - Check which process is using the port: `lsof -i :8001`

2. **Bot Not Responding to Health Checks**
   - Check if bot process is running: `ps aux | grep main.py`
   - Review logs: `tail -f casino_bot.log`
   - Restart manually: `python3 main.py`

3. **Too Many Restarts**
   - Check the restart count and delay in logs
   - Review error patterns to identify root cause
   - Adjust restart limits in `BotAutoRestart` class

4. **Database Issues**
   - Check database file permissions: `ls -la casino.db`
   - Verify database initialization: `python3 -c "from main import init_database; import asyncio; asyncio.run(init_database())"`

### Log Files

- **Bot Logs**: `casino_bot.log`
- **Launcher Logs**: `bot_launcher.log`
- **System Logs**: `/var/log/syslog` (systemd)

### Debug Mode

Enable debug logging by modifying the logging level:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    # ... rest of configuration
)
```

## 🔒 Security Considerations

1. **Health Endpoints**: Consider restricting access to health endpoints in production
2. **Restart Endpoint**: The `/restart` endpoint should be protected or disabled in production
3. **Environment Variables**: Keep sensitive tokens secure and never commit them to version control
4. **Process Permissions**: Run with minimal required permissions
5. **Resource Limits**: Set appropriate memory and CPU limits

## 📈 Performance Optimization

1. **Resource Monitoring**: Use the monitoring dashboard to track resource usage
2. **Error Rate**: Keep error rates below 1% for optimal performance
3. **Response Time**: Health endpoint should respond within 1 second
4. **Memory Usage**: Monitor for memory leaks over time
5. **Restart Frequency**: Healthy bots should require minimal restarts

## 🚀 Deployment Recommendations

### Development
- Use direct `python3 main.py` execution
- Enable debug logging
- Monitor with dashboard

### Staging
- Use `production_launcher.py`
- Test auto-restart functionality
- Verify health endpoints

### Production
- Use systemd service or Docker
- Set up external monitoring
- Configure log rotation
- Implement alerting

## 📝 Testing

Run the comprehensive test suite:
```bash
python3 test_keep_alive_system.py
```

Tests include:
- ✅ Health monitor functionality
- ✅ Auto-restart system
- ✅ Flask server creation
- ✅ Database initialization
- ✅ Import verification

## 🎯 Success Metrics

A healthy bot deployment should show:
- **Uptime**: >99.9%
- **Response Time**: <1 second for health checks
- **Error Rate**: <1%
- **Restart Frequency**: <1 restart per day
- **Memory Usage**: Stable over time
- **CPU Usage**: <10% average

## 📞 Support

For issues with the keep-alive system:
1. Check the troubleshooting section above
2. Review log files for error patterns
3. Run the test suite to verify system integrity
4. Monitor the health endpoints for real-time status

---

**Version**: 2.0.1  
**Last Updated**: September 19, 2025  
**Author**: Casino Bot Development Team
