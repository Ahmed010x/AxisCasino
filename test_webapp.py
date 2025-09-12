#!/usr/bin/env python3
"""
Simple test server for WebApp interface
"""

from aiohttp import web, ClientSession
import asyncio

async def casino_webapp(request):
    """Serve a simple casino WebApp interface"""
    user_id = request.query.get('user_id', 'guest')
    balance = request.query.get('balance', '1000')
    
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Casino WebApp</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            text-align: center; 
            padding: 20px;
        }
        .card { 
            background: rgba(255,255,255,0.1); 
            border-radius: 15px; 
            padding: 20px; 
            margin: 20px;
            backdrop-filter: blur(10px);
        }
        .game { 
            background: rgba(255,255,255,0.2); 
            border-radius: 10px; 
            padding: 15px; 
            margin: 10px;
            cursor: pointer;
        }
        .game:hover { 
            background: rgba(255,255,255,0.3); 
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>🎰 Casino WebApp</h1>
        <h2>""" + str(balance) + """ chips</h2>
        <p>Player: """ + str(user_id) + """</p>
    </div>
    
    <div class="card">
        <h3>🎮 Games</h3>
        <div class="game" onclick="alert('🎰 Slots coming soon!')">🎰 Slots</div>
        <div class="game" onclick="alert('🃏 Blackjack coming soon!')">🃏 Blackjack</div>
        <div class="game" onclick="alert('🎯 Roulette coming soon!')">🎯 Roulette</div>
        <div class="game" onclick="alert('🎲 Dice coming soon!')">🎲 Dice</div>
    </div>
    
    <div class="card">
        <p>✨ Full casino games coming soon!</p>
        <p>🔄 This is a demo interface</p>
    </div>
    
    <script>
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }
    </script>
</body>
</html>
"""
    return web.Response(text=html, content_type='text/html')

async def health_check(request):
    return web.json_response({"status": "healthy", "service": "casino-webapp"})

async def main():
    app = web.Application()
    app.router.add_get('/', casino_webapp)
    app.router.add_get('/casino', casino_webapp)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', 3001)
    await site.start()
    
    print("🚀 Casino WebApp server started on http://localhost:3001")
    print("Test URL: http://localhost:3001/casino?user_id=123&balance=5000")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
