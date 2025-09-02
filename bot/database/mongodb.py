"""
MongoDB database interface for advanced indexing and task management.
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from bot.core.config import Config

LOGGER = logging.getLogger(__name__)

class MongoDB:
    client = None
    db = None
    task_collection = None
    media_collection = None
    message_ids_cache = None
    tvmaze_cache = None # New collection for TVMaze cache

    @classmethod
    async def initialize(cls):
        try:
            cls.client = AsyncIOMotorClient(Config.DATABASE_URL)
            cls.db = cls.client.mediaindexbot
            cls.task_collection = cls.db.mediamanager
            cls.media_collection = cls.db.media_data
            cls.message_ids_cache = cls.db.message_ids_cache
            cls.tvmaze_cache = cls.db.tvmaze_cache # Initialize the cache collection
            await cls.client.admin.command('ismaster')
            LOGGER.info("MongoDB connected successfully.")
        except Exception as e:
            LOGGER.error(f"MongoDB connection failed: {e}")
            raise
    
    # ... (rest of the existing methods)

    @classmethod
    async def get_tvmaze_cache(cls, title):
        """Retrieves a cached TVMaze API response."""
        if cls.tvmaze_cache is not None:
            # Use a case-insensitive search for the title
            return await cls.tvmaze_cache.find_one({'_id': title.lower()})
        return None

    @classmethod
    async def set_tvmaze_cache(cls, title, data):
        """Saves a TVMaze API response to the cache."""
        if cls.tvmaze_cache is not None:
            # Use the lowercase title as a unique ID
            await cls.tvmaze_cache.update_one(
                {'_id': title.lower()},
                {'$set': {'data': data}},
                upsert=True
            )

    # ... (rest of the existing methods)
