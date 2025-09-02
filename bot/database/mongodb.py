"""
MongoDB database interface for advanced indexing and task management.
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from bot.core.config import Config
import pymongo # Import pymongo for the synchronous client

LOGGER = logging.getLogger(__name__)

class MongoDB:
    client = None
    db = None
    task_collection = None
    media_collection = None
    message_ids_cache = None
    tvmaze_cache = None
    tvmaze_episodes_cache = None
    sync_client = None # Synchronous client for non-async operations
    sync_db = None

    @classmethod
    async def initialize(cls):
        try:
            # Asynchronous client for the main bot operations
            cls.client = AsyncIOMotorClient(Config.DATABASE_URL)
            cls.db = cls.client.mediaindexbot
            cls.task_collection = cls.db.mediamanager
            cls.media_collection = cls.db.media_data
            cls.message_ids_cache = cls.db.message_ids_cache

            # Synchronous client for the TVMaze cache
            cls.sync_client = pymongo.MongoClient(Config.DATABASE_URL)
            cls.sync_db = cls.sync_client.mediaindexbot
            cls.tvmaze_cache = cls.sync_db.tvmaze_cache
            cls.tvmaze_episodes_cache = cls.sync_db.tvmaze_episodes_cache

            await cls.client.admin.command('ismaster')
            LOGGER.info("MongoDB connected successfully.")
        except Exception as e:
            LOGGER.error(f"MongoDB connection failed: {e}")
            raise

    @classmethod
    async def close(cls):
        if cls.client is not None:
            cls.client.close()
        if cls.sync_client is not None:
            cls.sync_client.close()
        LOGGER.info("MongoDB connections closed.")

    @classmethod
    def get_tvmaze_cache(cls, title):
        """Retrieves a cached TVMaze API response using a synchronous client."""
        if cls.tvmaze_cache is not None:
            return cls.tvmaze_cache.find_one({'_id': title.lower()})
        return None

    @classmethod
    def set_tvmaze_cache(cls, title, data):
        """Saves a TVMaze API response to the cache using a synchronous client."""
        if cls.tvmaze_cache is not None:
            cls.tvmaze_cache.update_one(
                {'_id': title.lower()},
                {'$set': {'data': data}},
                upsert=True
            )

    @classmethod
    def get_tvmaze_episodes_cache(cls, maze_id):
        """Retrieves a cached episode list for a show."""
        if cls.tvmaze_episodes_cache is not None:
            return cls.tvmaze_episodes_cache.find_one({'_id': maze_id})
        return None

    @classmethod
    def set_tvmaze_episodes_cache(cls, maze_id, episodes_data):
        """Saves an episode list to the cache."""
        if cls.tvmaze_episodes_cache is not None:
            cls.tvmaze_episodes_cache.update_one(
                {'_id': maze_id},
                {'$set': {'episodes': episodes_data}},
                upsert=True
            )

    # ... (rest of your existing asynchronous methods)
    @classmethod
    async def add_media_entry(cls, parsed_data, file_size, msg_id):
        if cls.media_collection is None: return
        title = parsed_data['title']
        if parsed_data['type'] == 'series':
            season, episode = parsed_data.get('season'), parsed_data.get('episode')
            quality, codec = parsed_data.get('quality', 'Unknown'), parsed_data.get('codec', 'Unknown')
            encoder = parsed_data.get('encoder', 'Unknown')
            quality_key = f"{quality} {codec}"
            update_query = {'$inc': {f'seasons.{season}.qualities.{quality_key}.size': file_size, 'total_size': file_size},
                            '$addToSet': {f'seasons.{season}.qualities.{quality_key}.episodes_by_encoder.{encoder}': episode,
                                          f'seasons.{season}.episodes': episode}}
            await cls.media_collection.update_one({'_id': title}, update_query, upsert=True)
        elif parsed_data['type'] == 'movie':
            version_data = {'title': title, 'year': parsed_data['year'], 'quality': parsed_data['quality'],
                            'codec': parsed_data['codec'], 'encoder': parsed_data['encoder'], 'size': file_size, 'msg_id': msg_id}
            await cls.media_collection.update_one({'_id': title}, {'$addToSet': {'versions': version_data}}, upsert=True)
