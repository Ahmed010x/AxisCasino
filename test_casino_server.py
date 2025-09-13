#!/usr/bin/env python3
"""
Simple test server for casino game pages
"""
import os
import asyncio
from aiohttp import web

async def serve_game_page(request):
    """Serve individual game pages"""
    # Extract game name from the request path
    game_file = request.match_info.get('game_file', '')
    user_id = request.query.get('user_id', 'guest')
    balance = request.query.get('balance', '1000')
    
    # Security check - only allow valid game files
    valid_games = [
        'game_slots.html', 'game_slots_enhanced.html',
        'game_blackjack.html', 'game_blackjack_enhanced.html',
        'game_roulette.html', 'game_roulette_enhanced.html',
        'game_dice.html', 'game_dice_enhanced.html',
        'game_poker.html', 'game_crash.html', 'game_mines.html', 
        'game_plinko.html', 'game_limbo.html', 'game_hilo.html', 
        'game_coinflip.html'
    ]
    
    if game_file not in valid_games:
        return web.Response(status=404, text="Game not found")
    
    # Try to read the game file
    game_path = os.path.join(os.path.dirname(__file__), game_file)
    try:
        with open(game_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Replace placeholders with actual values if needed
        html_content = html_content.replace('{USER_ID}', str(user_id))
        html_content = html_content.replace('{BALANCE}', str(balance))
        
        return web.Response(text=html_content, content_type='text/html')
    except FileNotFoundError:
        return web.Response(status=404, text=f"Game file {game_file} not found")

async def serve_casino_webapp(request):
    """Serve the main casino webapp"""
    user_id = request.query.get('user_id', 'guest')
    balance = request.query.get('balance', '1000')
    
    # Try to read the main casino webapp
    casino_path = os.path.join(os.path.dirname(__file__), 'casino_webapp_new.html')
    try:
        with open(casino_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Replace placeholders
        html_content = html_content.replace('{USER_ID}', str(user_id))
        html_content = html_content.replace('{BALANCE}', str(balance))
        
        return web.Response(text=html_content, content_type='text/html')
    except FileNotFoundError:
        return web.Response(status=404, text="Casino webapp not found")

async def health_check(request):
    """Health check endpoint"""
    return web.json_response({
        "status": "healthy",
        "message": "Casino game server is running",
        "games": ["slots", "blackjack", "dice", "roulette", "poker"]
    })

async def main():
    """Start the test server"""
    app = web.Application()
    
    # Add routes
    app.router.add_get('/health', health_check)
    app.router.add_get('/', serve_casino_webapp)
    app.router.add_get('/casino', serve_casino_webapp)
    app.router.add_get('/{game_file:game_[a-z_]+\.html}', serve_game_page)
    
    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', 3000)
    await site.start()
    
    print("🎰 Casino Game Server Started!")
    print("🌐 Server running at: http://localhost:3000")
    print("🎮 Main Casino: http://localhost:3000/casino?user_id=123&balance=1000")
    print("🎰 Test Slots: http://localhost:3000/game_slots_enhanced.html?user_id=123&balance=1000")
    print("🃏 Test Blackjack: http://localhost:3000/game_blackjack_enhanced.html?user_id=123&balance=1000")
    print("🎲 Test Dice: http://localhost:3000/game_dice_enhanced.html?user_id=123&balance=1000")
    print("💊 Health Check: http://localhost:3000/health")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
