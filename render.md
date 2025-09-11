# Render.com deployment configuration
# This file helps with deployment to Render hosting

# Build Command (if needed)
# pip install -r requirements.txt

# Start Command
# python main.py

# Environment Variables to set in Render dashboard:
# BOT_TOKEN=your_telegram_bot_token_here
# RENDER_EXTERNAL_URL=https://your-app-name.onrender.com
# PORT=8000 (automatically set by Render)
# HEARTBEAT_INTERVAL=300

# Render Service Configuration:
# - Service Type: Web Service
# - Language: Python 3
# - Build Command: pip install -r requirements.txt  
# - Start Command: python main.py
# - Instance Type: Starter (Free tier)
# - Auto-Deploy: Yes (recommended)

# Health Check Endpoints:
# GET / - Returns health status
# GET /health - Returns detailed health information  
# GET /status - Returns service status and configuration

# Keep-Alive Features:
# - Automatic heartbeat system prevents service sleeping
# - Self-pinging every 5 minutes (configurable)
# - Graceful shutdown handling
# - HTTP health check server on port 8000

# Database:
# - Uses SQLite (casino.db) 
# - Automatically created on first run
# - Persists between deployments (use Render disk storage)

# Scaling:
# - Optimized for single instance (SQLite limitation)
# - Can handle moderate traffic loads
# - Consider PostgreSQL for high-traffic scenarios
