#!/usr/bin/env python3
"""Debug version of main.py to catch the Updater error"""

import asyncio
import traceback
import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def debug_main():
    """Debug version of the main function"""
    try:
        print("=== DEBUG MAIN.PY EXECUTION ===")
        
        # Import main module
        print("Importing main module...")
        import main
        print("✅ Main module imported successfully")
        
        # Check environment
        print(f"BOT_TOKEN: {'Set' if main.BOT_TOKEN else 'Not set'}")
        print(f"OWNER_USER_ID: {main.OWNER_USER_ID}")
        print(f"DEMO_MODE: {main.DEMO_MODE}")
        
        # Try to call main() function but with better error handling
        print("Calling main.main()...")
        
        # Use a timeout to prevent hanging
        try:
            await asyncio.wait_for(main.main(), timeout=10.0)
        except asyncio.TimeoutError:
            print("✅ main() started successfully (timeout reached)")
        except Exception as e:
            print(f"❌ Error in main(): {e}")
            print(f"Error type: {type(e)}")
            
            # Check if this is the Updater error
            if "'Updater' object has no attribute" in str(e):
                print("🔍 FOUND THE UPDATER ERROR!")
                print("Full traceback:")
                traceback.print_exc()
                
                # Try to analyze the stack
                import inspect
                frame = inspect.currentframe()
                while frame:
                    print(f"Frame: {frame.f_code.co_filename}:{frame.f_lineno} in {frame.f_code.co_name}")
                    frame = frame.f_back
            
            raise
        
        print("✅ Debug completed successfully")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(debug_main())
    print(f"\\nResult: {'Success' if success else 'Failed'}")
