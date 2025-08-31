"""
Enhanced MediaInfo update with comprehensive logging and message skipping
"""

import asyncio
import logging
import os
import tempfile
from datetime import datetime
from pymediainfo import MediaInfo
from bot.core.client import TgClient
from bot.helpers.message_utils import send_message, edit_message

# Configure detailed logging
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

async def updatemediainfo_handler(client, message):
    """Enhanced handler with comprehensive logging and debugging"""
    try:
        LOGGER.info("🚀 Starting updatemediainfo command")
        
        # Parse input
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, 
                "❌ **Usage:**\n• `/updatemediainfo -1001234567890`\n• Reply to file with channel IDs")
            return
        
        LOGGER.info(f"📋 Processing {len(channels)} channels: {channels}")
        
        # Process each channel with detailed logging
        for i, channel_id in enumerate(channels):
            LOGGER.info(f"🔄 Processing channel {i+1}/{len(channels)}: {channel_id}")
            await process_channel_with_debug_logging(channel_id, message)
            
    except Exception as e:
        LOGGER.error(f"💥 UpdateMediaInfo handler error: {e}", exc_info=True)
        await send_message(message, f"❌ **Fatal Error:** {e}")

async def process_channel_with_debug_logging(channel_id, message):
    """Process channel with extensive debug logging"""
    try:
        # Step 1: Access channel
        LOGGER.info(f"🔍 Step 1: Accessing channel {channel_id}")
        try:
            chat = await TgClient.user.get_chat(channel_id)
            LOGGER.info(f"✅ Successfully accessed: {chat.title} (Type: {chat.type}, ID: {chat.id})")
        except Exception as e:
            LOGGER.error(f"❌ Failed to access channel {channel_id}: {e}")
            await send_message(message, f"❌ **Access Error:** Cannot access {channel_id}\n**Reason:** {str(e)}")
            return
        
        # Step 2: Initialize progress tracking
        LOGGER.info("🔍 Step 2: Initializing progress tracking")
        progress_msg = await send_message(message,
            f"🔄 **Processing:** {chat.title}\n"
            f"📊 **Debug Mode:** Detailed logging enabled\n"
            f"🔍 **Step:** Scanning messages...")
        
        processed = 0
        errors = 0
        skipped_no_media = 0
        skipped_already_processed = 0
        total_messages = 0
        media_found = 0
        
        # Step 3: Scan messages with detailed logging
        LOGGER.info("🔍 Step 3: Starting message scan")
        try:
            message_count = 0
            async for msg in TgClient.user.get_chat_history(chat_id=channel_id, limit=100):  # Limit for testing
                message_count += 1
                total_messages += 1
                
                LOGGER.debug(f"📨 Message {message_count}: ID={msg.id}, Date={msg.date}, Media={bool(msg.media)}")
                
                # Step 3a: Check for media (detailed logging)
                media_check_result = await detailed_media_check(msg)
                LOGGER.debug(f"🔍 Media check for message {msg.id}: {media_check_result}")
                
                if not media_check_result['has_media']:
                    LOGGER.debug(f"⏭️ Skipping message {msg.id}: {media_check_result['reason']}")
                    skipped_no_media += 1
                    continue
                
                # Step 3b: Check if already processed
                if await already_has_mediainfo(msg):
                    LOGGER.debug(f"⏭️ Skipping message {msg.id}: already has MediaInfo")
                    skipped_already_processed += 1
                    continue
                
                media_found += 1
                LOGGER.info(f"🎯 Processing media message {msg.id}: {media_check_result['filename']}")
                
                # Step 3c: Process individual message
                try:
                    success = await process_single_message_with_logging(msg, media_check_result)
                    if success:
                        processed += 1
                        LOGGER.info(f"✅ Successfully updated message {msg.id}")
                    else:
                        LOGGER.warning(f"⚠️ Failed to update message {msg.id}")
                        errors += 1
                except Exception as e:
                    LOGGER.error(f"❌ Error processing message {msg.id}: {e}", exc_info=True)
                    errors += 1
                
                # Step 3d: Progress update every 10 messages
                if message_count % 10 == 0:
                    await edit_message(progress_msg,
                        f"🔄 **Processing:** {chat.title}\n"
                        f"📊 **Messages:** {total_messages} | **Media:** {media_found}\n"
                        f"✅ **Updated:** {processed} | ❌ **Errors:** {errors}\n"
                        f"⏭️ **Skipped:** {skipped_no_media + skipped_already_processed}")
                    
                    LOGGER.info(f"📊 Progress: {message_count} messages processed, {media_found} media found")
                    await asyncio.sleep(0.5)  # Rate limiting
        
        except Exception as e:
            LOGGER.error(f"💥 Message scan error: {e}", exc_info=True)
            await send_message(message, f"❌ **Scan Error:** {str(e)}")
            return
        
        # Step 4: Final results
        LOGGER.info("🔍 Step 4: Generating final results")
        final_stats = (
            f"✅ **Completed:** {chat.title}\n"
            f"📊 **Total Messages:** {total_messages}\n"
            f"📁 **Media Found:** {media_found}\n"
            f"✅ **Updated:** {processed} files\n"
            f"❌ **Errors:** {errors} files\n"
            f"⏭️ **Skipped (No Media):** {skipped_no_media}\n"
            f"⏭️ **Skipped (Already Processed):** {skipped_already_processed}"
        )
        
        await edit_message(progress_msg, final_stats)
        LOGGER.info(f"🎉 Channel processing complete: {processed} updated, {errors} errors")
            
    except Exception as e:
        LOGGER.error(f"💥 Channel processing error: {e}", exc_info=True)
        await send_message(message, f"❌ **Channel Error:** {str(e)}")

