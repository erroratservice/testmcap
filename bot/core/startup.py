"""
Clean bot startup sequence
"""

import asyncio
import logging
import os
from bot.core.config import Config
from bot.core.client import TgClient
from bot.core.handlers import register_handlers
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

async def main():
    """Main startup function"""
    try:
        # Load and validate configuration
        Config.load()
        Config.validate()
        LOGGER.info("✅ Configuration loaded and validated")
        
        # Create download directory
        os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
        
        # Initialize database (optional)
        if Config.DATABASE_URL:
            try:
                await MongoDB.initialize()
                LOGGER.info("✅ Database connection established")
            except Exception as e:
                LOGGER.warning(f"⚠️ Database connection failed: {e}")
        
        # Initialize Telegram clients
        await TgClient.initialize()
        
        # Register command handlers
        register_handlers()
        
        # Success message
        LOGGER.info("🚀 Media Indexing Bot started successfully!")
        LOGGER.info("🎯 Ready for media processing operations")
        
        # Keep running
        await asyncio.Future()
        
    except KeyboardInterrupt:
        LOGGER.info("👋 Bot stopped by user")
    except Exception as e:
        LOGGER.error(f"💥 Startup failed: {e}")
        raise
    finally:
        await TgClient.stop()
        if Config.DATABASE_URL:
            await MongoDB.close()
