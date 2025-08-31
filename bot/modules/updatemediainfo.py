"""
Enhanced MediaInfo update with fixed extraction and safe caption editing
"""

import asyncio
import logging
import os
import tempfile
from datetime import datetime
from pymediainfo import MediaInfo
from pyrogram.errors import MessageNotModified
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
            f"📊 **Debug Mode:** Enhanced MediaInfo extraction\n"
            f"🔍 **Step:** Scanning messages...")
        
        processed = 0
        errors = 0
        skipped_no_media = 0
        skipped_already_processed = 0
        skipped_no_change = 0
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
                    result = await process_single_message_with_logging(msg, media_check_result)
                    if result == "success":
                        processed += 1
                        LOGGER.info(f"✅ Successfully updated message {msg.id}")
                    elif result == "no_change":
                        skipped_no_change += 1
                        LOGGER.info(f"ℹ️ No changes needed for message {msg.id}")
                    else:
                        errors += 1
                        LOGGER.warning(f"⚠️ Failed to update message {msg.id}")
                except Exception as e:
                    LOGGER.error(f"❌ Error processing message {msg.id}: {e}", exc_info=True)
                    errors += 1
                
                # Step 3d: Progress update every 10 messages
                if message_count % 10 == 0:
                    await edit_message(progress_msg,
                        f"🔄 **Processing:** {chat.title}\n"
                        f"📊 **Messages:** {total_messages} | **Media:** {media_found}\n"
                        f"✅ **Updated:** {processed} | ❌ **Errors:** {errors}\n"
                        f"ℹ️ **No Changes:** {skipped_no_change}\n"
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
            f"ℹ️ **No Changes:** {skipped_no_change} files\n"
            f"⏭️ **Skipped (No Media):** {skipped_no_media}\n"
            f"⏭️ **Skipped (Already Processed):** {skipped_already_processed}"
        )
        
        await edit_message(progress_msg, final_stats)
        LOGGER.info(f"🎉 Channel processing complete: {processed} updated, {errors} errors, {skipped_no_change} unchanged")
            
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
        
        # Check animation
        if msg.animation:
            result.update({
                'has_media': True,
                'type': 'animation',
                'filename': msg.animation.file_name or f"animation_{msg.id}.gif",
                'file_size': msg.animation.file_size or 0,
                'reason': 'Animation file detected'
            })
            LOGGER.debug(f"🎬 Animation detected: {result['filename']}")
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
        has_info = "Video:" in caption and "Audio:" in caption
        LOGGER.debug(f"📝 Caption check for message {msg.id}: has_mediainfo={has_info}")
        return has_info
    except Exception as e:
        LOGGER.error(f"❌ Caption check error for message {msg.id}: {e}")
        return False

async def process_single_message_with_logging(msg, media_info):
    """Process single message with proper MediaInfo extraction and safe caption editing"""
    temp_file = None
    try:
        LOGGER.info(f"🔄 Processing message {msg.id}: {media_info['filename']}")
        
        # Step A: Download media
        LOGGER.debug(f"📥 Step A: Downloading {media_info['filename']}")
        temp_file = await download_5mb_with_logging(msg, media_info)
        if not temp_file:
            LOGGER.error(f"❌ Download failed for message {msg.id}")
            return "error"
        
        # Step B: Extract MediaInfo with improved parsing
        LOGGER.debug(f"🔍 Step B: Extracting MediaInfo from {temp_file}")
        mediainfo_data = await extract_mediainfo_improved(temp_file)
        if not mediainfo_data or not mediainfo_data.get('has_content'):
            LOGGER.warning(f"⚠️ No useful MediaInfo extracted for message {msg.id}")
            return "error"
        
        # Step C: Generate caption
        LOGGER.debug(f"✏️ Step C: Generating enhanced caption")
        current_caption = msg.caption or ""
        enhanced_caption = generate_caption_with_logging(current_caption, mediainfo_data)
        
        # Step D: Safe caption update with change detection
        LOGGER.debug(f"📝 Step D: Safe caption update")
        result = await safe_edit_caption(msg, current_caption, enhanced_caption)
        
        if result:
            LOGGER.info(f"✅ Successfully processed message {msg.id}")
            return "success"
        else:
            LOGGER.info(f"ℹ️ No changes made to message {msg.id}")
            return "no_change"
        
    except Exception as e:
        LOGGER.error(f"💥 Processing error for message {msg.id}: {e}", exc_info=True)
        return "error"
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

