"""
Index files command for organizing channel content with batched status updates.
"""

import logging
import asyncio
from collections import defaultdict
from datetime import datetime
from bot.core.client import TgClient
from bot.core.config import Config
from bot.helpers.message_utils import send_message, send_reply
from bot.helpers.file_utils import extract_channel_list
from bot.helpers.indexing_parser import parse_media_info
from bot.helpers.formatters import format_series_post
from bot.database.mongodb import MongoDB
from bot.modules.status import trigger_status_creation

LOGGER = logging.getLogger(__name__)

# Mock data for total episodes per season
TOTAL_EPISODES_MAP = {
    "Breaking Bad": {1: 7, 2: 13, 3: 13, 4: 13, 5: 16},
    "Game of Thrones": {1: 10, 2: 10, 3: 10, 4: 10, 5: 10, 6: 10, 7: 7, 8: 6},
    "Byker Grove": {5: 20}
}

async def indexfiles_handler(client, message):
    """Handler for the /indexfiles command."""
    try:
        if MongoDB.db is None:
            await send_message(message, "❌ **Error:** Database is not connected.")
            return

        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, "❌ **Usage:** `/indexfiles -100123...`")
            return
        
        channel_id = channels[0]
        
        await trigger_status_creation(message)
        
        asyncio.create_task(create_channel_index(channel_id, message))
            
    except Exception as e:
        LOGGER.error(f"IndexFiles handler error: {e}")
        await send_message(message, f"❌ **Error:** {e}")

async def create_channel_index(channel_id, message):
    """The main indexing process with live status updates."""
    scan_id = f"index_{channel_id}_{message.id}"
    user_id = message.from_user.id
    
    try:
        chat = await TgClient.user.get_chat(channel_id)
        
        history_generator = TgClient.user.get_chat_history(chat_id=channel_id)
        messages = [msg async for msg in history_generator]
        total_messages = len(messages)
        
        await MongoDB.start_scan(scan_id, channel_id, user_id, total_messages, chat.title, "Indexing Scan")
        
        LOGGER.info(f"Phase 1: Scanning and collecting all media from {chat.title}...")
        
        media_map = defaultdict(list)
        unparsable_count = 0
        skipped_count = 0

        for i, msg in enumerate(reversed(messages)):
            media = msg.video or msg.audio or msg.document
            if media and hasattr(media, 'file_name') and media.file_name:
                parsed = parse_media_info(media.file_name, msg.caption)
                if parsed:
                    parsed['file_size'] = media.file_size
                    parsed['msg_id'] = msg.id
                    media_map[parsed['title']].append(parsed)
                else:
                    unparsable_count += 1
            else:
                skipped_count += 1
            
            # --- MODIFIED: Update progress in batches of 100 for efficiency ---
            if (i + 1) % 100 == 0 or (i + 1) == total_messages:
                await MongoDB.update_scan_progress(scan_id, i + 1)

        LOGGER.info(f"Phase 1 Complete. Found {len(media_map)} unique titles.")
        
        await MongoDB.end_scan(scan_id) # End the "Scanning" phase

        LOGGER.info(f"Phase 2: Aggregating data and updating posts...")
        if media_map:
            for title, items in media_map.items():
                for item in items:
                    await MongoDB.add_media_entry(item, item['file_size'], item['msg_id'])
                await update_or_create_post(title, channel_id)

        LOGGER.info(f"✅ Full indexing scan complete for channel {chat.title}.")
        
        summary_text = (f"✅ **Indexing Task Finished for {chat.title}**\n\n"
                        f"- **Titles Found:** {len(media_map)}\n"
                        f"- **Unparsable Media:** {unparsable_count} files\n"
                        f"- **Skipped Non-Media:** {skipped_count} messages")
        await send_reply(message, summary_text)

    except Exception as e:
        LOGGER.error(f"Error during indexing for {channel_id}: {e}")
        await send_reply(message, f"❌ An error occurred during the index scan for channel {channel_id}.")
    finally:
        await MongoDB.end_scan(scan_id)

async def update_or_create_post(title, channel_id):
    """Fetches data and updates or creates a post for a given title."""
    try:
        post_doc = await MongoDB.get_or_create_post(title, channel_id)
        media_data = await MongoDB.get_media_data(title)
        
        if not media_data: return

        is_complete = True
        if TOTAL_EPISODES_MAP.get(title):
            for season, expected_eps in TOTAL_EPISODES_MAP[title].items():
                if len(media_data.get('seasons', {}).get(str(season), {}).get('episodes', [])) != expected_eps:
                    is_complete = False
                    break
        media_data['is_complete'] = is_complete

        post_text = format_series_post(title, media_data, TOTAL_EPISODES_MAP)

        if len(post_text) > 4096:
            post_text = post_text[:4090] + "\n..."

        message_id = post_doc.get('message_id')
        
        if message_id:
            try:
                await TgClient.user.edit_message_text(Config.INDEX_CHANNEL_ID, message_id, post_text)
                LOGGER.info(f"Updated post for '{title}'.")
                return
            except Exception:
                pass
        
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
