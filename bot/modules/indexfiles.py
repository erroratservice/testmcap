"""
Index files command for organizing channel content
"""

import logging
from collections import defaultdict
from datetime import datetime
from bot.core.client import TgClient
from bot.core.config import Config
from bot.helpers.message_utils import send_message
from bot.helpers.file_utils import extract_channel_list, parse_media_filename

LOGGER = logging.getLogger(__name__)

async def indexfiles_handler(client, message):
    """Handler for /indexfiles command"""
    try:
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message,
                "❌ **Usage:**\n"
                "• `/indexfiles -1001234567890`\n"
                "• Reply to file with channel IDs")
            return
        
        for channel_id in channels:
            await create_channel_index(channel_id, message)
            
    except Exception as e:
        LOGGER.error(f"IndexFiles error: {e}")
        await send_message(message, f"❌ **Error:** {e}")

async def get_target_channels(message):
    """Extract channel IDs from command or file"""
    if message.reply_to_message and message.reply_to_message.document:
        return await extract_channel_list(message.reply_to_message)
    elif len(message.command) > 1:
        try:
            return [int(message.command[1])]
        except ValueError:
            return []
    return []

async def create_channel_index(channel_id, message):
    """Create organized index for channel content"""
    try:
        chat = await TgClient.user.get_chat(channel_id)
        progress_msg = await send_message(message,
            f"📊 **Indexing:** {chat.title}\n"
            f"🔍 Scanning and organizing content...")
        
        content_index = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        file_count = 0
        
        history_generator = TgClient.user.get_chat_history(chat_id=channel_id)
        messages = [msg async for msg in history_generator]
        LOGGER.info(f"Found {len(messages)} messages to index in {chat.title}.")

        for msg in reversed(messages):
            if msg.media and hasattr(msg.media, 'file_name'):
                parsed = parse_media_filename(msg.media.file_name)
                if parsed:
                    add_to_index(content_index, parsed, msg)
                    file_count += 1
        
        if content_index:
            index_text = format_content_index(chat.title, content_index, file_count)
            
            if Config.INDEX_CHANNEL_ID:
                await TgClient.bot.send_message(Config.INDEX_CHANNEL_ID, index_text)
            
            await send_message(message,
                f"✅ **Indexed:** {chat.title}\n"
                f"📊 **Files:** {file_count:,}\n"
                f"🎬 **Titles:** {len(content_index):,}")
        else:
            await send_message(message,
                f"⚠️ No indexable content found in {chat.title}")
            
    except Exception as e:
        LOGGER.error(f"Error indexing {channel_id}: {e}")
        await send_message(message, f"❌ Error indexing {channel_id}: {e}")

# ... (The rest of the functions in this file remain the same)
