#!/usr/bin/env python3
"""
Final Bot Verification Script
Test that the bot can start and the keep-alive system is working properly.
"""

import sys
import os
import time
import subprocess
import requests
import threading
import signal
from datetime import datetime

class BotVerification:
    """Verify bot startup and keep-alive functionality"""
    
    def __init__(self):
        self.bot_process = None
        self.test_passed = False
        self.health_port = None
        
    def start_bot_process(self):
        """Start the bot in background"""
        print("🚀 Starting bot process...")
        try:
            self.bot_process = subprocess.Popen([
                sys.executable, 'main.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            print(f"✅ Bot started with PID: {self.bot_process.pid}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")
            return False
    
    def wait_for_health_endpoint(self, timeout=30):
        """Wait for health endpoint to become available"""
        print("⏳ Waiting for health endpoint to become available...")
        
        # Load environment to get correct port
        from dotenv import load_dotenv
        load_dotenv()
        port = int(os.environ.get("PORT", "8001"))
        ports_to_try = [port, 8001, 8002, 8003]
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            for test_port in ports_to_try:
                try:
                    response = requests.get(f'http://localhost:{test_port}/health', timeout=5)
                    if response.status_code in [200, 503]:  # Either healthy or unhealthy is OK
                        print(f"✅ Health endpoint is responding on port {test_port}")
                        self.health_port = test_port  # Store the discovered port
                        return True
                except requests.exceptions.ConnectionError:
                    pass  # Expected while bot is starting
                except Exception as e:
                    pass  # Try next port
            
            time.sleep(2)
        
        print("❌ Health endpoint did not become available within timeout")
        return False
    
    def test_health_endpoints(self):
        """Test all health endpoints"""
        print("🧪 Testing health endpoints...")
        
        if not self.health_port:
            print("❌ No health port discovered")
            return False
        
        endpoints = {
            '/': 'Basic info endpoint',
            '/health': 'Health status endpoint', 
            '/ping': 'Ping endpoint'
        }
        
        success_count = 0
        for endpoint, description in endpoints.items():
            try:
                response = requests.get(f'http://localhost:{self.health_port}{endpoint}', timeout=10)
                if response.status_code in [200, 503]:
                    print(f"✅ {endpoint} - {description}: OK")
                    success_count += 1
                else:
                    print(f"❌ {endpoint} - {description}: HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ {endpoint} - {description}: {e}")
        
        return success_count == len(endpoints)
    
    def test_health_data(self):
        """Test health data structure"""
        print("🧪 Testing health data structure...")
        
        if not self.health_port:
            print("❌ No health port discovered")
            return False
        
        try:
            response = requests.get(f'http://localhost:{self.health_port}/health', timeout=10)
            data = response.json()
            
            required_fields = ['status', 'uptime_seconds', 'total_updates', 'total_errors']
            missing_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"❌ Missing health data fields: {missing_fields}")
                return False
            else:
                print("✅ Health data structure is correct")
                print(f"   Status: {data.get('status')}")
                print(f"   Uptime: {data.get('uptime_seconds'):.1f}s")
                print(f"   Updates: {data.get('total_updates')}")
                print(f"   Errors: {data.get('total_errors')}")
                return True
                
        except Exception as e:
            print(f"❌ Health data test failed: {e}")
            return False
    
    def stop_bot_process(self):
        """Stop the bot process gracefully"""
        if self.bot_process:
            print("🛑 Stopping bot process...")
            try:
                # Send SIGTERM for graceful shutdown
                self.bot_process.terminate()
                
                # Wait up to 10 seconds for graceful shutdown
                try:
                    self.bot_process.wait(timeout=10)
                    print("✅ Bot stopped gracefully")
                except subprocess.TimeoutExpired:
                    print("⚠️ Bot didn't stop gracefully, forcing kill")
                    self.bot_process.kill()
                    self.bot_process.wait()
                    
            except Exception as e:
                print(f"❌ Error stopping bot: {e}")
    
    def run_verification(self):
        """Run complete verification"""
        print("🎰 Telegram Casino Bot - Final Verification")
        print("=" * 50)
        print(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        try:
            # Step 1: Start bot
            if not self.start_bot_process():
                return False
            
            # Step 2: Wait for health endpoint
            if not self.wait_for_health_endpoint():
                return False
            
            # Step 3: Test endpoints
            if not self.test_health_endpoints():
                return False
            
            # Step 4: Test health data
            if not self.test_health_data():
                return False
            
            print()
            print("🎉 All verification tests passed!")
            print("✅ Bot can start successfully")
            print("✅ Keep-alive server is working")
            print("✅ Health endpoints are functional")
            print("✅ Health monitoring is operational")
            
            self.test_passed = True
            return True
            
        except Exception as e:
            print(f"❌ Verification failed with error: {e}")
            return False
        finally:
            # Always stop the bot
            self.stop_bot_process()

def main():
    """Main verification function"""
    verification = BotVerification()
    
    # Set up signal handler for clean exit
    def signal_handler(signum, frame):
        print("\n🛑 Verification interrupted")
        verification.stop_bot_process()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run verification
    success = verification.run_verification()
    
    if success:
        print("\n🚀 The Telegram Casino Bot is ready for production!")
        print("📋 You can now deploy using:")
        print("   • python3 main.py (direct)")
        print("   • python3 production_launcher.py (recommended)")
        print("   • ./docker-startup.sh (container)")
        print("   • systemctl start casino-bot (systemd)")
        return 0
    else:
        print("\n❌ Verification failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