async def extract_mediainfo_improved(file_path):
    """Improved MediaInfo extraction with better track detection"""
    try:
        LOGGER.debug(f"🔍 Parsing MediaInfo from: {file_path}")
        
        # Parse with pymediainfo
        media_info = MediaInfo.parse(file_path)
        LOGGER.debug(f"📊 MediaInfo parsed, {len(media_info.tracks)} tracks found")
        
        video_info = None
        audio_tracks = []
        
        # Enhanced track parsing with detailed logging
        for i, track in enumerate(media_info.tracks):
            track_type = getattr(track, 'track_type', 'Unknown')
            LOGGER.debug(f"🎬 Track {i}: Type={track_type}")
            
            if track_type == "Video" and not video_info:
                # Extract video information
                codec = getattr(track, 'codec', None) or getattr(track, 'format', None) or 'Unknown'
                width = getattr(track, 'width', None)
                height = getattr(track, 'height', None) 
                frame_rate = getattr(track, 'frame_rate', None)
                
                video_info = {
                    'codec': codec,
                    'width': width,
                    'height': height,
                    'frame_rate': frame_rate
                }
                LOGGER.debug(f"📹 Video track found: {video_info}")
                
            elif track_type == "Audio":
                # Extract audio information
                language = getattr(track, 'language', None) or 'Unknown'
                codec = getattr(track, 'codec', None) or getattr(track, 'format', None) or 'Unknown'
                channels = getattr(track, 'channel_s', None) or getattr(track, 'channels', None) or 1
                
                audio_track = {
                    'language': language,
                    'codec': codec,
                    'channels': channels
                }
                audio_tracks.append(audio_track)
                LOGGER.debug(f"🎵 Audio track found: {audio_track}")
            
            elif track_type == "General":
                # Sometimes video info is in General track for certain formats
                if not video_info:
                    codec = (getattr(track, 'video_format_list', None) or 
                            getattr(track, 'video_codecs', None) or
                            getattr(track, 'format', None))
                    width = getattr(track, 'width', None)
                    height = getattr(track, 'height', None)
                    
                    if codec and codec != 'Unknown':
                        video_info = {
                            'codec': codec,
                            'width': width,
                            'height': height,
                            'frame_rate': None
                        }
                        LOGGER.debug(f"📹 Video info from General track: {video_info}")
                
                # Check for audio info in General track
                audio_count = (getattr(track, 'audio_count', None) or 
                              getattr(track, 'count_of_audio_streams', None))
                if audio_count and not audio_tracks:
                    try:
                        # Create placeholder audio tracks
                        for i in range(int(audio_count)):
                            audio_tracks.append({
                                'language': 'Unknown',
                                'codec': 'Unknown', 
                                'channels': 1
                            })
                        LOGGER.debug(f"🎵 Audio tracks from General: {audio_count}")
                    except (ValueError, TypeError):
                        pass
        
        # Determine if we have useful content
        has_content = bool(video_info and video_info.get('codec') != 'Unknown') or bool(audio_tracks)
        
        result = {
            'video': video_info,
            'audio': audio_tracks,
            'has_content': has_content
        }
        
        LOGGER.info(f"✅ MediaInfo extracted: Video={bool(video_info)}, Audio={len(audio_tracks)} tracks, HasContent={has_content}")
        return result
        
    except Exception as e:
        LOGGER.error(f"💥 MediaInfo extraction error: {e}", exc_info=True)
        return None

