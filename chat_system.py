# chat_system.py
"""
Live Chat System for Casino WebApp
Handles real-time messaging between users
"""

import json
import uuid
import weakref
from datetime import datetime
from aiohttp import web, WSMsgType
import logging

logger = logging.getLogger(__name__)

class ChatManager:
    """Manages live chat connections and message broadcasting"""
    
    def __init__(self):
        self.connections = weakref.WeakSet()
        self.user_connections = {}  # user_id -> websocket info
        self.message_history = []
        self.max_history = 50
        
    async def add_connection(self, websocket, user_id, username):
        """Add a new chat connection"""
        self.connections.add(websocket)
        self.user_connections[user_id] = {
            'ws': websocket,
            'username': username,
            'joined_at': datetime.now()
        }
        
        # Send recent message history to new user
        for message in self.message_history[-10:]:
            await self.send_to_user(websocket, message)
        
        # Broadcast online count update
        await self.broadcast_online_count()
        
        logger.info(f"User {username} ({user_id}) joined chat")
        
    async def remove_connection(self, websocket, user_id=None):
        """Remove a chat connection"""
        if user_id and user_id in self.user_connections:
            username = self.user_connections[user_id]['username']
            del self.user_connections[user_id]
            await self.broadcast_online_count()
            logger.info(f"User {username} ({user_id}) left chat")
    
    async def broadcast_message(self, message_data):
        """Broadcast message to all connected users"""
        if message_data['type'] == 'message':
            # Add to history
            self.message_history.append(message_data)
            if len(self.message_history) > self.max_history:
                self.message_history.pop(0)
        
        # Send to all connections
        dead_connections = []
        for connection in list(self.connections):
            try:
                await self.send_to_user(connection, message_data)
            except Exception as e:
                logger.warning(f"Failed to send message: {e}")
                dead_connections.append(connection)
        
        # Clean up dead connections
        for dead_conn in dead_connections:
            self.connections.discard(dead_conn)
    
    async def send_to_user(self, websocket, message_data):
        """Send message to specific user"""
        if websocket.closed:
            return
        
        try:
            await websocket.send_str(json.dumps(message_data))
        except Exception as e:
            logger.warning(f"Failed to send message to user: {e}")
            raise
    
    async def broadcast_online_count(self):
        """Broadcast current online user count"""
        count_message = {
            'type': 'online_count',
            'count': len(self.user_connections),
            'timestamp': datetime.now().isoformat()
        }
        await self.broadcast_message(count_message)
    
    async def handle_user_message(self, user_id, username, message_text):
        """Process and broadcast user message"""
        # Basic validation
        if not message_text or len(message_text.strip()) == 0:
            return False
        
        if len(message_text) > 200:
            return False
        
        # Create message object
        message_data = {
            'type': 'message',
            'id': str(uuid.uuid4()),
            'user': {
                'id': user_id,
                'name': username
            },
            'message': message_text.strip(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Broadcast to all users
        await self.broadcast_message(message_data)
        return True

# Global chat manager instance
chat_manager = ChatManager()

async def websocket_chat_handler(request):
    """WebSocket handler for live chat"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    user_id = None
    username = None
    
    try:
        # Get user info from query parameters
        user_id = request.query.get('user_id', f'guest_{uuid.uuid4().hex[:8]}')
        username = request.query.get('username', f'Player_{user_id[-4:]}')
        
        # Add connection to chat manager
        await chat_manager.add_connection(ws, user_id, username)
        
        # Handle incoming messages
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    
                    if data.get('type') == 'message':
                        message_text = data.get('message', '').strip()
                        if message_text:
                            success = await chat_manager.handle_user_message(
                                user_id, username, message_text
                            )
                            if not success:
                                # Send error message back to user
                                error_msg = {
                                    'type': 'error',
                                    'message': 'Message too long or invalid',
                                    'timestamp': datetime.now().isoformat()
                                }
                                await chat_manager.send_to_user(ws, error_msg)
                    
                    elif data.get('type') == 'ping':
                        # Respond to ping
                        pong_msg = {
                            'type': 'pong',
                            'timestamp': datetime.now().isoformat()
                        }
                        await chat_manager.send_to_user(ws, pong_msg)
                
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from user {user_id}")
                except Exception as e:
                    logger.error(f"Error handling message from {user_id}: {e}")
            
            elif msg.type == WSMsgType.ERROR:
                logger.error(f'WebSocket error for user {user_id}: {ws.exception()}')
                break
    
    except Exception as e:
        logger.error(f"WebSocket connection error for user {user_id}: {e}")
    
    finally:
        # Clean up connection
        if user_id:
            await chat_manager.remove_connection(ws, user_id)
    
    return ws
