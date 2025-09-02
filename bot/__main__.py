"""
Clean entry point for Media Indexing Bot
"""

import asyncio
import logging  # <-- FIX: Added the missing import
from bot.core.startup import main

if __name__ == '__main__':
    # Setup clean logging
    logging.basicConfig(
        format='[%(asctime)s] [%(levelname)s] - %(message)s',
        datefmt='%d-%b-%y %I:%M:%S %p',
        level=logging.INFO,
        handlers=[
            logging.FileHandler("log.txt"),
            logging.StreamHandler()
        ]
    )
    
    # Reduce Pyrogram log noise
    logging.getLogger('pyrogram').setLevel(logging.WARNING)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
