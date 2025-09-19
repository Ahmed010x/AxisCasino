#!/usr/bin/env python3
"""
Production Bot Launcher with Keep-Alive and Health Monitoring
Ensures the Telegram Casino Bot stays alive reliably in production.
"""

import os
import sys
import time
import signal
import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_launcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BotLauncher")

class ProductionBotManager:
    """Manage bot lifecycle in production with health monitoring"""
    
    def __init__(self):
        self.bot_process = None
        self.should_run = True
        self.restart_count = 0
        self.max_restarts = 20
        self.restart_cooldown = 30  # seconds
        self.health_check_interval = 60  # seconds
        self.last_health_check = datetime.now()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.should_run = False
        if self.bot_process:
            self.bot_process.terminate()
    
    def check_environment(self):
        """Check if environment is properly configured"""
        logger.info("🔍 Checking environment configuration...")
        
        required_files = ['main.py', '.env', 'requirements.txt']
        missing_files = []
        
        for file in required_files:
            if not Path(file).exists():
                missing_files.append(file)
        
        if missing_files:
            logger.error(f"❌ Missing required files: {missing_files}")
            return False
        
        # Check environment variables
        env_vars = [
            'BOT_TOKEN',
            'OWNER_USER_ID'
        ]
        
        missing_env = []
        for var in env_vars:
            if not os.getenv(var):
                missing_env.append(var)
        
        if missing_env:
            logger.error(f"❌ Missing environment variables: {missing_env}")
            return False
        
        logger.info("✅ Environment configuration OK")
        return True
    
    def install_dependencies(self):
        """Install required dependencies"""
        logger.info("📦 Installing dependencies...")
        
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info("✅ Dependencies installed successfully")
                return True
            else:
                logger.error(f"❌ Failed to install dependencies: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Dependency installation timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Error installing dependencies: {e}")
            return False
    
    def start_bot(self):
        """Start the bot process"""
        logger.info("🚀 Starting bot process...")
        
        try:
            self.bot_process = subprocess.Popen([
                sys.executable, 'main.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            logger.info(f"✅ Bot started with PID: {self.bot_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start bot: {e}")
            return False
    
    def check_bot_health(self):
        """Check if bot is healthy via HTTP health endpoint"""
        try:
            import requests
            
            # Try multiple ports in case of port conflicts
            ports = [8001, 8002, 8003]
            
            for port in ports:
                try:
                    response = requests.get(f'http://localhost:{port}/health', timeout=10)
                    if response.status_code == 200:
                        health_data = response.json()
                        logger.info(f"✅ Bot health check OK (port {port}): {health_data.get('status', 'unknown')}")
                        return True
                except requests.exceptions.RequestException:
                    continue
            
            logger.warning("⚠️ Health check failed on all ports")
            return False
            
        except ImportError:
            logger.warning("⚠️ Requests not available, skipping health check")
            return True  # Assume healthy if we can't check
        except Exception as e:
            logger.warning(f"⚠️ Health check error: {e}")
            return False
    
    def monitor_bot(self):
        """Monitor bot process and restart if needed"""
        while self.should_run:
            try:
                # Check if process is still running
                if not self.bot_process or self.bot_process.poll() is not None:
                    if self.bot_process:
                        returncode = self.bot_process.returncode
                        logger.warning(f"⚠️ Bot process died with exit code: {returncode}")
                        
                        # Log the last output
                        if self.bot_process.stderr:
                            stderr = self.bot_process.stderr.read()
                            if stderr:
                                logger.error(f"Bot stderr: {stderr}")
                    
                    if self.restart_count >= self.max_restarts:
                        logger.critical(f"❌ Maximum restart attempts ({self.max_restarts}) reached")
                        break
                    
                    logger.info(f"🔄 Restarting bot (attempt {self.restart_count + 1}/{self.max_restarts})")
                    time.sleep(self.restart_cooldown)
                    
                    if self.start_bot():
                        self.restart_count += 1
                    else:
                        logger.error("❌ Failed to restart bot")
                        break
                
                # Periodic health check
                now = datetime.now()
                if (now - self.last_health_check).total_seconds() >= self.health_check_interval:
                    if not self.check_bot_health():
                        logger.warning("⚠️ Health check failed, bot may be unresponsive")
                    self.last_health_check = now
                
                # Sleep before next check
                time.sleep(10)
                
            except KeyboardInterrupt:
                logger.info("🛑 Monitoring interrupted by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(5)
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up...")
        
        if self.bot_process:
            try:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=10)
                logger.info("✅ Bot process terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("⚠️ Bot process didn't terminate, forcing kill")
                self.bot_process.kill()
                self.bot_process.wait()
            except Exception as e:
                logger.error(f"❌ Error during cleanup: {e}")
    
    def run(self):
        """Main run method"""
        logger.info("🚀 Production Bot Manager Starting")
        logger.info(f"📍 Working directory: {os.getcwd()}")
        logger.info(f"🐍 Python executable: {sys.executable}")
        
        try:
            # Environment check
            if not self.check_environment():
                logger.critical("❌ Environment check failed")
                return False
            
            # Install dependencies
            if not self.install_dependencies():
                logger.critical("❌ Dependency installation failed")
                return False
            
            # Start bot
            if not self.start_bot():
                logger.critical("❌ Failed to start bot")
                return False
            
            # Monitor bot
            self.monitor_bot()
            
            return True
            
        except Exception as e:
            logger.critical(f"❌ Critical error in bot manager: {e}")
            return False
        finally:
            self.cleanup()

def main():
    """Main entry point"""
    print("🎰 Telegram Casino Bot - Production Launcher")
    print("=" * 50)
    
    manager = ProductionBotManager()
    success = manager.run()
    
    if success:
        print("✅ Bot manager completed successfully")
        return 0
    else:
        print("❌ Bot manager failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
