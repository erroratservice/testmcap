"""
Utilities for handling channel message history and caching.
"""
import logging
import asyncio
from bot.core.client import TgClient
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

async def get_history_for_processing(channel_id, force=False):
    """
    Fetches message history for a channel, utilizing a cache of message IDs.
    On the first run, it fetches all messages. On subsequent runs, it only fetches new ones.
    
    :param channel_id: The ID of the target channel.
    :param force: If True, ignores the cache and re-processes all messages.
    :return: A list of message objects to be processed.
    """
    LOGGER.info(f"Fetching history for channel {channel_id}. Force rescan: {force}")
    
    if force:
        await MongoDB.clear_cached_message_ids(channel_id)
        LOGGER.info(f"Cleared message ID cache for channel {channel_id} due to force rescan.")

    # Fetch all message IDs currently in the channel from Telegram
    try:
        all_ids_in_channel = [msg.id async for msg in TgClient.user.get_chat_history(chat_id=channel_id)]
        if not all_ids_in_channel:
            LOGGER.warning(f"No messages found in channel {channel_id}.")
            return []
    except Exception as e:
        LOGGER.error(f"Could not get chat history for {channel_id}: {e}")
        return []

    # Determine which message IDs need to be processed
    if force:
        ids_to_process = all_ids_in_channel
    else:
        cached_ids = await MongoDB.get_cached_message_ids(channel_id)
        ids_to_process = list(set(all_ids_in_channel) - set(cached_ids))

    if not ids_to_process:
        LOGGER.info(f"No new messages to process for channel {channel_id}.")
        return []

    LOGGER.info(f"Found {len(ids_to_process)} messages to process for channel {channel_id}.")

    # Fetch full message objects for the required IDs in batches of 100
    messages_to_process = []
    for i in range(0, len(ids_to_process), 100):
        batch_ids = ids_to_process[i:i+100]
        try:
            # The get_messages method can handle a list of IDs
            messages = await TgClient.user.get_messages(chat_id=channel_id, message_ids=batch_ids)
            messages_to_process.extend(messages)
            await asyncio.sleep(1) # Sleep to avoid hitting API limits
        except Exception as e:
            LOGGER.error(f"Could not get a batch of messages for {channel_id}: {e}")

    # Update the cache with the newly processed message IDs
    if ids_to_process:
        await MongoDB.update_cached_message_ids(channel_id, ids_to_process)
    
    return messages_to_process
