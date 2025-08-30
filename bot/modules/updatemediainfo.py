"""
Update MediaInfo command for enhancing video captions
"""

import asyncio
import logging
from datetime import datetime
from bot.core.client import TgClient
from bot.core.config import Config
from bot.helpers.message_utils import send_message, edit_message
from bot.helpers.file_utils import extract_channel_list, download_media_chunk
from bot.helpers.media_utils import extract_mediainfo

LOGGER = logging.getLogger(__name__)

async def updatemediainfo_handler(client, message):
    """Handler for /updatemediainfo command"""
    try:
        # Parse input
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, 
                "❌ **Usage:**\n"
                "• `/updatemediainfo -1001234567890`\n" 
                "• Reply to file with channel IDs")
            return
        
        # Process each channel
        for channel_id in channels:
            await process_channel_mediainfo(channel_id, message)
            
    except Exception as e:
        LOGGER.error(f"UpdateMediaInfo error: {e}")
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

async def process_channel_mediainfo(channel_id, message):
    """Process MediaInfo updates for a channel"""
    try:
        chat = await TgClient.user.get_chat(channel_id)
        progress_msg = await send_message(message,
            f"🔄 **Processing:** {chat.title}\n"
            f"📊 Extracting MediaInfo and updating captions...")
        
        processed = 0
        errors = 0
        
        async for msg in TgClient.user.get_chat_history(chat_id=channel_id):
            if msg.media and hasattr(msg.media, 'file_name'):
                try:
                    await update_media_caption(msg)
                    processed += 1
                except Exception as e:
                    LOGGER.error(f"Caption update error: {e}")
                    errors += 1
                
                # Update progress every 10 files
                if (processed + errors) % 10 == 0:
                    await edit_message(progress_msg,
                        f"🔄 **Processing:** {chat.title}\n"
                        f"✅ **Updated:** {processed}\n"
                        f"❌ **Errors:** {errors}")
        
        await edit_message(progress_msg,
            f"✅ **Completed:** {chat.title}\n"
            f"📊 **Updated:** {processed} files\n"
            f"❌ **Errors:** {errors} files")
            
    except Exception as e:
        LOGGER.error(f"Channel processing error: {e}")
        await send_message(message, f"❌ Error processing {channel_id}: {e}")

async def update_media_caption(msg):
    """Update individual message caption with MediaInfo"""
    try:
        # Download small chunk for analysis
        temp_file = await download_media_chunk(msg)
        if not temp_file:
            return
        
        # Extract MediaInfo
        media_info = await extract_mediainfo(temp_file)
        
        # Build enhanced caption
        original = msg.caption or ""
        enhanced = build_enhanced_caption(original, media_info)
        
        # Update caption
        await TgClient.user.edit_message_caption(
            chat_id=msg.chat.id,
            message_id=msg.id,
            caption=enhanced
        )
        
    except Exception as e:
        LOGGER.error(f"Caption update failed: {e}")
        raise

def build_enhanced_caption(original, media_info):
    """Build enhanced caption with MediaInfo"""
    # Extract key information
    video_codec = media_info.get('video_codec', 'Unknown')
    resolution = f"{media_info.get('height', 'Unknown')}p"
    audio_count = len(media_info.get('audio_streams', []))
    languages = [stream.get('language', '').upper() for stream in media_info.get('audio_streams', [])]
    
    # Build clean caption
    enhanced = original
    enhanced += f"\n\nVideo: {video_codec} {resolution}"
    enhanced += f"\nAudio: {audio_count}"
    
    if languages:
        enhanced += f" ({', '.join(languages[:3])})"
    
    return enhanced
