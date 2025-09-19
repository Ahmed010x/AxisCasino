#!/bin/bash
# Pre-deployment verification script for Telegram Casino Bot

echo "🔍 Checking bot deployment readiness..."

# Check Python syntax
echo "1. Checking Python syntax..."
python3 -m py_compile main_clean.py
if [ $? -eq 0 ]; then
    echo "✅ Python syntax OK"
else
    echo "❌ Python syntax errors found"
    exit 1
fi

# Check required files
echo "2. Checking required files..."
required_files=("main_clean.py" "requirements.txt" ".env.example")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
        exit 1
    fi
done

# Check environment variables
echo "3. Checking environment variables..."
if [ -f ".env" ]; then
    echo "✅ .env file exists"
    
    # Check critical env vars
    if grep -q "BOT_TOKEN=" .env; then
        echo "✅ BOT_TOKEN configured"
    else
        echo "⚠️  BOT_TOKEN not found in .env"
    fi
    
    if grep -q "OWNER_USER_ID=" .env; then
        echo "✅ OWNER_USER_ID configured"
    else
        echo "⚠️  OWNER_USER_ID not found in .env"
    fi
else
    echo "⚠️  .env file not found, will use environment variables"
fi

# Check dependencies
echo "4. Checking dependencies..."
if [ -f "requirements.txt" ]; then
    echo "✅ requirements.txt exists"
    echo "   Required packages:"
    cat requirements.txt | head -10
else
    echo "❌ requirements.txt missing"
    exit 1
fi

# Check database path
echo "5. Checking database setup..."
if [ -f "casino.db" ]; then
    echo "✅ casino.db exists"
else
    echo "ℹ️  casino.db will be created on first run"
fi

# Check main entry point
echo "6. Testing main entry point..."
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    import main_clean
    print('✅ main_clean.py can be imported')
except Exception as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ Import test passed"
else
    echo "❌ Import test failed"
    exit 1
fi

echo ""
echo "🎉 Bot deployment readiness check complete!"
echo ""
echo "📋 Deployment commands:"
echo "   1. Set environment variables (BOT_TOKEN, OWNER_USER_ID, etc.)"
echo "   2. Run: python3 main_clean.py"
echo "   3. For production: python3 deploy_bot.py"
echo ""
echo "🌐 Environment variables needed:"
echo "   - BOT_TOKEN (required)"
echo "   - OWNER_USER_ID (recommended)"
echo "   - ADMIN_USER_IDS (optional)"
echo "   - CRYPTOBOT_API_TOKEN (for deposits/withdrawals)"
echo "   - PORT (default: 8001)"
echo ""
