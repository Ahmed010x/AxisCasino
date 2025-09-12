#!/bin/bash

# Telegram Casino Bot Setup Script

echo "🎰 Setting up Telegram Casino Bot..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file and add your BOT_TOKEN"
    echo "   Get your token from @BotFather on Telegram"
    echo ""
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your BOT_TOKEN"
echo "2. Run: python main.py"
echo ""
echo "🎲 Have fun with your casino bot!"
