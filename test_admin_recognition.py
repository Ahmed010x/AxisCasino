#!/usr/bin/env python3
"""
Test script to verify admin recognition is working properly.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load admin configuration (same as in main.py)
ADMIN_USER_IDS = list(map(int, os.environ.get("ADMIN_USER_IDS", "").split(","))) if os.environ.get("ADMIN_USER_IDS") else []

def is_admin(user_id: int) -> bool:
    """Check if user is an admin/owner"""
    return user_id in ADMIN_USER_IDS

def test_admin_recognition():
    """Test admin recognition functionality"""
    print("🔧 Admin Recognition Test")
    print("=" * 40)
    
    # Print configuration
    print(f"📋 Raw env var: {os.environ.get('ADMIN_USER_IDS', 'NOT SET')}")
    print(f"📋 Parsed admin IDs: {ADMIN_USER_IDS}")
    print(f"📋 Number of admins: {len(ADMIN_USER_IDS)}")
    print()
    
    # Test the configured admin ID
    if ADMIN_USER_IDS:
        test_admin_id = ADMIN_USER_IDS[0]
        print(f"🧪 Testing admin ID: {test_admin_id}")
        print(f"✅ is_admin({test_admin_id}): {is_admin(test_admin_id)}")
        print()
    
    # Test a non-admin ID
    test_non_admin_id = 123456789
    print(f"🧪 Testing non-admin ID: {test_non_admin_id}")
    print(f"❌ is_admin({test_non_admin_id}): {is_admin(test_non_admin_id)}")
    print()
    
    # Summary
    if ADMIN_USER_IDS:
        print("✅ Admin recognition is configured and working!")
        print(f"🎮 User {ADMIN_USER_IDS[0]} will have admin features in the bot")
    else:
        print("⚠️ No admin users configured")
    
    return len(ADMIN_USER_IDS) > 0

if __name__ == "__main__":
    success = test_admin_recognition()
    exit(0 if success else 1)
