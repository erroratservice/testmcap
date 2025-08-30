"""
Entry point for the Media Indexing Bot
"""

import asyncio
import logging
from bot.core.startup import main

if __name__ == '__main__':
    logging.basicConfig(
        format='[%(asctime)s] [%(levelname)s] - %(message)s',
        datefmt='%d-%b-%y %I:%M:%S %p',
        level=logging.INFO
    )
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🔴 Bot stopped by user")
    except Exception as e:
        print(f"🔴 Fatal error: {e}")
