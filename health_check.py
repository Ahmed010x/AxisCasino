#!/usr/bin/env python3
"""
Health Check Script for Telegram Casino Bot
Can be used by external monitoring systems to check bot health.
"""

import sys
import requests
import json
import os
from datetime import datetime

def discover_bot_port():
    """Auto-discover the bot's health endpoint port"""
    # Check environment variable first
    env_port = os.getenv('PORT')
    if env_port:
        try:
            port = int(env_port)
            if test_port(port):
                return port
        except ValueError:
            pass
    
    # Try common ports
    ports_to_try = [10000, 8001, 8002, 8003, 5000]
    for port in ports_to_try:
        if test_port(port):
            return port
    
    return 8001  # fallback

def test_port(port):
    """Test if the bot is responding on a specific port"""
    try:
        response = requests.get(f'http://localhost:{port}/health', timeout=2)
        return response.status_code in [200, 503]
    except:
        return False

def check_bot_health(port=None, timeout=10):
    """Check bot health via HTTP endpoint"""
    if port is None:
        port = discover_bot_port()
    
    try:
        response = requests.get(f'http://localhost:{port}/health', timeout=timeout)
        
        if response.status_code in [200, 503]:
            # Bot is responding, even if it reports unhealthy status
            health_data = response.json()
            is_healthy = response.status_code == 200
            return is_healthy, health_data, port
        else:
            return False, {"error": f"HTTP {response.status_code}"}, port
            
    except requests.exceptions.ConnectionError:
        return False, {"error": "Connection refused - bot may be down"}, port
    except requests.exceptions.Timeout:
        return False, {"error": "Health check timeout"}, port
    except Exception as e:
        return False, {"error": str(e)}, port

def check_multiple_ports():
    """Check health on multiple ports in case of port conflicts"""
    # Auto-discover the port
    port = discover_bot_port()
    healthy, data, discovered_port = check_bot_health(port)
    
    if discovered_port:  # Bot is responding on this port
        return healthy, data, discovered_port
    
    return False, {"error": "No bot instances found on any port"}, None

def main():
    """Main health check"""
    healthy, data, port = check_multiple_ports()
    
    timestamp = datetime.now().isoformat()
    
    result = {
        "timestamp": timestamp,
        "healthy": healthy,
        "port": port,
        "data": data
    }
    
    # Output as JSON for easy parsing
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    return 0 if healthy else 1

if __name__ == "__main__":
    sys.exit(main())
