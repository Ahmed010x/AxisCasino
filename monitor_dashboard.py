#!/usr/bin/env python3
"""
Bot Monitoring Dashboard
Real-time monitoring of the Telegram Casino Bot health and statistics.
"""

import time
import json
import requests
import subprocess
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class BotMonitor:
    """Monitor bot health and system resources"""
    
    def __init__(self, port: int = None):
        self.port = port or self.discover_bot_port()
        self.start_time = datetime.now()
        self.health_history = []
        self.max_history = 100
    
    def discover_bot_port(self) -> int:
        """Auto-discover the bot's health endpoint port"""
        # Check environment variable first
        env_port = os.getenv('PORT')
        if env_port:
            try:
                port = int(env_port)
                if self.test_port(port):
                    print(f"✅ Using port {port} from environment")
                    return port
            except ValueError:
                pass
        
        # Try common ports
        ports_to_try = [10000, 8001, 8002, 8003, 5000]
        for port in ports_to_try:
            if self.test_port(port):
                print(f"✅ Discovered bot on port {port}")
                return port
        
        print(f"⚠️ Could not discover bot port, using default 8001")
        return 8001
    
    def test_port(self, port: int) -> bool:
        """Test if the bot is responding on a specific port"""
        try:
            response = requests.get(f'http://localhost:{port}/health', timeout=2)
            return response.status_code in [200, 503]
        except:
            return False
        
    def get_bot_health(self) -> Dict[str, Any]:
        """Get bot health from HTTP endpoint"""
        try:
            response = requests.get(f'http://localhost:{self.port}/health', timeout=5)
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "data": response.json(),
                    "response_time": response.elapsed.total_seconds(),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system resource statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def get_bot_process_info(self) -> Dict[str, Any]:
        """Get information about bot processes"""
        try:
            bot_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'main.py' in cmdline or 'production_launcher.py' in cmdline:
                        bot_processes.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "cmdline": cmdline,
                            "cpu_percent": proc.info['cpu_percent'],
                            "memory_percent": proc.info['memory_percent']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                "processes": bot_processes,
                "count": len(bot_processes),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            return f"{seconds/86400:.1f}d"
    
    def display_dashboard(self):
        """Display the monitoring dashboard"""
        # Clear screen
        print("\033[2J\033[H", end="")
        
        # Header
        print("🎰 Telegram Casino Bot - Monitoring Dashboard")
        print("=" * 60)
        print(f"⏰ Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🚀 Monitor Uptime: {self.format_duration((datetime.now() - self.start_time).total_seconds())}")
        print()
        
        # Bot Health
        health = self.get_bot_health()
        print("🏥 BOT HEALTH")
        print("-" * 20)
        
        if health["status"] == "healthy":
            data = health["data"]
            print(f"✅ Status: {data.get('status', 'unknown').upper()}")
            print(f"⏱️  Uptime: {self.format_duration(data.get('uptime_seconds', 0))}")
            print(f"📊 Updates: {data.get('total_updates', 0)}")
            print(f"❌ Errors: {data.get('total_errors', 0)}")
            print(f"📈 Error Rate: {data.get('error_rate', 0):.2%}")
            print(f"🔄 Last Update: {self.format_duration(data.get('last_update_ago', 0))} ago")
            print(f"⚡ Response Time: {health.get('response_time', 0):.3f}s")
        else:
            print(f"❌ Status: UNHEALTHY")
            print(f"🔥 Error: {health.get('error', 'Unknown error')}")
        print()
        
        # System Resources
        system = self.get_system_stats()
        print("💻 SYSTEM RESOURCES")
        print("-" * 20)
        
        if "error" not in system:
            print(f"🔥 CPU Usage: {system['cpu_percent']:.1f}%")
            print(f"🧠 Memory Usage: {system['memory']['percent']:.1f}% ({self.format_bytes(system['memory']['used'])}/{self.format_bytes(system['memory']['total'])})")
            print(f"💾 Disk Usage: {system['disk']['percent']:.1f}% ({self.format_bytes(system['disk']['used'])}/{self.format_bytes(system['disk']['total'])})")
        else:
            print(f"❌ Error: {system['error']}")
        print()
        
        # Process Information
        process_info = self.get_bot_process_info()
        print("🔄 BOT PROCESSES")
        print("-" * 20)
        
        if "error" not in process_info:
            if process_info["count"] > 0:
                for proc in process_info["processes"]:
                    print(f"📋 PID {proc['pid']}: {proc['name']}")
                    print(f"   💾 Memory: {proc['memory_percent']:.1f}%")
                    print(f"   🔥 CPU: {proc['cpu_percent']:.1f}%")
                    print(f"   📝 Command: {proc['cmdline'][:50]}...")
                    print()
            else:
                print("⚠️ No bot processes found")
        else:
            print(f"❌ Error: {process_info['error']}")
        
        # Health History
        if len(self.health_history) > 1:
            print("📈 HEALTH TREND (Last 10 checks)")
            print("-" * 35)
            for entry in self.health_history[-10:]:
                status_icon = "✅" if entry["status"] == "healthy" else "❌"
                timestamp = datetime.fromisoformat(entry["timestamp"]).strftime("%H:%M:%S")
                print(f"{status_icon} {timestamp} - {entry['status'].upper()}")
            print()
        
        print("🔄 Auto-refresh every 10 seconds... (Ctrl+C to exit)")
    
    def run_monitoring(self):
        """Run continuous monitoring"""
        try:
            while True:
                # Get current health and add to history
                health = self.get_bot_health()
                self.health_history.append(health)
                
                # Keep history limited
                if len(self.health_history) > self.max_history:
                    self.health_history.pop(0)
                
                # Display dashboard
                self.display_dashboard()
                
                # Wait before next update
                time.sleep(10)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"\n\n❌ Monitoring error: {e}")

def main():
    """Main entry point"""
    print("🚀 Starting Bot Monitoring Dashboard...")
    
    # Check if psutil is available
    try:
        import psutil
    except ImportError:
        print("❌ psutil not installed. Install with: pip install psutil")
        return 1
    
    # Check if requests is available
    try:
        import requests
    except ImportError:
        print("❌ requests not installed. Install with: pip install requests")
        return 1
    
    # Create monitor and show port discovery
    print("🔍 Discovering bot health endpoint...")
    monitor = BotMonitor()
    print(f"📡 Monitoring bot on port {monitor.port}")
    
    monitor.run_monitoring()
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