async def detailed_media_check(msg):
    """Detailed media checking with comprehensive logging"""
    try:
        LOGGER.debug(f"🔍 Detailed media check for message {msg.id}")
        
        result = {
            'has_media': False,
            'type': None,
            'filename': None,
            'file_size': 0,
            'reason': 'No media detected'
        }
        
        # Check video
        if msg.video:
            result.update({
                'has_media': True,
                'type': 'video',
                'filename': msg.video.file_name or f"video_{msg.id}.mp4",
                'file_size': msg.video.file_size or 0,
                'reason': 'Video file detected'
            })
            LOGGER.debug(f"📹 Video detected: {result['filename']} ({result['file_size']} bytes)")
            return result
        
        # Check audio
        if msg.audio:
            result.update({
                'has_media': True,
                'type': 'audio',
                'filename': msg.audio.file_name or f"audio_{msg.id}.mp3",
                'file_size': msg.audio.file_size or 0,
                'reason': 'Audio file detected'
            })
            LOGGER.debug(f"🎵 Audio detected: {result['filename']} ({result['file_size']} bytes)")
            return result
        
        # Check document
        if msg.document:
            mime_type = msg.document.mime_type or ""
            if (mime_type.startswith('video/') or 
                mime_type.startswith('audio/') or
                msg.document.file_name):
                
                result.update({
                    'has_media': True,
                    'type': 'document',
                    'filename': msg.document.file_name or f"document_{msg.id}",
                    'file_size': msg.document.file_size or 0,
                    'reason': f'Document with media mime type: {mime_type}'
                })
                LOGGER.debug(f"📄 Document detected: {result['filename']} ({mime_type})")
                return result
        
        # No media found
        LOGGER.debug(f"⭕ No media in message {msg.id}: text message or unsupported media type")
        return result
        
    except Exception as e:
        LOGGER.error(f"❌ Media check error for message {msg.id}: {e}")
        return {
            'has_media': False,
            'type': None,
            'filename': None,
            'file_size': 0,
            'reason': f'Error during media check: {e}'
        }

