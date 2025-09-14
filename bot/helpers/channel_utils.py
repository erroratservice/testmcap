"""
Utilities for handling channel message history with an ID-based batching approach.
"""
import logging
import asyncio
from bot.core.client import TgClient
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

async def stream_messages_by_id_batches(channel_id, force=False):
    """
    Asynchronously yields batches of messages by fetching them in ID ranges using the bot session.
    This is highly efficient and avoids FloodWaits.

    :param channel_id: The ID of the target channel.
    :param force: If True, ignores the cache and re-processes all messages.
    :return: An asynchronous generator that yields lists of message objects.
    """
    LOGGER.info(f"Starting ID-based message stream for channel {channel_id}. Force rescan: {force}")

    if force:
        await MongoDB.clear_cached_message_ids(channel_id)
        LOGGER.info(f"Cleared message ID cache for channel {channel_id} due to force rescan.")

    cached_ids = set(await MongoDB.get_cached_message_ids(channel_id))
    
    try:
        # Use user session once to get the total number of messages reliably.
        total_messages = await TgClient.user.get_chat_history_count(chat_id=channel_id)
        if total_messages == 0:
            LOGGER.info(f"Channel {channel_id} is empty. Nothing to stream.")
            return

        # Start from the latest message ID
        last_message = await anext(TgClient.user.get_chat_history(chat_id=channel_id, limit=1))
        last_id = last_message.id if last_message else total_messages

        current_id = last_id
        
        while current_id > 0:
            # Define the batch of message IDs to fetch (e.g., 100 at a time)
            message_ids = list(range(current_id, max(0, current_id - 100), -1))
            current_id -= 100 # Move to the next batch

            if not message_ids:
                continue
            
            # Filter out IDs that are already cached, unless force scanning
            if not force:
                ids_to_fetch = [msg_id for msg_id in message_ids if msg_id not in cached_ids]
            else:
                ids_to_fetch = message_ids

            if not ids_to_fetch:
                LOGGER.info("Skipping batch as all message IDs are already cached.")
                continue

            try:
                # Use the BOT session for the high-rate get_messages call
                messages = await TgClient.bot.get_messages(chat_id=channel_id, message_ids=ids_to_fetch)
                
                # Filter out empty messages (deleted or service messages)
                valid_messages = [msg for msg in messages if not msg.empty]

                if valid_messages:
                    LOGGER.info(f"Yielding batch of {len(valid_messages)} messages for channel {channel_id}.")
                    yield valid_messages
                    
                    # Cache the successfully processed message IDs
                    ids_to_cache = [msg.id for msg in valid_messages]
                    if ids_to_cache:
                        await MongoDB.update_cached_message_ids(channel_id, ids_to_cache)
                
                # A small sleep between batches to be respectful to the API
                await asyncio.sleep(2)

            except Exception as e:
                LOGGER.error(f"Could not fetch message batch for IDs {ids_to_fetch} in {channel_id}: {e}")
                # Wait a bit longer if an error occurs during a batch fetch
                await asyncio.sleep(10)
                
        LOGGER.info(f"Finished ID-based message stream for channel {channel_id}.")

    except Exception as e:
        LOGGER.error(f"Critical error during message streaming for {channel_id}: {e}", exc_info=True)
