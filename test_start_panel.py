#!/usr/bin/env python3
"""
Test the start panel functionality directly
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import init_db, create_user, get_user, start_command

class MockUser:
    def __init__(self, user_id=12345, username="test_user"):
        self.id = user_id
        self.username = username
        self.first_name = "Test"
        self.full_name = "Test User"

class MockMessage:
    def __init__(self):
        self.replies = []
    
    async def reply_text(self, text, reply_markup=None, parse_mode=None):
        print("📱 BOT REPLY:")
        print(text)
        if reply_markup:
            print("\n🎛️ KEYBOARD BUTTONS:")
            for row in reply_markup.inline_keyboard:
                row_text = " | ".join([btn.text for btn in row])
                print(f"   {row_text}")
        print("\n" + "="*50)
        return True

class MockUpdate:
    def __init__(self):
        self.effective_user = MockUser()
        self.message = MockMessage()

class MockContext:
    pass

async def test_start_panel():
    """Test the start panel functionality"""
    print("🧪 TESTING START PANEL FUNCTIONALITY")
    print("="*50)
    
    # Initialize database
    await init_db()
    print("✅ Database initialized")
    
    # Test with new user
    print("\n🆕 TESTING NEW USER REGISTRATION:")
    update = MockUpdate()
    update.effective_user = MockUser(12345, "new_user")
    context = MockContext()
    
    await start_command(update, context)
    
    # Test with existing user
    print("\n👤 TESTING EXISTING USER:")
    update2 = MockUpdate()
    update2.effective_user = MockUser(12345, "new_user")  # Same user
    
    await start_command(update2, context)
    
    print("\n✅ START PANEL TEST COMPLETED!")

if __name__ == "__main__":
    asyncio.run(test_start_panel())
