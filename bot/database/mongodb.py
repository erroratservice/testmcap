"""
MongoDB database interface (optional)
"""

from motor.motor_asyncio import AsyncIOMotorClient
from bot.core.config import Config

class MongoDB:
    """MongoDB database manager"""
    
    client = None
    db = None
    collection = None # Using a single collection for all data

    @classmethod
    async def initialize(cls):
        """Initialize database connection"""
        try:
            cls.client = AsyncIOMotorClient(Config.DATABASE_URL)
            cls.db = cls.client.mediaindexbot
            cls.collection = cls.db.mcapindexer # All data will be in this collection
            await cls.client.admin.command('ismaster')
        except Exception:
            raise
    
    @classmethod
    async def close(cls):
        """Close database connection"""
        if cls.client:
            cls.client.close()

    # --- Failed IDs Management ---
    @classmethod
    async def save_failed_ids(cls, channel_id, failed_ids):
        """Save failed IDs as a document in the main collection."""
        if not cls.collection: return
        await cls.collection.update_one(
            {'_id': f"failed_{channel_id}", 'type': 'failed_job'},
            {'$set': {'channel_id': channel_id, 'failed_ids': failed_ids}},
            upsert=True
        )

    @classmethod
    async def get_failed_ids(cls, channel_id):
        """Retrieve failed IDs from the main collection."""
        if not cls.collection: return []
        document = await cls.collection.find_one({'_id': f"failed_{channel_id}", 'type': 'failed_job'})
        return document.get('failed_ids', []) if document else []

    @classmethod
    async def clear_failed_ids(cls, channel_id):
        """Clear the failed IDs document from the main collection."""
        if not cls.collection: return
        await cls.collection.delete_one({'_id': f"failed_{channel_id}", 'type': 'failed_job'})

    # --- Active Scan Tracking ---
    @classmethod
    async def start_scan(cls, scan_id, channel_id, user_id, total_messages, chat_title):
        """Create a new scan document in the main collection."""
        if not cls.collection: return
        await cls.collection.insert_one({
            '_id': scan_id,
            'type': 'active_scan', # Sub-category for this document
            'channel_id': channel_id,
            'user_id': user_id,
            'total_messages': total_messages,
            'processed_messages': 0,
            'chat_title': chat_title
        })

    @classmethod
    async def update_scan_progress(cls, scan_id, processed_count):
        """Update the progress of an active scan document."""
        if not cls.collection: return
        await cls.collection.update_one(
            {'_id': scan_id, 'type': 'active_scan'},
            {'$set': {'processed_messages': processed_count}}
        )

    @classmethod
    async def end_scan(cls, scan_id):
        """Remove a scan document upon completion or cancellation."""
        if not cls.collection: return
        await cls.collection.delete_one({'_id': scan_id, 'type': 'active_scan'})

    @classmethod
    async def get_interrupted_scans(cls):
        """Get all active scan documents from the main collection."""
        if not cls.collection: return []
        cursor = cls.collection.find({'type': 'active_scan'})
        return await cursor.to_list(length=None)

    @classmethod
    async def clear_all_scans(cls):
        """Clear all active scan documents from the main collection."""
        if not cls.collection: return
        await cls.collection.delete_many({'type': 'active_scan'})
