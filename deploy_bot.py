#!/usr/bin/env python3
"""
Casino Bot Deployment Script
Ensures all dependencies are installed and configurations are correct before deployment
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_python_version():
    """Check if Python version is compatible"""
    logger.info("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        logger.error(f"❌ Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    logger.info(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def check_environment_variables():
    """Check required environment variables"""
    logger.info("🔧 Checking environment variables...")
    
    # Load environment files
    try:
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv("env.litecoin")
        logger.info("✅ Environment files loaded")
    except Exception as e:
        logger.error(f"❌ Failed to load environment: {e}")
        return False
    
    # Required variables
    required_vars = [
        'CRYPTOBOT_API_TOKEN',
        'CRYPTOBOT_WEBHOOK_SECRET',
        'RENDER_EXTERNAL_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var) == 'your_bot_token_here':
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def check_dependencies():
    """Check if all required packages are installed"""
    logger.info("📦 Checking dependencies...")
    
    # Package mapping: import_name -> package_name
    required_packages = {
        'telegram': 'python-telegram-bot',
        'aiosqlite': 'aiosqlite', 
        'aiohttp': 'aiohttp',
        'flask': 'flask',
        'dotenv': 'python-dotenv',
        'nest_asyncio': 'nest-asyncio'
    }
    
    missing_packages = []
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
            logger.info(f"✅ {package_name} is installed")
        except ImportError:
            missing_packages.append(package_name)
            logger.error(f"❌ {package_name} is missing")
    
    if missing_packages:
        logger.error(f"❌ Missing packages: {missing_packages}")
        logger.info("📝 Install with: pip install " + " ".join(missing_packages))
        return False
    
    return True

def test_bot_import():
    """Test if the main bot script can be imported"""
    logger.info("🤖 Testing bot script import...")
    
    try:
        import main
        logger.info("✅ Bot script imports successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Bot script import failed: {e}")
        return False

def check_database():
    """Check database connectivity"""
    logger.info("🗄️ Checking database...")
    
    try:
        import sqlite3
        import asyncio
        from main import init_db, DB_PATH
        
        # Test database initialization
        asyncio.run(init_db())
        
        # Test database connection
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        
        logger.info(f"✅ Database initialized with {len(tables)} tables")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database check failed: {e}")
        return False

def test_webhook_server():
    """Test webhook server setup"""
    logger.info("🌐 Testing webhook server...")
    
    try:
        from main import setup_cryptobot_webhook_server
        import asyncio
        
        # Test webhook server creation
        app = asyncio.run(setup_cryptobot_webhook_server())
        logger.info("✅ Webhook server setup successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Webhook server test failed: {e}")
        return False

def create_systemd_service():
    """Create systemd service file for production deployment"""
    logger.info("🔧 Creating systemd service file...")
    
    current_dir = Path.cwd()
    python_path = sys.executable
    
    service_content = f"""[Unit]
Description=Casino Bot Telegram Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory={current_dir}
Environment=PATH={os.environ.get('PATH', '')}
ExecStart={python_path} main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
    
    service_file = current_dir / "casino-bot.service"
    try:
        with open(service_file, 'w') as f:
            f.write(service_content)
        logger.info(f"✅ Systemd service file created: {service_file}")
        
        logger.info("📝 To install the service:")
        logger.info(f"   sudo cp {service_file} /etc/systemd/system/")
        logger.info("   sudo systemctl daemon-reload")
        logger.info("   sudo systemctl enable casino-bot")
        logger.info("   sudo systemctl start casino-bot")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create service file: {e}")
        return False

def create_docker_files():
    """Create Docker files for containerized deployment"""
    logger.info("🐳 Creating Docker files...")
    
    # Dockerfile
    dockerfile_content = """FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create database directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application
CMD ["python", "main.py"]
"""
    
    # Docker Compose
    docker_compose_content = """version: '3.8'

services:
  casino-bot:
    build: .
    container_name: casino-bot
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - CRYPTOBOT_API_TOKEN=${CRYPTOBOT_API_TOKEN}
      - CRYPTOBOT_WEBHOOK_SECRET=${CRYPTOBOT_WEBHOOK_SECRET}
      - RENDER_EXTERNAL_URL=${RENDER_EXTERNAL_URL}
    volumes:
      - ./data:/app/data
      - ./env.litecoin:/app/env.litecoin:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
"""
    
    try:
        with open("Dockerfile", 'w') as f:
            f.write(dockerfile_content)
        
        with open("docker-compose.yml", 'w') as f:
            f.write(docker_compose_content)
            
        logger.info("✅ Docker files created")
        logger.info("📝 To deploy with Docker:")
        logger.info("   docker-compose up -d")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create Docker files: {e}")
        return False

def run_deployment_checks():
    """Run all deployment checks"""
    logger.info("🚀 Starting deployment checks...")
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Environment Variables", check_environment_variables),
        ("Bot Import", test_bot_import),
        ("Database", check_database),
        ("Webhook Server", test_webhook_server)
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        logger.info(f"\n--- {name} Check ---")
        if check_func():
            passed += 1
        else:
            logger.error(f"❌ {name} check failed")
    
    logger.info(f"\n🎯 Deployment Check Results: {passed}/{total} passed")
    
    if passed == total:
        logger.info("🎉 All checks passed! Bot is ready for deployment.")
        
        # Create deployment files
        create_systemd_service()
        create_docker_files()
        
        logger.info("\n🚀 Deployment Options:")
        logger.info("1. Direct: python main.py")
        logger.info("2. Systemd: Use the generated service file")
        logger.info("3. Docker: docker-compose up -d")
        logger.info("4. Cloud: Deploy to Render/Railway/Heroku")
        
        return True
    else:
        logger.error("❌ Some checks failed. Please fix the issues before deployment.")
        return False

if __name__ == "__main__":
    success = run_deployment_checks()
    sys.exit(0 if success else 1)
