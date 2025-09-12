#!/bin/bash
# Quick Deployment Script for Render
# This script helps verify your deployment is ready

echo "🎰 Casino Bot - Render Deployment Checker 🎰"
echo "=============================================="

# Check required files
echo "📁 Checking required files..."
files=("main.py" "requirements.txt" "render.yaml")
for file in "${files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file found"
    else
        echo "❌ $file missing"
        exit 1
    fi
done

# Check Python syntax
echo -e "\n🐍 Checking Python syntax..."
if python3 -m py_compile main.py; then
    echo "✅ main.py syntax valid"
else
    echo "❌ main.py has syntax errors"
    exit 1
fi

# Check environment file
echo -e "\n🔧 Checking environment configuration..."
if [[ -f ".env" ]]; then
    echo "✅ .env file found"
    if grep -q "BOT_TOKEN=" .env; then
        echo "✅ BOT_TOKEN configured in .env"
    else
        echo "⚠️  BOT_TOKEN not found in .env"
    fi
else
    echo "⚠️  .env file not found (copy from env.example)"
fi

# Check for WebApp integration
echo -e "\n🚀 Checking Mini App integration..."
if grep -q "WebApp" main.py; then
    echo "✅ WebApp integration found"
else
    echo "❌ WebApp integration missing"
    exit 1
fi

if grep -q "mini_app_centre" main.py; then
    echo "✅ Mini App Centre found"
else
    echo "❌ Mini App Centre missing"
    exit 1
fi

echo -e "\n🎯 Deployment Readiness Check Complete!"
echo "==========================================="
echo ""
echo "🚀 Ready for Render Deployment!"
echo ""
echo "📋 Next Steps:"
echo "1. Push code to GitHub repository"
echo "2. Connect repository to Render"
echo "3. Set environment variables in Render dashboard:"
echo "   - BOT_TOKEN (from @BotFather)"
echo "   - WEBAPP_URL (your casino WebApp URL)"
echo "   - WEBAPP_SECRET_KEY (your secret key)"
echo "   - RENDER_EXTERNAL_URL (your Render app URL)"
echo "4. Deploy as Web Service"
echo "5. Test with /start command"
echo ""
echo "🎰 Your Casino Bot with Mini App is ready! 🎰"
