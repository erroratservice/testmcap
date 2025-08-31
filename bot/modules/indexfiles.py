"""
Index files command for organizing channel content
"""

import logging
import asyncio
from collections import defaultdict
from datetime import datetime
from bot.core.client import TgClient
from bot.core.config import Config
from bot.helpers.message_utils import send_message
from bot.helpers.file_utils import extract_channel_list, parse_media_filename
from bot.database.mongodb import MongoDB
from bot.modules.status import trigger_status_creation

LOGGER = logging.getLogger(__name__)

async def indexfiles_handler(client, message):
    """Handler for /indexfiles command"""
    try:
        if MongoDB.db is None:
            await send_message(message, "❌ **Error:** Database is not connected. This feature is disabled.")
            return

        channels = await get_target_channels(message)
        if not channels:
            await send_message(message,
                "❌ **Usage:**\n"
                "• `/indexfiles -1001234567890`\n"
                "• Reply to file with channel IDs")
            return
        
        channel_id = channels[0]
        
        # Directly create the status message instead of a confirmation
        await trigger_status_creation(message)
        
        asyncio.create_task(create_channel_index(channel_id, message))
            
    except Exception as e:
        LOGGER.error(f"IndexFiles handler error: {e}")
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
    scan_id = f"index_{channel_id}_{message.id}"
    user_id = message.from_user.id
    
    try:
        chat = await TgClient.user.get_chat(channel_id)
        
        history_generator = TgClient.user.get_chat_history(chat_id=channel_id)
        messages = [msg async for msg in history_generator]
        total_messages = len(messages)
        LOGGER.info(f"Found {total_messages} messages to index in {chat.title}.")
        
        await MongoDB.start_scan(scan_id, channel_id, user_id, total_messages, chat.title, "Indexing")

        content_index = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        file_count = 0

        for i, msg in enumerate(reversed(messages)):
            if msg.media and hasattr(msg.media, 'file_name'):
                parsed = parse_media_filename(msg.media.file_name)
                if parsed:
                    add_to_index(content_index, parsed, msg)
                    file_count += 1

            await MongoDB.update_scan_progress(scan_id, i + 1)
        
        if content_index:
            index_text = format_content_index(chat.title, content_index, file_count)
            
            if Config.INDEX_CHANNEL_ID:
                await TgClient.bot.send_message(Config.INDEX_CHANNEL_ID, index_text)
                await send_message(message, f"✅ **Index for {chat.title} created successfully** and posted to the index channel.")
            else:
                 await send_message(message, f"✅ **Index for {chat.title} created successfully**.\n(Index channel not configured, so not posted anywhere).")
        else:
            await send_message(message, f"⚠️ No indexable content found in {chat.title}")
            
    except Exception as e:
        LOGGER.error(f"Error indexing {channel_id}: {e}")
        await send_message(message, f"❌ Error indexing {channel_id}: {e}")
    finally:
        await MongoDB.end_scan(scan_id)

def add_to_index(content_index, parsed, message):
    """Add parsed content to index structure"""
    title = parsed['title']
    
    if parsed['type'] == 'series':
        season = parsed['season']
        episode = parsed['episode']
        content_index[title][season][episode].append({
            'quality': parsed['quality'],
            'codec': parsed['codec'],
            'size': format_file_size(message.media.file_size),
            'message_id': message.id
        })
    else:  # movie
        content_index[title][parsed['year']]['movie'].append({
            'quality': parsed['quality'],
            'codec': parsed['codec'],
            'size': format_file_size(message.media.file_size),
            'message_id': message.id
        })

def format_content_index(channel_name, content_index, total_files):
    """Format organized content index"""
    lines = [
        f"📺 **{channel_name} - Content Index**",
        f"📅 **Generated:** {datetime.now().strftime('%d/%m/%Y %H:%M IST')}",
        f"📁 **Total Files:** {total_files:,}",
        f"🎬 **Total Titles:** {len(content_index)}",
        "━━━━━━━━━━━━━━━━━━━━",
        ""
    ]
    
    for title, content in sorted(content_index.items()):
        lines.append(f"🎬 **{title}**")
        
        if any(isinstance(k, int) and k > 1900 for k in content.keys()):
            for year, data in content.items():
                if 'movie' in data:
                    qualities = " | ".join(f"{q['quality']} ({q['codec']})" for q in data['movie'])
                    lines.append(f"🎞️ **{year}**: {qualities}")
        else:
            for season, episodes in sorted(content.items()):
                lines.append(f"📺 **Season {season}**")
                for episode, data in sorted(episodes.items()):
                    qualities = " | ".join(f"{q['quality']} ({q['codec']})" for q in data)
                    lines.append(f"└── Episode {episode}: {qualities}")
        
        lines.append("")
    
    return "\n".join(lines)

def format_file_size(bytes_size):
    """Convert bytes to human readable size"""
    if not isinstance(bytes_size, (int, float)):
        return "0B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}PB"
