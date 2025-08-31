"""
MongoDB database interface (optional)
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from bot.core.config import Config

LOGGER = logging.getLogger(__name__)

class MongoDB:
    """MongoDB database manager"""
    
    client = None
    db = None
    
    @classmethod
    async def initialize(cls):
        """Initialize database connection"""
        try:
            cls.client = AsyncIOMotorClient(Config.DATABASE_URL)
            cls.db = cls.client.mediaindexbot
            
            # Test connection
            await cls.client.admin.command('ismaster')
            LOGGER.info("✅ MongoDB connected successfully")
            
        except Exception as e:
            LOGGER.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    @classmethod
    async def close(cls):
        """Close database connection"""
        if cls.client:
            cls.client.close()
            LOGGER.info("✅ MongoDB connection closed")
