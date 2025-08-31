"""
Advanced index files command for organizing channel content.
"""
import logging
import asyncio
from collections import defaultdict
from bot.core.client import TgClient
from bot.core.config import Config
from bot.helpers.message_utils import send_message, send_reply
from bot.helpers.file_utils import extract_channel_list
from bot.helpers.indexing_parser import parse_media_info
from bot.helpers.formatters import format_series_post
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

# Mock data for total episodes per season - in a real bot, this would come from an API like TVDB or TMDB
TOTAL_EPISODES_MAP = {
    "Breaking Bad": {1: 7, 2: 13, 3: 13, 4: 13, 5: 16},
    "Game of Thrones": {1: 10, 2: 10, 3: 10, 4: 10, 5: 10, 6: 10, 7: 7, 8: 6},
    "Byker Grove": {5: 20} # Example for your test case
}

async def indexfiles_handler(client, message):
    """Handler for the new /indexfiles command."""
    try:
        if MongoDB.db is None:
            await send_message(message, "❌ **Error:** Database is not connected.")
            return

        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, "❌ **Usage:** `/indexfiles -100123...`")
            return
        
        channel_id = channels[0]
        
        await send_reply(message, f"✅ **Indexing task started for channel `{channel_id}`.**\n\nI will now scan the channel and create/update posts in the index channel. This may take some time.")
        
        asyncio.create_task(create_channel_index(channel_id, message))
            
    except Exception as e:
        LOGGER.error(f"IndexFiles handler error: {e}")
        await send_message(message, f"❌ **Error:** {e}")

async def create_channel_index(channel_id, message):
    """The main indexing process with a two-phase (scan then update) approach."""
    try:
        chat = await TgClient.user.get_chat(channel_id)
        history_generator = TgClient.user.get_chat_history(chat_id=channel_id)
        
        LOGGER.info(f"Phase 1: Scanning and collecting all media from {chat.title}...")
        
        # --- PHASE 1: Scan and Collect ---
        media_map = defaultdict(list)
        async for msg in history_generator:
            media = msg.video or msg.audio or msg.document
            if not (media and hasattr(media, 'file_name') and media.file_name):
                continue

            parsed = parse_media_info(media.file_name, msg.caption)
            if not parsed:
                continue
            
            # Add file size and message id for later processing
            parsed['file_size'] = media.file_size
            parsed['msg_id'] = msg.id
            media_map[parsed['title']].append(parsed)

        LOGGER.info(f"Phase 1 Complete. Found {len(media_map)} unique titles.")

        # --- PHASE 2: Aggregate and Update ---
        LOGGER.info(f"Phase 2: Aggregating data and updating posts...")
        for title, items in media_map.items():
            for item in items:
                await MongoDB.add_media_entry(item, item['file_size'], item['msg_id'])
            
            # Update the post for this title once with all its collected data
            await update_or_create_post(title, channel_id)

        LOGGER.info(f"✅ Full indexing scan complete for channel {chat.title}.")
        await send_reply(message, f"✅ Indexing task for **{chat.title}** has finished successfully.")

    except Exception as e:
        LOGGER.error(f"Error during indexing for {channel_id}: {e}")
        await send_reply(message, f"❌ An error occurred during the index scan for channel {channel_id}.")

async def update_or_create_post(title, channel_id):
    """Fetches data and updates or creates a post for a given title."""
    try:
        post_doc = await MongoDB.get_or_create_post(title, channel_id)
        media_data = await MongoDB.get_media_data(title)
        
        if not media_data: return

        # Check completeness
        is_complete = True
        if TOTAL_EPISODES_MAP.get(title):
            for season, expected_eps in TOTAL_EPISODES_MAP[title].items():
                if len(media_data.get('seasons', {}).get(str(season), {}).get('episodes', [])) != expected_eps:
                    is_complete = False
                    break
        media_data['is_complete'] = is_complete

        post_text = format_series_post(title, media_data, TOTAL_EPISODES_MAP)

        if len(post_text) > 4096:
            post_text = post_text[:4090] + "\n..." # Truncate if too long

        message_id = post_doc.get('message_id')
        
        if message_id:
            try:
                # Use user client to bypass 48-hour edit limit
                await TgClient.user.edit_message_text(Config.INDEX_CHANNEL_ID, message_id, post_text)
                LOGGER.info(f"Updated post for '{title}'.")
                return
            except Exception:
                # If editing fails (e.g., message deleted), create a new one
                pass
        
        # Create a new post
        new_post = await TgClient.user.send_message(Config.INDEX_CHANNEL_ID, post_text)
        if new_post:
            await MongoDB.update_post_message_id(post_doc['_id'], new_post.id)
            LOGGER.info(f"Created new post for '{title}'.")

    except Exception as e:
        LOGGER.error(f"Failed to update post for '{title}': {e}")


async def get_target_channels(message):
    if message.reply_to_message and message.reply_to_message.document:
        return await extract_channel_list(message.reply_to_message)
    elif len(message.command) > 1:
        try:
            return [int(message.command[1])]
        except ValueError:
            return []
    return []
