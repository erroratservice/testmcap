"""
MediaInfo update with consistent 5MB partial downloads for all files
"""

import asyncio
import logging
import os
import tempfile
from datetime import datetime
from pymediainfo import MediaInfo
from bot.core.client import TgClient
from bot.helpers.message_utils import send_message, edit_message

LOGGER = logging.getLogger(__name__)

async def updatemediainfo_handler(client, message):
    """Handler for /updatemediainfo with consistent 5MB downloads"""
    try:
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, 
                "❌ **Usage:**\n• `/updatemediainfo -1001234567890`\n• Reply to file with channel IDs")
            return
        
        for channel_id in channels:
            await process_channel_with_5mb_downloads(channel_id, message)
            
    except Exception as e:
        LOGGER.error(f"UpdateMediaInfo error: {e}")
        await send_message(message, f"❌ **Error:** {e}")

async def process_channel_with_5mb_downloads(channel_id, message):
    """Process channel with consistent 5MB partial downloads"""
    try:
        # Access channel
        try:
            chat = await TgClient.user.get_chat(channel_id)
            LOGGER.info(f"✅ Processing: {chat.title}")
        except Exception as e:
            await send_message(message, f"❌ Cannot access {channel_id}: {e}")
            return
        
        progress_msg = await send_message(message,
            f"🔄 **Processing:** {chat.title}\n📊 Using 5MB partial downloads for optimal speed...")
        
        processed = 0
        errors = 0
        total_messages = 0
        media_found = 0
        
        # Scan messages for media
        async for msg in TgClient.user.get_chat_history(chat_id=channel_id, limit=1000):
            total_messages += 1
            
            # Check for media
            if await has_processable_media(msg):
                media_found += 1
                
                try:
                    success = await process_message_with_5mb_download(msg)
                    if success:
                        processed += 1
                        LOGGER.info(f"✅ Updated message {msg.id} with MediaInfo")
                    else:
                        LOGGER.info(f"ℹ️ Message {msg.id} already has MediaInfo")
                except Exception as e:
                    LOGGER.error(f"❌ Failed message {msg.id}: {e}")
                    errors += 1
            
            # Progress update every 50 messages
            if total_messages % 50 == 0:
                await edit_message(progress_msg,
                    f"🔄 **Processing:** {chat.title}\n"
                    f"📊 **Messages:** {total_messages} | **Media:** {media_found}\n"
                    f"✅ **Updated:** {processed} | ❌ **Errors:** {errors}")
                await asyncio.sleep(0.1)
        
        # Final result
        await edit_message(progress_msg,
            f"✅ **Completed:** {chat.title}\n"
            f"📊 **Messages Scanned:** {total_messages}\n"
            f"📁 **Media Found:** {media_found}\n"
            f"✅ **Updated:** {processed} files\n"
            f"❌ **Errors:** {errors} files")
            
    except Exception as e:
        LOGGER.error(f"❌ Channel processing error: {e}")
        await send_message(message, f"❌ Error: {e}")

async def has_processable_media(msg):
    """Check for processable media types"""
    return bool(msg.video or msg.audio or 
                (msg.document and msg.document.mime_type and 
                 (msg.document.mime_type.startswith('video/') or 
                  msg.document.mime_type.startswith('audio/'))))

async def process_message_with_5mb_download(msg):
    """Process message with consistent 5MB MediaInfo extraction"""
    try:
        # Skip if already has MediaInfo
        current_caption = msg.caption or ""
        if "Video:" in current_caption and "Audio:" in current_caption:
            return False
        
        # Get media object
        media = msg.video or msg.audio or msg.document
        if not media:
            return False
        
        # Always use 5MB partial download
        temp_file = await download_5mb_partial(msg, media)
        if not temp_file:
            return False
        
        try:
            # Extract MediaInfo from 5MB chunk
            mediainfo_data = extract_mediainfo_from_partial(temp_file)
            if not mediainfo_data:
                return False
            
            # Generate clean caption
            enhanced_caption = generate_clean_mediainfo_caption(current_caption, mediainfo_data)
            
            # Update caption
            await TgClient.user.edit_message_caption(
                chat_id=msg.chat.id,
                message_id=msg.id,
                caption=enhanced_caption
            )
            
            return True
            
        finally:
            # Cleanup temp file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass
        
    except Exception as e:
        LOGGER.error(f"❌ MediaInfo processing failed: {e}")
        return False