async def already_has_mediainfo(msg):
    """Check if message already has MediaInfo in caption"""
    try:
        caption = msg.caption or ""
        has_info = "Video:" in caption or "Audio:" in caption
        LOGGER.debug(f"📝 Caption check for message {msg.id}: has_mediainfo={has_info}")
        return has_info
    except Exception as e:
        LOGGER.error(f"❌ Caption check error for message {msg.id}: {e}")
        return False

async def process_single_message_with_logging(msg, media_info):
    """Process single message with detailed step logging"""
    temp_file = None
    try:
        LOGGER.info(f"🔄 Processing message {msg.id}: {media_info['filename']}")
        
        # Step A: Download media
        LOGGER.debug(f"📥 Step A: Downloading {media_info['filename']}")
        temp_file = await download_5mb_with_logging(msg, media_info)
        if not temp_file:
            LOGGER.error(f"❌ Download failed for message {msg.id}")
            return False
        
        # Step B: Extract MediaInfo
        LOGGER.debug(f"🔍 Step B: Extracting MediaInfo from {temp_file}")
        mediainfo_data = await extract_mediainfo_with_logging(temp_file)
        if not mediainfo_data:
            LOGGER.error(f"❌ MediaInfo extraction failed for message {msg.id}")
            return False
        
        # Step C: Generate caption
        LOGGER.debug(f"✏️ Step C: Generating enhanced caption")
        current_caption = msg.caption or ""
        enhanced_caption = generate_caption_with_logging(current_caption, mediainfo_data)
        
        # Step D: Update message
        LOGGER.debug(f"📝 Step D: Updating message caption")
        await TgClient.user.edit_message_caption(
            chat_id=msg.chat.id,
            message_id=msg.id,
            caption=enhanced_caption
        )
        
        LOGGER.info(f"✅ Successfully processed message {msg.id}")
        return True
        
    except Exception as e:
        LOGGER.error(f"💥 Processing error for message {msg.id}: {e}", exc_info=True)
        return False
    finally:
        # Cleanup
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
                LOGGER.debug(f"🗑️ Cleaned up temp file: {temp_file}")
            except Exception as e:
                LOGGER.warning(f"⚠️ Cleanup warning: {e}")

async def download_5mb_with_logging(msg, media_info):
    """Download 5MB with comprehensive logging"""
    try:
        LOGGER.debug(f"📥 Starting download: {media_info['filename']} ({media_info['file_size']} bytes)")
        
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
            temp_path = temp_file.name
        
        LOGGER.debug(f"📁 Created temp file: {temp_path}")
        
        # Download first 5MB using stream_media
        chunk_count = 0
        max_chunks = 50  # ~5MB
        total_downloaded = 0
        
        LOGGER.debug(f"📡 Starting stream download (max {max_chunks} chunks)")
        async for chunk in TgClient.user.stream_media(msg, limit=max_chunks):
            with open(temp_path, "ab") as f:
                f.write(chunk)
            chunk_count += 1
            total_downloaded += len(chunk)
            
            if chunk_count >= max_chunks:
                break
        
        if chunk_count > 0 and os.path.exists(temp_path):
            final_size = os.path.getsize(temp_path)
            LOGGER.info(f"✅ Download complete: {final_size/1024/1024:.1f}MB in {chunk_count} chunks")
            return temp_path
        else:
            LOGGER.error(f"❌ Download failed: no chunks received")
            return None
        
    except Exception as e:
        LOGGER.error(f"💥 Download error: {e}", exc_info=True)
        return None

