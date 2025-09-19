#!/bin/bash
"""
Docker/Container Startup Script for Telegram Casino Bot
Ensures proper initialization in containerized environments.
"""

set -e

echo "🐳 Container startup script for Telegram Casino Bot"
echo "=================================================="

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for dependencies
wait_for_deps() {
    echo "⏳ Waiting for dependencies to be ready..."
    
    # Wait for network to be available
    while ! ping -c 1 google.com >/dev/null 2>&1; do
        echo "⏳ Waiting for network connectivity..."
        sleep 5
    done
    echo "✅ Network connectivity OK"
}

# Function to setup environment
setup_environment() {
    echo "🔧 Setting up environment..."
    
    # Ensure proper Python version
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        echo "❌ Python not found!"
        exit 1
    fi
    
    echo "✅ Python command: $PYTHON_CMD"
    
    # Check if we're in the right directory
    if [ ! -f "main.py" ]; then
        echo "❌ main.py not found in current directory"
        echo "Current directory: $(pwd)"
        echo "Files: $(ls -la)"
        exit 1
    fi
    
    echo "✅ Bot files found"
}

# Function to install dependencies
install_deps() {
    echo "📦 Installing dependencies..."
    
    if [ -f "requirements.txt" ]; then
        $PYTHON_CMD -m pip install --no-cache-dir -r requirements.txt
        echo "✅ Dependencies installed"
    else
        echo "⚠️ requirements.txt not found, assuming dependencies are pre-installed"
    fi
}

# Function to check environment variables
check_env_vars() {
    echo "🔍 Checking environment variables..."
    
    required_vars=(
        "BOT_TOKEN"
        "OWNER_USER_ID"
    )
    
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo "❌ Missing required environment variables:"
        printf " - %s\n" "${missing_vars[@]}"
        exit 1
    fi
    
    echo "✅ Environment variables OK"
}

# Function to initialize database
init_database() {
    echo "🗃️ Initializing database..."
    
    # Run a simple Python script to initialize the database
    $PYTHON_CMD -c "
import asyncio
import sys
sys.path.insert(0, '.')
from main import init_database
asyncio.run(init_database())
print('✅ Database initialized')
"
}

# Function to start the bot
start_bot() {
    echo "🚀 Starting Telegram Casino Bot..."
    
    # Use production launcher for better reliability
    if [ -f "production_launcher.py" ]; then
        echo "Using production launcher..."
        exec $PYTHON_CMD production_launcher.py
    else
        echo "Using direct main.py..."
        exec $PYTHON_CMD main.py
    fi
}

# Main execution
main() {
    echo "🎰 Telegram Casino Bot - Container Startup"
    echo "Time: $(date)"
    echo "User: $(whoami)"
    echo "Working directory: $(pwd)"
    echo ""
    
    # Setup steps
    wait_for_deps
    setup_environment
    check_env_vars
    install_deps
    init_database
    
    echo ""
    echo "🎉 Setup complete! Starting bot..."
    echo "=================================="
    
    # Start the bot
    start_bot
}

# Handle signals gracefully
trap 'echo "🛑 Received termination signal, shutting down..."; exit 0' TERM INT

# Run main function
main "$@"