async def download_5mb_partial(msg, media):
    """Always download only first 5MB using stream_media - optimized for all file sizes"""
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
            temp_path = temp_file.name
        
        file_size = media.file_size or 0
        file_size_mb = file_size / 1024 / 1024
        
        # Always use partial download (5MB maximum)
        LOGGER.info(f"📥 Downloading 5MB chunk from {file_size_mb:.1f}MB file for MediaInfo")
        
        # Stream first 5MB only (approximately 50 chunks of ~100KB each)
        chunk_count = 0
        max_chunks = 50  # Limit to ~5MB
        
        async for chunk in TgClient.user.stream_media(msg, limit=max_chunks):
            with open(temp_path, "ab") as f:
                f.write(chunk)
            chunk_count += 1
            
            # Safety limit to ensure we don't exceed 5MB
            if chunk_count >= max_chunks:
                break
        
        if chunk_count > 0 and os.path.exists(temp_path):
            downloaded_size = os.path.getsize(temp_path)
            downloaded_mb = downloaded_size / 1024 / 1024
            LOGGER.info(f"📁 Downloaded {downloaded_mb:.1f}MB ({chunk_count} chunks) for analysis")
            return temp_path
        
        return None
        
    except Exception as e:
        LOGGER.error(f"❌ 5MB partial download failed: {e}")
        return None

def extract_mediainfo_from_partial(file_path):
    """Extract MediaInfo from 5MB partial file"""
    try:
        # Parse the partial file with pymediainfo
        media_info = MediaInfo.parse(file_path)
        
        video_info = None
        audio_tracks = []
        
        # Extract video and audio metadata from header
        for track in media_info.tracks:
            if track.track_type == "Video" and not video_info:
                video_info = {
                    'codec': getattr(track, 'codec', 'Unknown') or 'Unknown',
                    'width': getattr(track, 'width', None),
                    'height': getattr(track, 'height', None),
                    'frame_rate': getattr(track, 'frame_rate', None)
                }
            elif track.track_type == "Audio":
                audio_tracks.append({
                    'language': getattr(track, 'language', 'Unknown') or 'Unknown',
                    'codec': getattr(track, 'codec', 'Unknown') or 'Unknown',
                    'channels': getattr(track, 'channel_s', 1),
                    'bit_rate': getattr(track, 'bit_rate', None)
                })
        
        return {
            'video': video_info,
            'audio': audio_tracks
        }
        
    except Exception as e:
        LOGGER.error(f"❌ MediaInfo extraction from partial file failed: {e}")
        return None

def generate_clean_mediainfo_caption(original_caption, mediainfo_data):
    """Generate clean MediaInfo caption like 'Video: H264 1080p\\nAudio: 1 (ENG)'"""
    try:
        # Start with original caption
        enhanced = original_caption.strip() if original_caption else ""
        
        # Build MediaInfo section
        mediainfo_lines = []
        
        # Video information
        video = mediainfo_data.get('video')
        if video:
            codec = video.get('codec', 'Unknown')
            height = video.get('height')
            
            # Convert height to standard resolution labels
            if height:
                if height >= 2160:
                    resolution = "4K"
                elif height >= 1440:
                    resolution = "1440p" 
                elif height >= 1080:
                    resolution = "1080p"
                elif height >= 720:
                    resolution = "720p"
                elif height >= 480:
                    resolution = "480p"
                else:
                    resolution = f"{height}p"
            else:
                resolution = "Unknown"
            
            mediainfo_lines.append(f"Video: {codec} {resolution}")
        
        # Audio information
        audio_tracks = mediainfo_data.get('audio', [])
        if audio_tracks:
            audio_count = len(audio_tracks)
            
            # Extract unique languages
            languages = []
            for audio in audio_tracks:
                lang = audio.get('language', 'Unknown').upper()
                # Clean up language codes
                if lang not in ['UNKNOWN', 'UND', 'UNDEFINED', ''] and lang not in languages:
                    # Convert common language codes
                    if lang in ['EN', 'ENG']:
                        lang = 'ENG'
                    elif lang in ['HI', 'HIN']:
                        lang = 'HIN'
                    languages.append(lang)
            
            # Build audio line
            audio_line = f"Audio: {audio_count}"
            if languages:
                # Show up to 3 languages for clean display
                lang_display = ', '.join(languages[:3])
                audio_line += f" ({lang_display})"
            
            mediainfo_lines.append(audio_line)
        
        # Combine with original caption
        if mediainfo_lines:
            mediainfo_section = "\n\n" + "\n".join(mediainfo_lines)
            enhanced_caption = enhanced + mediainfo_section
            
            # Respect Telegram's 1024 character caption limit
            if len(enhanced_caption) > 1020:
                # Truncate original if needed to fit MediaInfo
                max_original = 1020 - len(mediainfo_section) - 5
                if max_original > 0:
                    enhanced_caption = enhanced[:max_original] + "..." + mediainfo_section
                else:
                    enhanced_caption = mediainfo_section
            
            return enhanced_caption
        
        return enhanced
        
    except Exception as e:
        LOGGER.error(f"❌ Caption generation failed: {e}")
        return original_caption or ""

async def get_target_channels(message):
    """Extract channel IDs from command"""
    if len(message.command) > 1:
        try:
            channel_id = message.command[1]
            if channel_id.startswith('-100'):
                return [int(channel_id)]
            elif channel_id.isdigit():
                return [int(f"-100{channel_id}")]
            else:
                return [channel_id]
        except ValueError:
            return []
    return []
