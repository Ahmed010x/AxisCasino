# Production Keep-Alive Server Configuration

## Overview
The bot now uses a production-ready keep-alive server built with Waitress WSGI server instead of Flask's development server.

## Features

### Production WSGI Server (Waitress)
- **Multi-threaded**: Configurable thread pool (default: 4 threads)
- **Connection limiting**: Maximum 1000 concurrent connections
- **Proxy support**: Handles X-Forwarded-For and X-Forwarded-Proto headers
- **Memory efficient**: Automatic cleanup every 30 seconds
- **Graceful fallback**: Falls back to Flask dev server if Waitress fails

### Health Check Endpoints
- `GET /` - Basic status message
- `GET /health` - Detailed health check with bot info
- `GET /status` - Active status with version and webapp info
- `GET /ping` - Simple ping/pong with timestamp
- `GET /metrics` - Basic metrics including uptime

### Environment Configuration
```bash
# Server Configuration
HOST=0.0.0.0              # Bind address (default: 0.0.0.0)
PORT=8080                 # Server port (default: 8080)
THREADS=4                 # Worker threads (default: 4)

# For Render.com deployment
PORT=10000                # Render assigns this automatically
```

### Deployment Benefits
1. **Production-ready**: Uses Waitress WSGI server
2. **Scalable**: Multi-threaded with connection limits
3. **Reliable**: Automatic fallback mechanism
4. **Monitorable**: Multiple health check endpoints
5. **Proxy-friendly**: Handles reverse proxy headers
6. **Resource-efficient**: Automatic cleanup and memory management

### Monitoring
The `/metrics` endpoint provides:
- Bot uptime in seconds
- Running status
- Bot version
- Demo mode status

### Error Handling
- Graceful fallback to Flask dev server if Waitress fails
- Comprehensive error logging
- Connection timeout and cleanup
- Trusted proxy header validation

## Usage in Production

### Render.com
The server automatically uses the PORT environment variable assigned by Render.

### Railway.app
Compatible with Railway's port assignment and proxy headers.

### Heroku
Fully compatible with Heroku's dyno system and port binding.

### VPS/Dedicated Servers
Configure HOST and PORT as needed for your infrastructure.

## Load Testing
The server can handle:
- Up to 1000 concurrent connections
- 4 worker threads (configurable)
- Automatic connection cleanup
- Memory-efficient operation

## Security
- Validates trusted proxy headers
- Logs untrusted proxy headers for security monitoring
- Thread-safe operation
- Resource limits to prevent DoS

## Logging
All server events are logged with appropriate levels:
- INFO: Server startup and configuration
- WARNING: Fallback scenarios
- ERROR: Server failures and exceptions