async def safe_edit_caption(msg, current_caption, new_caption):
    """Safely edit caption with change detection and error handling"""
    try:
        # Check if caption actually changed
        if current_caption == new_caption:
            LOGGER.info(f"ℹ️ Message {msg.id}: Caption unchanged, skipping edit")
            return False
        
        # Check if new caption has meaningful content
        current_clean = (current_caption or "").strip()
        new_clean = (new_caption or "").strip()
        
        if new_clean == current_clean:
            LOGGER.info(f"ℹ️ Message {msg.id}: No meaningful caption changes")
            return False
        
        # Check if new caption actually adds MediaInfo
        if "Video:" not in new_caption and "Audio:" not in new_caption:
            LOGGER.info(f"ℹ️ Message {msg.id}: No MediaInfo content to add")
            return False
        
        # Attempt to edit caption
        try:
            await TgClient.user.edit_message_caption(
                chat_id=msg.chat.id,
                message_id=msg.id,
                caption=new_caption
            )
            LOGGER.info(f"✅ Caption successfully updated for message {msg.id}")
            return True
            
        except MessageNotModified:
            LOGGER.info(f"ℹ️ Message {msg.id}: Telegram says content unchanged")
            return False
            
    except Exception as e:
        LOGGER.error(f"❌ Caption edit error for message {msg.id}: {e}")
        return False

def generate_caption_with_logging(original_caption, mediainfo_data):
    """Generate caption with enhanced MediaInfo data"""
    try:
        if not mediainfo_data or not mediainfo_data.get('has_content'):
            LOGGER.warning("⚠️ No MediaInfo content to generate caption")
            return original_caption or ""
            
        LOGGER.debug(f"✏️ Generating caption (original length: {len(original_caption)})")
        
        # Start with original
        enhanced = original_caption.strip() if original_caption else ""
        mediainfo_lines = []
        
        # Video information
        video = mediainfo_data.get('video')
        if video and video.get('codec') and video.get('codec') != 'Unknown':
            codec = video.get('codec', 'Unknown')
            height = video.get('height')
            
            # Determine resolution
            if height:
                try:
                    height = int(height)
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
                except (ValueError, TypeError):
                    resolution = ""
            else:
                resolution = ""
            
            # Build video line
            video_line = f"Video: {codec}"
            if resolution:
                video_line += f" {resolution}"
            
            mediainfo_lines.append(video_line)
            LOGGER.debug(f"📹 Generated video line: {video_line}")
        
        # Audio information
        audio_tracks = mediainfo_data.get('audio', [])
        if audio_tracks:
            audio_count = len(audio_tracks)
            
            # Extract languages
            languages = []
            for audio in audio_tracks:
                lang = audio.get('language', 'Unknown').upper()
                # Clean language codes
                if lang and lang not in ['UNKNOWN', 'UND', 'UNDEFINED', '']:
                    # Standardize common language codes
                    if lang in ['EN', 'ENG', 'ENGLISH']:
                        lang = 'ENG'
                    elif lang in ['HI', 'HIN', 'HINDI']:
                        lang = 'HIN'
                    elif lang in ['ES', 'SPA', 'SPANISH']:
                        lang = 'SPA'
                    elif lang in ['FR', 'FRA', 'FRENCH']:
                        lang = 'FRA'
                    
                    if lang not in languages:
                        languages.append(lang)
            
            # Build audio line
            audio_line = f"Audio: {audio_count}"
            if languages:
                audio_line += f" ({', '.join(languages[:3])})"
            
            mediainfo_lines.append(audio_line)
            LOGGER.debug(f"🎵 Generated audio line: {audio_line}")
        
        # Combine with original caption
        if mediainfo_lines:
            mediainfo_section = "\n\n" + "\n".join(mediainfo_lines)
            enhanced_caption = enhanced + mediainfo_section
            
            # Respect Telegram's caption limit (1024 characters)
            if len(enhanced_caption) > 1020:
                max_original = 1020 - len(mediainfo_section) - 5
                if max_original > 0:
                    enhanced_caption = enhanced[:max_original] + "..." + mediainfo_section
                else:
                    enhanced_caption = mediainfo_section
            
            LOGGER.debug(f"✅ Caption generated (final length: {len(enhanced_caption)})")
            return enhanced_caption
        
        LOGGER.warning("⚠️ No MediaInfo lines generated - returning original")
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
