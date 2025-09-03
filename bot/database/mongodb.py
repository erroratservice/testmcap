"""
MongoDB database interface for advanced indexing and task management.
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from bot.core.config import Config
import pymongo

LOGGER = logging.getLogger(__name__)

class MongoDB:
    client = None
    db = None
    task_collection = None
    media_collection = None
    message_ids_cache = None
    tvmaze_cache = None
    sync_client = None
    sync_db = None

    @classmethod
    async def initialize(cls):
        try:
            cls.client = AsyncIOMotorClient(Config.DATABASE_URL)
            cls.db = cls.client.mediaindexbot
            cls.task_collection = cls.db.mediamanager
            cls.media_collection = cls.db.media_data
            cls.message_ids_cache = cls.db.message_ids_cache
            cls.sync_client = pymongo.MongoClient(Config.DATABASE_URL)
            cls.sync_db = cls.sync_client.mediaindexbot
            cls.tvmaze_cache = cls.sync_db.tvmaze_cache
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
        if cls.tvmaze_cache is not None:
            return cls.tvmaze_cache.find_one({'_id': title.lower()})
        return None

    @classmethod
    def set_tvmaze_cache(cls, title, data):
        if cls.tvmaze_cache is not None:
            cls.tvmaze_cache.update_one(
                {'_id': title.lower()},
                {'$set': {'data': data}},
                upsert=True
            )

    @classmethod
    async def get_cached_message_ids(cls, channel_id):
        if cls.message_ids_cache is None: return []
        document = await cls.message_ids_cache.find_one({'_id': channel_id})
        return document.get('message_ids', []) if document else []

    @classmethod
    async def update_cached_message_ids(cls, channel_id, new_ids):
        if cls.message_ids_cache is not None:
            await cls.message_ids_cache.update_one({'_id': channel_id}, {'$addToSet': {'message_ids': {'$each': new_ids}}}, upsert=True)

    @classmethod
    async def clear_cached_message_ids(cls, channel_id):
        if cls.message_ids_cache is not None:
            await cls.message_ids_cache.delete_one({'_id': channel_id})

    @classmethod
    async def clear_media_data_for_channel(cls, channel_id):
        if cls.db is None: return
        post_prefix = f"post_{channel_id}_"
        post_docs = await cls.task_collection.find({'_id': {'$regex': f'^{post_prefix}'}}).to_list(length=None)
        if not post_docs: return
        titles_to_delete = [doc['canonical_title'] for doc in post_docs]
        if titles_to_delete:
            await cls.media_collection.delete_many({'_id': {'$in': titles_to_delete}})
            await cls.task_collection.delete_many({'_id': {'$regex': f'^{post_prefix}'}})
            LOGGER.info(f"Cleared media and post data for {len(titles_to_delete)} titles from channel {channel_id}.")

    @classmethod
    async def add_media_entry(cls, parsed_data, file_size, msg_id):
        if cls.media_collection is None: return
        
        # Use canonical_title for unique identification in the database
        canonical_title = parsed_data['canonical_title']
        display_title = parsed_data['title']

        if parsed_data['type'] == 'series':
            season, episode = parsed_data.get('season'), parsed_data.get('episode')
            quality, codec = parsed_data.get('quality', 'Unknown'), parsed_data.get('codec', 'Unknown')
            encoder = parsed_data.get('encoder', 'Unknown')
            quality_key = f"{quality} {codec}"
            
            update_query = {
                '$set': {'display_title': display_title},
                '$inc': {
                    f'seasons.{season}.qualities.{quality_key}.size': file_size,
                    'total_size': file_size
                },
                '$addToSet': {
                    f'seasons.{season}.qualities.{quality_key}.episodes_by_encoder.{encoder}': episode,
                    f'seasons.{season}.episodes': episode
                }
            }
            await cls.media_collection.update_one({'_id': canonical_title}, update_query, upsert=True)
            
        elif parsed_data['type'] == 'movie':
            version_data = {
                'title': display_title,
                'year': parsed_data['year'],
                'quality': parsed_data['quality'],
                'codec': parsed_data['codec'],
                'encoder': parsed_data['encoder'],
                'size': file_size,
                'msg_id': msg_id
            }
            update_query = {
                '$set': {'display_title': display_title},
                '$addToSet': {'versions': version_data}
            }
            await cls.media_collection.update_one({'_id': canonical_title}, update_query, upsert=True)
            
    @classmethod
    async def get_or_create_post(cls, canonical_title, display_title, channel_id):
        if cls.task_collection is None: return None
        doc_id = f"post_{channel_id}_{canonical_title.lower().replace(' ', '_')}"
        post = await cls.task_collection.find_one({'_id': doc_id})
        if not post:
            post = {
                '_id': doc_id,
                'canonical_title': canonical_title,
                'display_title': display_title,
                'channel_id': channel_id,
                'message_id': None
            }
            await cls.task_collection.insert_one(post)
        return post

    @classmethod
    async def update_post_message_id(cls, post_id, message_id):
        if cls.task_collection is not None: await cls.task_collection.update_one({'_id': post_id}, {'$set': {'message_id': message_id}})

    @classmethod
    async def get_media_data(cls, title):
        if cls.media_collection is not None: return await cls.media_collection.find_one({'_id': title})
        return None

    @classmethod
    async def set_status_message(cls, chat_id, message_id):
        if cls.task_collection is not None: await cls.task_collection.update_one({'_id': 'status_message_tracker'}, {'$set': {'chat_id': chat_id, 'message_id': message_id}}, upsert=True)
    
    @classmethod
    async def get_status_message(cls):
        if cls.task_collection is not None: return await cls.task_collection.find_one({'_id': 'status_message_tracker'})
        return None

    @classmethod
    async def delete_status_message_tracker(cls):
        if cls.task_collection is not None: await cls.task_collection.delete_one({'_id': 'status_message_tracker'})

    @classmethod
    async def save_failed_ids(cls, channel_id, failed_ids):
        if cls.task_collection is not None: await cls.task_collection.update_one({'_id': f"failed_{channel_id}", 'type': 'failed_job'}, {'$set': {'channel_id': channel_id, 'failed_ids': failed_ids}}, upsert=True)

    @classmethod
    async def get_failed_ids(cls, channel_id):
        if cls.task_collection is not None:
            doc = await cls.task_collection.find_one({'_id': f"failed_{channel_id}", 'type': 'failed_job'})
            return doc.get('failed_ids', []) if doc else []
        return []

    @classmethod
    async def clear_failed_ids(cls, channel_id):
        if cls.task_collection is not None: await cls.task_collection.delete_one({'_id': f"failed_{channel_id}", 'type': 'failed_job'})

    @classmethod
    async def start_scan(cls, scan_id, channel_id, user_id, total_messages, chat_title, operation):
        if cls.task_collection is not None: await cls.task_collection.update_one({'_id': scan_id}, {'$set': {'type': 'active_scan', 'operation': operation, 'channel_id': channel_id, 'user_id': user_id, 'total_messages': total_messages, 'processed_messages': 0, 'chat_title': chat_title}}, upsert=True)

    @classmethod
    async def update_scan_total(cls, scan_id, total_messages):
        if cls.task_collection is not None: await cls.task_collection.update_one({'_id': scan_id}, {'$set': {'total_messages': total_messages}})

    @classmethod
    async def update_scan_progress(cls, scan_id, processed_count):
        if cls.task_collection is not None: await cls.task_collection.update_one({'_id': scan_id, 'type': 'active_scan'}, {'$set': {'processed_messages': processed_count}})

    @classmethod
    async def end_scan(cls, scan_id):
        if cls.task_collection is not None: await cls.task_collection.delete_one({'_id': scan_id, 'type': 'active_scan'})

    @classmethod
    async def get_active_scans(cls):
        if cls.task_collection is not None: return await cls.task_collection.find({'type': 'active_scan'}).to_list(length=None)
        return []

    @classmethod
    async def set_scan_flood_wait(cls, scan_id, end_time):
        """Sets a timestamp until which a scan is in flood wait."""
        if cls.task_collection is not None:
            await cls.task_collection.update_one(
                {'_id': scan_id},
                {'$set': {'flood_wait_until': end_time}}
            )

    @classmethod
    async def clear_scan_flood_wait(cls, scan_id):
        """Clears the flood wait status from a scan."""
        if cls.task_collection is not None:
            await cls.task_collection.update_one(
                {'_id': scan_id},
                {'$unset': {'flood_wait_until': ""}}
            )

    @classmethod
    async def clear_all_scans(cls):
        if cls.task_collection is not None: await cls.task_collection.delete_many({'type': 'active_scan'})
