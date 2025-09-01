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

    @classmethod
    async def initialize(cls):
        try:
            cls.client = AsyncIOMotorClient(Config.DATABASE_URL)
            cls.db = cls.client.mediaindexbot
            cls.task_collection = cls.db.mcapindexer
            cls.media_collection = cls.db.media_data
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

    # --- Live Status & Task Management ---
    @classmethod
    async def set_status_message(cls, chat_id, message_id):
        if cls.task_collection is None: return
        await cls.task_collection.update_one(
            {'_id': 'status_message_tracker'},
            {'$set': {'chat_id': chat_id, 'message_id': message_id}},
            upsert=True
        )

    @classmethod
    async def get_status_message(cls):
        if cls.task_collection is None: return None
        return await cls.task_collection.find_one({'_id': 'status_message_tracker'})
    
    @classmethod
    async def delete_status_message_tracker(cls):
        if cls.task_collection is None: return
        await cls.task_collection.delete_one({'_id': 'status_message_tracker'})

    @classmethod
    async def start_scan(cls, scan_id, channel_id, user_id, total_messages, chat_title, operation):
        if cls.task_collection is None: return
        await cls.task_collection.insert_one({
            '_id': scan_id, 'type': 'active_scan', 'operation': operation,
            'channel_id': channel_id, 'user_id': user_id, 'total_messages': total_messages,
            'processed_messages': 0, 'chat_title': chat_title
        })

    @classmethod
    async def update_scan_progress(cls, scan_id, processed_count):
        if cls.task_collection is None: return
        await cls.task_collection.update_one(
            {'_id': scan_id, 'type': 'active_scan'},
            {'$set': {'processed_messages': processed_count}}
        )

    @classmethod
    async def end_scan(cls, scan_id):
        if cls.task_collection is None: return
        await cls.task_collection.delete_one({'_id': scan_id, 'type': 'active_scan'})

    @classmethod
    async def get_active_scans(cls):
        if cls.task_collection is None: return []
        cursor = cls.task_collection.find({'type': 'active_scan'})
        return await cursor.to_list(length=None)

    @classmethod
    async def clear_all_scans(cls):
        if cls.task_collection is None: return
        await cls.task_collection.delete_many({'type': 'active_scan'})

    # --- RESTORED: Failed IDs Management ---
    @classmethod
    async def save_failed_ids(cls, channel_id, failed_ids):
        """Save failed IDs as a document in the task collection."""
        if cls.task_collection is None: return
        await cls.task_collection.update_one(
            {'_id': f"failed_{channel_id}", 'type': 'failed_job'},
            {'$set': {'channel_id': channel_id, 'failed_ids': failed_ids}},
            upsert=True
        )

    @classmethod
    async def get_failed_ids(cls, channel_id):
        """Retrieve failed IDs from the task collection."""
        if cls.task_collection is None: return []
        document = await cls.task_collection.find_one({'_id': f"failed_{channel_id}", 'type': 'failed_job'})
        return document.get('failed_ids', []) if document else []

    @classmethod
    async def clear_failed_ids(cls, channel_id):
        """Clear the failed IDs document from the task collection."""
        if cls.task_collection is None: return
        await cls.task_collection.delete_one({'_id': f"failed_{channel_id}", 'type': 'failed_job'})

    # --- Advanced Indexing ---
    @classmethod
    async def get_or_create_post(cls, title, channel_id):
        """Finds an existing post for a title or creates a placeholder."""
        if cls.task_collection is None: return None
        doc_id = f"post_{channel_id}_{title.lower().replace(' ', '_')}"
        post = await cls.task_collection.find_one({'_id': doc_id})
        if not post:
            post = {'_id': doc_id, 'title': title, 'message_id': None}
            await cls.task_collection.insert_one(post)
        return post

    @classmethod
    async def update_post_message_id(cls, post_id, message_id):
        """Updates the message_id for a given post."""
        if cls.task_collection is None: return
        await cls.task_collection.update_one({'_id': post_id}, {'$set': {'message_id': message_id}})

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
