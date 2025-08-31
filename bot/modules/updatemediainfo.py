"""
Enhanced MediaInfo update with comprehensive media detection
"""

import asyncio
import logging
from datetime import datetime
from bot.core.client import TgClient
from bot.core.config import Config
from bot.helpers.message_utils import send_message, edit_message

LOGGER = logging.getLogger(__name__)

async def updatemediainfo_handler(client, message):
    """Enhanced handler for /updatemediainfo command with better media detection"""
    try:
        # Parse input
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, 
                "❌ **Usage:**\n"
                "• `/updatemediainfo -1001234567890`\n" 
                "• Reply to file with channel IDs")
            return
        
        # Process each channel with enhanced detection
        for channel_id in channels:
            await process_channel_mediainfo_enhanced(channel_id, message)
            
    except Exception as e:
        LOGGER.error(f"UpdateMediaInfo error: {e}")
        await send_message(message, f"❌ **Error:** {e}")

async def get_target_channels(message):
    """Extract channel IDs from command or file"""
    if message.reply_to_message and message.reply_to_message.document:
        return await extract_channel_list(message.reply_to_message)
    elif len(message.command) > 1:
        try:
            channel_id = message.command[1]
            # Handle both with and without -100 prefix
            if channel_id.startswith('-100'):
                return [int(channel_id)]
            elif channel_id.isdigit():
                return [int(f"-100{channel_id}")]
            else:
                return [channel_id]  # Username
        except ValueError:
            return []
    return []

async def process_channel_mediainfo_enhanced(channel_id, message):
    """Enhanced media processing with comprehensive detection"""
    try:
        # Get chat info with error handling
        try:
            chat = await TgClient.user.get_chat(channel_id)
            LOGGER.info(f"✅ Successfully accessed chat: {chat.title} ({chat.type})")
        except Exception as e:
            await send_message(message, f"❌ **Access Error:** Cannot access channel {channel_id}\n**Reason:** {str(e)}")
            return
        
        progress_msg = await send_message(message,
            f"🔄 **Scanning:** {chat.title}\n"
            f"📊 **Type:** {chat.type}\n"
            f"🔍 Looking for media files...")
        
        processed = 0
        errors = 0
        total_messages = 0
        media_found = 0
        
        # Enhanced message scanning with detailed logging
        try:
            async for msg in TgClient.user.get_chat_history(chat_id=channel_id, limit=1000):
                total_messages += 1
                
                # Comprehensive media detection
                media_info = detect_media_comprehensive(msg)
                
                if media_info['has_media']:
                    media_found += 1
                    LOGGER.info(f"📁 Found media: {media_info['filename']} ({media_info['type']})")
                    
                    try:
                        await update_media_caption_enhanced(msg, media_info)
                        processed += 1
                        LOGGER.info(f"✅ Updated: {media_info['filename']}")
                    except Exception as e:
                        LOGGER.error(f"❌ Failed to update {media_info['filename']}: {e}")
                        errors += 1
                
                # Update progress every 50 messages
                if total_messages % 50 == 0:
                    await edit_message(progress_msg,
                        f"🔄 **Scanning:** {chat.title}\n"
                        f"📊 **Messages:** {total_messages}\n"
                        f"📁 **Media Found:** {media_found}\n"
                        f"✅ **Updated:** {processed}\n"
                        f"❌ **Errors:** {errors}")
                    
                    # Add delay to avoid rate limits
                    await asyncio.sleep(0.1)
        
        except Exception as e:
            LOGGER.error(f"❌ History scan error: {e}")
            await send_message(message, f"❌ **Scan Error:** {str(e)}")
            return
        
        # Final result
        await edit_message(progress_msg,
            f"✅ **Completed:** {chat.title}\n"
            f"📊 **Total Messages:** {total_messages}\n"
            f"📁 **Media Found:** {media_found}\n"
            f"✅ **Updated:** {processed}\n"
            f"❌ **Errors:** {errors}")
            
    except Exception as e:
        LOGGER.error(f"❌ Channel processing error: {e}")
        await send_message(message, f"❌ **Error processing {channel_id}:** {str(e)}")

def detect_media_comprehensive(msg):
    """Comprehensive media detection for all types"""
    media_info = {
        'has_media': False,
        'type': None,
        'filename': None,
        'file_size': 0,
        'mime_type': None
    }
    
    try:
        # Check for video
        if msg.video:
            media_info.update({
                'has_media': True,
                'type': 'video',
                'filename': msg.video.file_name or f"video_{msg.id}.mp4",
                'file_size': msg.video.file_size,
                'mime_type': msg.video.mime_type
            })
            return media_info
        
        # Check for audio
        if msg.audio:
            media_info.update({
                'has_media': True,
                'type': 'audio', 
                'filename': msg.audio.file_name or f"audio_{msg.id}.mp3",
                'file_size': msg.audio.file_size,
                'mime_type': msg.audio.mime_type
            })
            return media_info
        
        # Check for document (includes various file types)
        if msg.document:
            # Filter for video/audio documents
            mime_type = msg.document.mime_type or ""
            if (mime_type.startswith('video/') or 
                mime_type.startswith('audio/') or
                msg.document.file_name):
                
                media_info.update({
                    'has_media': True,
                    'type': 'document',
                    'filename': msg.document.file_name or f"document_{msg.id}",
                    'file_size': msg.document.file_size,
                    'mime_type': mime_type
                })
                return media_info
        
        # Check for animation (GIFs, etc.)
        if msg.animation:
            media_info.update({
                'has_media': True,
                'type': 'animation',
                'filename': msg.animation.file_name or f"animation_{msg.id}.gif",
                'file_size': msg.animation.file_size,
                'mime_type': msg.animation.mime_type
            })
            return media_info
            
    except Exception as e:
        LOGGER.error(f"❌ Media detection error for message {msg.id}: {e}")
    
    return media_info

async def update_media_caption_enhanced(msg, media_info):
    """Update message caption with enhanced MediaInfo"""
    try:
        # For now, just add basic info (you can enhance with actual MediaInfo extraction later)
        original_caption = msg.caption or ""
        
        # Create enhanced caption
        enhanced_caption = original_caption
        
        if not original_caption.endswith(f"\n\n📁 **File:** {media_info['filename']}"):
            enhanced_caption += f"\n\n📁 **File:** {media_info['filename']}"
            enhanced_caption += f"\n📊 **Type:** {media_info['type'].title()}"
            enhanced_caption += f"\n💾 **Size:** {format_file_size(media_info['file_size'])}"
            
            if media_info['mime_type']:
                enhanced_caption += f"\n🔧 **Format:** {media_info['mime_type']}"
        
        # Update caption
        await TgClient.user.edit_message_caption(
            chat_id=msg.chat.id,
            message_id=msg.id,
            caption=enhanced_caption
        )
        
    except Exception as e:
        LOGGER.error(f"❌ Caption update failed for {media_info['filename']}: {e}")
        raise

def format_file_size(bytes_size):
    """Convert bytes to human readable size"""
    if not bytes_size:
        return "Unknown"
        
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"

async def extract_channel_list(reply_message):
    """Extract channel IDs from text file"""
    try:
        if reply_message.document:
            file_path = await reply_message.download(in_memory=True)
            content = file_path.getvalue().decode('utf-8')
        else:
            content = reply_message.text or ""
        
        channels = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith('-100') and line.lstrip('-').isdigit():
                channels.append(int(line))
            elif line.isdigit():
                channels.append(int(f"-100{line}"))
        
        return channels
    except Exception as e:
        LOGGER.error(f"❌ Channel list extraction error: {e}")
        return []
