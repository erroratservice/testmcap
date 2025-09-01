"""
Clean entry point for Media Indexing Bot
"""

import asyncio
import logging
from bot.core.startup import main

if __name__ == '__main__':
    # Setup clean logging
    logging.basicConfig(
        format='[%(asctime)s] [%(levelname)s] - %(message)s',
        datefmt='%d-%b-%y %I:%M:%S %p',
        level=logging.DEBUG  # Temporarily set to DEBUG to trace the issue
    )
    
    # Reduce Pyrogram log noise
    logging.getLogger('pyrogram').setLevel(logging.WARNING)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🔴 Bot stopped by user")
    except Exception as e:
        print(f"🔴 Fatal error: {e}")
