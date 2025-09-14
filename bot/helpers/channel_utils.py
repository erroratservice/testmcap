"""
Utilities for handling channel message history and caching with a streaming approach.
"""
import logging
import asyncio
from bot.core.client import TgClient
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

async def stream_history_for_processing(channel_id, force=False):
    """
    Asynchronously yields batches of new messages from a channel's history.
    This combines a streaming approach with database caching to process only new messages
    since the last scan, while avoiding high memory usage and rate limits.

    :param channel_id: The ID of the target channel.
    :param force: If True, ignores the cache and re-processes all messages.
    :return: An asynchronous generator that yields lists of message objects.
    """
    LOGGER.info(f"Streaming history for channel {channel_id}. Force rescan: {force}")

    if force:
        await MongoDB.clear_cached_message_ids(channel_id)
        LOGGER.info(f"Cleared message ID cache for channel {channel_id} due to force rescan.")

    cached_ids = set(await MongoDB.get_cached_message_ids(channel_id))
    
    batch = []
    ids_to_cache = []
    
    try:
        total_messages_processed = 0
        async for message in TgClient.bot.get_chat_history(chat_id=channel_id):
            total_messages_processed += 1
            if not force and message.id in cached_ids:
                continue

            batch.append(message)
            ids_to_cache.append(message.id)

            # Yield a batch when it reaches 100 messages
            if len(batch) == 100:
                LOGGER.info(f"Yielding batch of {len(batch)} messages for channel {channel_id}.")
                yield batch
                await MongoDB.update_cached_message_ids(channel_id, ids_to_cache)
                batch, ids_to_cache = [], []
                await asyncio.sleep(2) # A small sleep between batches to respect rate limits

        # Yield any remaining messages in the last batch
        if batch:
            LOGGER.info(f"Yielding final batch of {len(batch)} messages for channel {channel_id}.")
            yield batch
            await MongoDB.update_cached_message_ids(channel_id, ids_to_cache)
            
        LOGGER.info(f"Finished streaming history for channel {channel_id}. Scanned {total_messages_processed} total messages.")

    except Exception as e:
        LOGGER.error(f"Could not stream chat history for {channel_id}: {e}", exc_info=True)
        # Still yield any messages collected before an error
        if batch:
            yield batch
