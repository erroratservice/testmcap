"""
MongoDB database interface for advanced indexing.
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from bot.core.config import Config

LOGGER = logging.getLogger(__name__)

class MongoDB:
    client = None
    db = None
    collection = None 
    media_collection = None

    @classmethod
    async def initialize(cls):
        try:
            cls.client = AsyncIOMotorClient(Config.DATABASE_URL)
            cls.db = cls.client.mediaindexbot
            cls.collection = cls.db.mcapindexer
            cls.media_collection = cls.db.media_data # New collection for media details
            await cls.client.admin.command('ismaster')
            LOGGER.info("✅ MongoDB connected successfully.")
        except Exception as e:
            LOGGER.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    @classmethod
    async def close(cls):
        if cls.client:
            cls.client.close()
            LOGGER.info("✅ MongoDB connection closed.")

    @classmethod
    async def get_or_create_post(cls, title, channel_id):
        """Finds an existing post for a title or creates a placeholder."""
        if cls.collection is None: return None
        doc_id = f"post_{channel_id}_{title.lower().replace(' ', '_')}"
        post = await cls.collection.find_one({'_id': doc_id})
        if not post:
            post = {'_id': doc_id, 'title': title, 'message_id': None}
            await cls.collection.insert_one(post)
        return post

    @classmethod
    async def update_post_message_id(cls, post_id, message_id):
        """Updates the message_id for a given post."""
        if cls.collection is None: return
        await cls.collection.update_one({'_id': post_id}, {'$set': {'message_id': message_id}})

    @classmethod
    async def add_media_entry(cls, parsed_data, file_size, msg_id):
        """Adds or updates a media entry in the database."""
        if cls.media_collection is None: return
        
        title = parsed_data['title']
        season = parsed_data.get('season')
        episode = parsed_data.get('episode')
        quality_key = f"{parsed_data['quality']} {parsed_data['codec']} ({parsed_data['encoder']})"
        
        update_query = {
            '$inc': {
                f'seasons.{season}.qualities.{quality_key}.size': file_size,
                'total_size': file_size
            },
            '$addToSet': {
                f'seasons.{season}.qualities.{quality_key}.episodes': episode,
                f'seasons.{season}.episodes': episode,
            }
        }
        
        await cls.media_collection.update_one(
            {'_id': title},
            update_query,
            upsert=True
        )

    @classmethod
    async def get_media_data(cls, title):
        """Retrieves all aggregated data for a given title."""
        if cls.media_collection is None: return None
        return await cls.media_collection.find_one({'_id': title})
