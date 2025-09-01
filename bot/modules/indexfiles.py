"""
Advanced index files command with a batched processing system for split files and episode ranges.
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
from bot.modules.status import trigger_status_creation
from bot.core.tasks import ACTIVE_TASKS

LOGGER = logging.getLogger(__name__)

# Mock data for total episodes per season
TOTAL_EPISODES_MAP = {}
BATCH_SIZE = 100

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
        
        scan_id = f"index_{channel_id}_{message.id}"
        task = asyncio.create_task(create_channel_index(channel_id, message, scan_id))
        ACTIVE_TASKS[scan_id] = task
            
    except Exception as e:
        LOGGER.error(f"IndexFiles handler error: {e}")
        await send_message(message, f"❌ **Error:** {e}")

async def create_channel_index(channel_id, message, scan_id):
    """The main indexing process with split file handling."""
    user_id = message.from_user.id
    chat = None
    
    try:
        chat = await TgClient.user.get_chat(channel_id)
        
        await MongoDB.start_scan(scan_id, channel_id, user_id, 0, chat.title, "Indexing Scan")
        
        history_generator = TgClient.user.get_chat_history(chat_id=channel_id)
        messages = [msg async for msg in history_generator]
        total_messages = len(messages)
        
        await MongoDB.update_scan_total(scan_id, total_messages)
        
        LOGGER.info(f"Pre-processing {total_messages} messages to group split files...")
        
        message_groups = defaultdict(list)
        unparsable_count = 0
        skipped_count = 0
        
        base_name_map = {}
        for msg in messages:
            media = msg.video or msg.document
            if media and hasattr(media, 'file_name') and media.file_name:
                parsed_temp = parse_media_info(media.file_name)
                if parsed_temp and parsed_temp.get('is_split'):
                    base_name = parsed_temp['base_name']
                    if base_name not in base_name_map:
                        base_name_map[base_name] = []
                    base_name_map[base_name].append(msg)
                else:
                    message_groups[msg.id] = [msg]
            else:
                skipped_count += 1

        for base_name, parts in base_name_map.items():
            first_message = min(parts, key=lambda x: x.id)
            message_groups[first_message.id] = parts

        LOGGER.info(f"Finished grouping. Found {len(message_groups)} unique media items.")
        
        media_map = defaultdict(list)
        
        sorted_groups = sorted(message_groups.values(), key=lambda x: x[0].id)

        for i, msg_group in enumerate(sorted_groups):
            first_msg = msg_group[0]
            media = first_msg.video or first_msg.document

            if media and hasattr(media, 'file_name') and media.file_name:
                parsed = parse_media_info(media.file_name, first_msg.caption)
                if parsed:
                    total_size = sum(part.document.file_size for part in msg_group if part.document)
                    parsed['file_size'] = total_size
                    parsed['msg_id'] = first_msg.id
                    media_map[parsed['title']].append(parsed)
                else:
                    unparsable_count += 1
                    # --- MODIFIED: Log the filename that failed to parse ---
                    LOGGER.warning(f"Could not parse filename: {media.file_name}")
            
            if (i + 1) % BATCH_SIZE == 0 or (i + 1) == len(sorted_groups):
                LOGGER.info(f"Processing batch of {len(media_map)} titles...")
                await process_batch(media_map, channel_id)
                media_map.clear()
                
                if (i + 1) < len(sorted_groups):
                    LOGGER.info(f"Batch complete. Waiting for 10 seconds...")
                    await asyncio.sleep(10)
            
            await MongoDB.update_scan_progress(scan_id, i + 1)

        LOGGER.info(f"✅ Full indexing scan complete for channel {chat.title}.")
        
        summary_text = (f"✅ **Indexing Task Finished for {chat.title}**\n\n"
                        f"- **Unparsable Media:** {unparsable_count} files\n"
                        f"- **Skipped Non-Media:** {skipped_count} messages")
        await send_reply(message, summary_text)

    except asyncio.CancelledError:
        LOGGER.warning(f"Indexing task {scan_id} was cancelled by user.")
        await send_reply(message, f"❌ Indexing for **{chat.title if chat else 'Unknown'}** was cancelled.")
    except Exception as e:
        LOGGER.error(f"Error during indexing for {channel_id}: {e}", exc_info=True)
        await send_reply(message, f"❌ An error occurred during the index scan for channel {channel_id}.")
    finally:
        await MongoDB.end_scan(scan_id)
        ACTIVE_TASKS.pop(scan_id, None)

async def process_batch(media_map, channel_id):
    """Aggregates and updates posts for a batch of collected media."""
    for title, items in media_map.items():
        for item in items:
            for episode_num in item['episodes']:
                item_copy = item.copy()
                item_copy['episode'] = episode_num
                await MongoDB.add_media_entry(item_copy, item['file_size'], item['msg_id'])
        await update_or_create_post(title, channel_id)

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
