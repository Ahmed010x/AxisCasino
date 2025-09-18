#!/bin/bash
# Production deployment script for Telegram Casino Bot
# Supports multiple platforms: Render, Railway, Heroku, VPS

set -e

echo "🚀 Deploying Telegram Casino Bot - Production Server"
echo "=================================================="

# Check Python version
python_version=$(python3 --version 2>&1)
echo "🐍 Python version: $python_version"

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Check environment configuration
echo "🔧 Checking environment configuration..."

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN is not set!"
    exit 1
fi

if [ -z "$ADMIN_USER_IDS" ]; then
    echo "⚠️ ADMIN_USER_IDS is not set - admin features will be disabled"
fi

if [ -z "$PORT" ]; then
    echo "🔧 PORT not set, using default 8080"
    export PORT=8080
fi

if [ -z "$THREADS" ]; then
    echo "🔧 THREADS not set, using default 4"
    export THREADS=4
fi

# Database setup
echo "🗄️ Setting up database..."
python3 -c "
import asyncio
import sys
sys.path.append('.')
from bot.database.db import create_tables
asyncio.run(create_tables())
print('✅ Database tables created/verified')
"

# Verify bot configuration
echo "🤖 Verifying bot configuration..."
python3 -c "
import sys
sys.path.append('.')
try:
    import main
    print('✅ Bot configuration verified')
except Exception as e:
    print(f'❌ Bot configuration error: {e}')
    sys.exit(1)
"

echo "✅ Deployment preparation complete!"
echo ""
echo "🌐 Production Server Features:"
echo "   • Waitress WSGI server with fallback"
echo "   • Multi-threaded with connection limits"
echo "   • Health check endpoints: /, /health, /status, /ping, /metrics"
echo "   • Proxy-friendly with header validation"
echo "   • Automatic cleanup and memory management"
echo ""
echo "🚀 Starting bot with production server..."
echo "   Server will run on 0.0.0.0:$PORT with $THREADS threads"
echo ""

# Start the bot
exec python3 main.py