async def extract_mediainfo_with_logging(file_path):
    """Extract MediaInfo with detailed logging"""
    try:
        LOGGER.debug(f"🔍 Parsing MediaInfo from: {file_path}")
        
        # Parse with pymediainfo
        media_info = MediaInfo.parse(file_path)
        LOGGER.debug(f"📊 MediaInfo parsed successfully, {len(media_info.tracks)} tracks found")
        
        video_info = None
        audio_tracks = []
        
        # Extract track information
        for i, track in enumerate(media_info.tracks):
            LOGGER.debug(f"🎬 Track {i}: Type={track.track_type}")
            
            if track.track_type == "Video" and not video_info:
                video_info = {
                    'codec': getattr(track, 'codec', 'Unknown') or 'Unknown',
                    'width': getattr(track, 'width', None),
                    'height': getattr(track, 'height', None),
                    'frame_rate': getattr(track, 'frame_rate', None)
                }
                LOGGER.debug(f"📹 Video track: {video_info}")
                
            elif track.track_type == "Audio":
                audio_track = {
                    'language': getattr(track, 'language', 'Unknown') or 'Unknown',
                    'codec': getattr(track, 'codec', 'Unknown') or 'Unknown',
                    'channels': getattr(track, 'channel_s', 1)
                }
                audio_tracks.append(audio_track)
                LOGGER.debug(f"🎵 Audio track: {audio_track}")
        
        result = {
            'video': video_info,
            'audio': audio_tracks
        }
        
        LOGGER.info(f"✅ MediaInfo extracted: Video={bool(video_info)}, Audio={len(audio_tracks)} tracks")
        return result
        
    except Exception as e:
        LOGGER.error(f"💥 MediaInfo extraction error: {e}", exc_info=True)
        return None

def generate_caption_with_logging(original_caption, mediainfo_data):
    """Generate caption with logging"""
    try:
        LOGGER.debug(f"✏️ Generating caption (original length: {len(original_caption)})")
        
        # Start with original
        enhanced = original_caption.strip() if original_caption else ""
        mediainfo_lines = []
        
        # Video info
        video = mediainfo_data.get('video')
        if video:
            codec = video.get('codec', 'Unknown')
            height = video.get('height')
            
            if height:
                if height >= 2160:
                    resolution = "4K"
                elif height >= 1440:
                    resolution = "1440p" 
                elif height >= 1080:
                    resolution = "1080p"
                elif height >= 720:
                    resolution = "720p"
                else:
                    resolution = f"{height}p"
            else:
                resolution = "Unknown"
            
            video_line = f"Video: {codec} {resolution}"
            mediainfo_lines.append(video_line)
            LOGGER.debug(f"📹 Generated video line: {video_line}")
        
        # Audio info
        audio_tracks = mediainfo_data.get('audio', [])
        if audio_tracks:
            audio_count = len(audio_tracks)
            
            # Get languages
            languages = []
            for audio in audio_tracks:
                lang = audio.get('language', 'Unknown').upper()
                if lang not in ['UNKNOWN', 'UND', ''] and lang not in languages:
                    languages.append(lang)
            
            audio_line = f"Audio: {audio_count}"
            if languages:
                audio_line += f" ({', '.join(languages[:3])})"
            
            mediainfo_lines.append(audio_line)
            LOGGER.debug(f"🎵 Generated audio line: {audio_line}")
        
        # Combine
        if mediainfo_lines:
            mediainfo_section = "\n\n" + "\n".join(mediainfo_lines)
            enhanced_caption = enhanced + mediainfo_section
            
            LOGGER.debug(f"✅ Caption generated (final length: {len(enhanced_caption)})")
            return enhanced_caption
        
        LOGGER.warning("⚠️ No MediaInfo lines generated")
        return enhanced
        
    except Exception as e:
        LOGGER.error(f"💥 Caption generation error: {e}", exc_info=True)
        return original_caption or ""

async def get_target_channels(message):
    """Extract channel IDs with logging"""
    try:
        if len(message.command) > 1:
            channel_id = message.command[1]
            LOGGER.debug(f"📋 Parsing channel ID: {channel_id}")
            
            if channel_id.startswith('-100'):
                result = [int(channel_id)]
            elif channel_id.isdigit():
                result = [int(f"-100{channel_id}")]
            else:
                result = [channel_id]  # Username
            
            LOGGER.info(f"🎯 Target channels: {result}")
            return result
        
        LOGGER.warning("⚠️ No channel specified in command")
        return []
        
    except Exception as e:
        LOGGER.error(f"💥 Channel parsing error: {e}")
        return []
