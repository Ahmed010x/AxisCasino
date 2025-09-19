#!/bin/bash
"""
Fix HTTPXRequest Dependencies
Reinstall python-telegram-bot and related dependencies with correct versions
"""

echo "🔧 Fixing HTTPXRequest Dependencies"
echo "=================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Determine Python command
if command_exists python3; then
    PYTHON_CMD="python3"
elif command_exists python; then
    PYTHON_CMD="python"
else
    echo "❌ Python not found!"
    exit 1
fi

echo "🐍 Using Python: $PYTHON_CMD"

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
else
    echo "⚠️ Not in a virtual environment"
fi

echo ""
echo "🗑️ Removing problematic packages..."

# Uninstall potentially conflicting packages
$PYTHON_CMD -m pip uninstall -y python-telegram-bot httpx httpcore h2 anyio sniffio certifi

echo ""
echo "📦 Installing compatible versions..."

# Install specific compatible versions
$PYTHON_CMD -m pip install \
    python-telegram-bot==20.7 \
    httpx==0.24.1 \
    httpcore==0.17.3 \
    h2==4.1.0 \
    anyio==3.7.1 \
    sniffio==1.3.0 \
    certifi==2023.7.22

echo ""
echo "🔄 Installing all requirements..."

# Install all other requirements
$PYTHON_CMD -m pip install -r requirements.txt

echo ""
echo "🧪 Testing installation..."

# Test basic imports
$PYTHON_CMD -c "
import telegram
import httpx
import httpcore
print('✅ telegram:', telegram.__version__)
print('✅ httpx:', httpx.__version__)
print('✅ httpcore:', httpcore.__version__)
print('🎉 All imports successful!')
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Dependencies fixed successfully!"
    echo "🚀 You can now run the bot:"
    echo "   python3 main.py"
    echo "   python3 test_bot_httpx.py"
else
    echo ""
    echo "❌ Some imports failed. Please check the errors above."
    exit 1
fi
