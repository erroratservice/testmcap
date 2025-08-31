"""
Enhanced MediaInfo update with FFprobe and intelligent fallback system
"""

import asyncio
import logging
import os
import tempfile
import json
from datetime import datetime
from pyrogram.errors import MessageNotModified
from bot.core.client import TgClient
from bot.helpers.message_utils import send_message, edit_message

# Configure detailed logging
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

async def updatemediainfo_handler(client, message):
    """Enhanced handler with FFprobe-based metadata extraction and fallback"""
    try:
        LOGGER.info("🚀 Starting updatemediainfo command with FFprobe fallback")
        
        # Parse input
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, 
                "❌ **Usage:**\n• `/updatemediainfo -1001234567890`\n• Reply to file with channel IDs")
            return
        
        LOGGER.info(f"📋 Processing {len(channels)} channels: {channels}")
        
        # Process each channel with FFprobe fallback
        for i, channel_id in enumerate(channels):
            LOGGER.info(f"🔄 Processing channel {i+1}/{len(channels)}: {channel_id}")
            await process_channel_with_ffprobe_fallback(channel_id, message)
            
    except Exception as e:
        LOGGER.error(f"💥 UpdateMediaInfo handler error: {e}", exc_info=True)
        await send_message(message, f"❌ **Fatal Error:** {e}")

async def process_channel_with_ffprobe_fallback(channel_id, message):
    """Process channel with FFprobe and intelligent fallback system"""
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
            f"📊 **Method:** FFprobe with 5MB→20MB fallback\n"
            f"🔍 **Step:** Scanning messages...")
        
        processed = 0
        errors = 0
        skipped_no_media = 0
        skipped_already_processed = 0
        skipped_no_change = 0
        fallback_used = 0
        total_messages = 0
        media_found = 0
        
        # Step 3: Scan messages with FFprobe fallback
        LOGGER.info("🔍 Step 3: Starting message scan with FFprobe fallback")
        try:
            message_count = 0
            async for msg in TgClient.user.get_chat_history(chat_id=channel_id, limit=100):  # Limit for testing
                message_count += 1
                total_messages += 1
                
                LOGGER.debug(f"📨 Message {message_count}: ID={msg.id}, Date={msg.date}, Media={bool(msg.media)}")
                
                # Step 3a: Check for media
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
                
                # Step 3c: Process with FFprobe fallback
                try:
                    result, used_fallback = await process_message_with_ffprobe_fallback(msg, media_check_result)
                    if used_fallback:
                        fallback_used += 1
                        
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
                        f"🔄 **Fallback Used:** {fallback_used} | ℹ️ **No Changes:** {skipped_no_change}\n"
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
            f"🔄 **Fallback Used:** {fallback_used} files\n"
            f"ℹ️ **No Changes:** {skipped_no_change} files\n"
            f"⏭️ **Skipped (No Media):** {skipped_no_media}\n"
            f"⏭️ **Skipped (Already Processed):** {skipped_already_processed}"
        )
        
        await edit_message(progress_msg, final_stats)
        LOGGER.info(f"🎉 Channel processing complete: {processed} updated, {errors} errors, {fallback_used} fallbacks used")
            
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

async def process_message_with_ffprobe_fallback(msg, media_info):
    """Process single message with FFprobe fallback system (5MB → 20MB)"""
    temp_file_5mb = None
    temp_file_20mb = None
    used_fallback = False
    
    try:
        LOGGER.info(f"🔄 Processing message {msg.id}: {media_info['filename']}")
        
        # Step A: Try 5MB first
        LOGGER.debug(f"📥 Step A: Trying 5MB download for {media_info['filename']}")
        temp_file_5mb = await download_partial_media_mb(msg, media_info, 5)
        if not temp_file_5mb:
            LOGGER.error(f"❌ 5MB download failed for message {msg.id}")
            return "error", False
        
        # Step B: Extract metadata with FFprobe (5MB attempt)
        LOGGER.debug(f"🔍 Step B: Extracting metadata with FFprobe from 5MB file")
        ffprobe_data = await extract_metadata_with_ffprobe(temp_file_5mb)
        
        # Step C: Check if 5MB gave us good results
        if not ffprobe_data or not ffprobe_data.get('has_content') or not is_metadata_complete(ffprobe_data):
            LOGGER.info(f"🔄 5MB insufficient for message {msg.id}, trying 20MB fallback")
            used_fallback = True
            
            # Cleanup 5MB file
            if temp_file_5mb and os.path.exists(temp_file_5mb):
                os.unlink(temp_file_5mb)
                temp_file_5mb = None
            
            # Step D: Try 20MB fallback
            LOGGER.debug(f"📥 Step D: Fallback 20MB download for {media_info['filename']}")
            temp_file_20mb = await download_partial_media_mb(msg, media_info, 20)
            if not temp_file_20mb:
                LOGGER.error(f"❌ 20MB fallback download failed for message {msg.id}")
                return "error", True
            
            # Step E: Extract metadata with FFprobe (20MB attempt)
            LOGGER.debug(f"🔍 Step E: Extracting metadata from 20MB fallback file")
            ffprobe_data = await extract_metadata_with_ffprobe(temp_file_20mb)
        
        # Final check
        if not ffprobe_data or not ffprobe_data.get('has_content'):
            LOGGER.warning(f"⚠️ No useful metadata extracted for message {msg.id} even with fallback")
            return "error", used_fallback
        
        # Step F: Generate caption
        LOGGER.debug(f"✏️ Step F: Generating enhanced caption")
        current_caption = msg.caption or ""
        enhanced_caption = generate_caption_with_ffprobe_data(current_caption, ffprobe_data)
        
        # Step G: Safe caption update
        LOGGER.debug(f"📝 Step G: Safe caption update")
        result = await safe_edit_caption(msg, current_caption, enhanced_caption)
        
        if result:
            LOGGER.info(f"✅ Successfully processed message {msg.id} {'(with fallback)' if used_fallback else ''}")
            return "success", used_fallback
        else:
            LOGGER.info(f"ℹ️ No changes made to message {msg.id}")
            return "no_change", used_fallback
        
    except Exception as e:
        LOGGER.error(f"💥 Processing error for message {msg.id}: {e}", exc_info=True)
        return "error", used_fallback
    finally:
        # Cleanup both temp files
        for temp_file in [temp_file_5mb, temp_file_20mb]:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    LOGGER.debug(f"🗑️ Cleaned up temp file: {temp_file}")
                except Exception as e:
                    LOGGER.warning(f"⚠️ Cleanup warning: {e}")

def is_metadata_complete(ffprobe_data):
    """Check if extracted metadata is complete enough"""
    try:
        video = ffprobe_data.get('video')
        audio = ffprobe_data.get('audio', [])
        
        # Consider metadata complete if we have:
        # - Video with codec and resolution OR
        # - Audio with codec info
        video_complete = (video and 
                         video.get('codec_name') and 
                         video.get('width') and 
                         video.get('height'))
        
        audio_complete = (audio and 
                         len(audio) > 0 and 
                         audio[0].get('codec_name'))
        
        return video_complete or audio_complete
    except Exception as e:
        LOGGER.error(f"❌ Error checking metadata completeness: {e}")
        return False

async def download_partial_media_mb(msg, media_info, size_mb):
    """Download partial media with specified size in MB"""
    try:
        LOGGER.debug(f"📥 Starting {size_mb}MB download: {media_info['filename']} ({media_info['file_size']} bytes)")
        
        # Create temp file with proper extension
        file_ext = os.path.splitext(media_info['filename'])[1] or '.tmp'
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_path = temp_file.name
        
        LOGGER.debug(f"📁 Created temp file: {temp_path}")
        
        # Calculate chunks needed
        chunk_size = 100 * 1024  # 100KB per chunk
        max_chunks = int((size_mb * 1024 * 1024) / chunk_size)
        
        chunk_count = 0
        total_downloaded = 0
        
        LOGGER.debug(f"📡 Starting stream download (max {max_chunks} chunks for {size_mb}MB)")
        async for chunk in TgClient.user.stream_media(msg, limit=max_chunks):
            with open(temp_path, "ab") as f:
                f.write(chunk)
            chunk_count += 1
            total_downloaded += len(chunk)
            
            if chunk_count >= max_chunks:
                break
        
        if chunk_count > 0 and os.path.exists(temp_path):
            final_size = os.path.getsize(temp_path)
            LOGGER.info(f"✅ {size_mb}MB download complete: {final_size/1024/1024:.1f}MB in {chunk_count} chunks")
            return temp_path
        else:
            LOGGER.error(f"❌ {size_mb}MB download failed: no chunks received")
            return None
        
    except Exception as e:
        LOGGER.error(f"💥 {size_mb}MB download error: {e}", exc_info=True)
        return None

async def extract_metadata_with_ffprobe(file_path):
    """Extract comprehensive metadata using FFprobe with enhanced parameters"""
    try:
        LOGGER.debug(f"🔍 Running FFprobe on: {file_path}")
        
        # Enhanced FFprobe command for partial files
        cmd = [
            "ffprobe",
            "-v", "error",
            "-analyzeduration", "15000000",    # 15 seconds analysis duration
            "-probesize", "15000000",          # 15MB probe size
            "-show_entries", "format=duration,bit_rate,size:stream=codec_type,codec_name,width,height,channels,sample_rate,bit_rate,tags",
            "-print_format", "json",
            file_path
        ]
        
        # Run FFprobe
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if stderr:
            stderr_text = stderr.decode().strip()
            if "partial file" in stderr_text.lower() or "truncated" in stderr_text.lower():
                LOGGER.warning(f"⚠️ FFprobe detected partial/truncated file, but continuing")
            elif stderr_text:
                LOGGER.warning(f"⚠️ FFprobe warnings: {stderr_text}")
        
        if proc.returncode != 0 and not stdout:
            LOGGER.error(f"❌ FFprobe failed with return code {proc.returncode}")
            return None
        
        # Parse JSON output
        try:
            data = json.loads(stdout.decode())
        except json.JSONDecodeError as e:
            LOGGER.error(f"❌ Failed to parse FFprobe JSON output: {e}")
            return None
        
        LOGGER.debug(f"📊 FFprobe data: {len(data.get('streams', []))} streams found")
        
        # Parse streams
        video_info = None
        audio_tracks = []
        
        for i, stream in enumerate(data.get('streams', [])):
            codec_type = stream.get('codec_type')
            LOGGER.debug(f"🎬 Stream {i}: Type={codec_type}")
            
            if codec_type == "video" and not video_info:
                codec_name = stream.get('codec_name', 'Unknown')
                width = stream.get('width')
                height = stream.get('height')
                
                video_info = {
                    'codec_name': codec_name,
                    'codec': codec_name,  # Compatibility
                    'width': width,
                    'height': height,
                    'aspect_ratio': stream.get('display_aspect_ratio'),
                    'frame_rate': stream.get('avg_frame_rate'),
                    'bit_rate': stream.get('bit_rate')
                }
                LOGGER.debug(f"📹 Video stream: {video_info}")
                
            elif codec_type == "audio":
                codec_name = stream.get('codec_name', 'Unknown')
                channels = stream.get('channels', 1)
                
                # Extract language from tags
                tags = stream.get('tags', {}) or {}
                language = None
                for key in ['language', 'lang', 'LANGUAGE', 'Language']:
                    if key in tags:
                        language = tags[key]
                        break
                
                audio_track = {
                    'codec_name': codec_name,
                    'codec': codec_name,  # Compatibility
                    'channels': channels,
                    'language': language or 'Unknown',
                    'sample_rate': stream.get('sample_rate'),
                    'bit_rate': stream.get('bit_rate'),
                    'tags': tags
                }
                audio_tracks.append(audio_track)
                LOGGER.debug(f"🎵 Audio stream: {audio_track}")
        
        # Get format information
        format_info = data.get('format', {})
        duration = format_info.get('duration')
        bit_rate = format_info.get('bit_rate')
        
        # Determine if we have useful content
        has_content = bool(video_info) or bool(audio_tracks)
        
        result = {
            'video': video_info,
            'audio': audio_tracks,
            'format': {
                'duration': duration,
                'bit_rate': bit_rate,
                'size': format_info.get('size')
            },
            'has_content': has_content
        }
        
        LOGGER.info(f"✅ FFprobe extracted: Video={bool(video_info)}, Audio={len(audio_tracks)} tracks, HasContent={has_content}")
        return result
        
    except Exception as e:
        LOGGER.error(f"💥 FFprobe extraction error: {e}", exc_info=True)
        return None

def generate_caption_with_ffprobe_data(original_caption, ffprobe_data):
    """Generate caption with comprehensive FFprobe metadata"""
    try:
        if not ffprobe_data or not ffprobe_data.get('has_content'):
            LOGGER.warning("⚠️ No FFprobe content to generate caption")
            return original_caption or ""
            
        LOGGER.debug(f"✏️ Generating caption with FFprobe data (original length: {len(original_caption)})")
        
        # Start with original caption
        enhanced = original_caption.strip() if original_caption else ""
        mediainfo_lines = []
        
        # Video information
        video = ffprobe_data.get('video')
        if video and video.get('codec_name'):
            codec = video.get('codec_name', 'Unknown')
            width = video.get('width')
            height = video.get('height')
            
            # Determine resolution label
            resolution = ""
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
                    if width and height:
                        resolution = f"{width}x{height}"
            
            # Build video line
            video_line = f"Video: {codec.upper()}"
            if resolution:
                video_line += f" {resolution}"
            
            mediainfo_lines.append(video_line)
            LOGGER.debug(f"📹 Generated video line: {video_line}")
        
        # Audio information
        audio_tracks = ffprobe_data.get('audio', [])
        if audio_tracks:
            audio_count = len(audio_tracks)
            
            # Extract languages
            languages = []
            for audio in audio_tracks:
                lang = audio.get('language', 'Unknown').upper()
                
                # Clean and standardize language codes
                if lang and lang not in ['UNKNOWN', 'UND', 'UNDEFINED', 'N/A', '']:
                    # Convert common language codes
                    lang_map = {
                        'EN': 'ENG', 'ENGLISH': 'ENG',
                        'HI': 'HIN', 'HINDI': 'HIN',
                        'ES': 'SPA', 'SPANISH': 'SPA',
                        'FR': 'FRA', 'FRENCH': 'FRA',
                        'DE': 'GER', 'GERMAN': 'GER',
                        'IT': 'ITA', 'ITALIAN': 'ITA',
                        'JA': 'JPN', 'JAPANESE': 'JPN',
                        'KO': 'KOR', 'KOREAN': 'KOR',
                        'ZH': 'CHI', 'CHINESE': 'CHI',
                        'AR': 'ARA', 'ARABIC': 'ARA',
                        'RU': 'RUS', 'RUSSIAN': 'RUS',
                        'PT': 'POR', 'PORTUGUESE': 'POR'
                    }
                    lang = lang_map.get(lang, lang)
                    
                    if lang not in languages:
                        languages.append(lang)
            
            # Build audio line
            audio_line = f"Audio: {audio_count}"
            if languages:
                # Show up to 3 languages for clean display
                lang_display = ', '.join(languages[:3])
                if len(languages) > 3:
                    lang_display += f" (+{len(languages)-3})"
                audio_line += f" ({lang_display})"
            
            mediainfo_lines.append(audio_line)
            LOGGER.debug(f"🎵 Generated audio line: {audio_line}")
        
        # Combine with original caption
        if mediainfo_lines:
            mediainfo_section = "\n\n" + "\n".join(mediainfo_lines)
            enhanced_caption = enhanced + mediainfo_section
            
            # Respect Telegram's 1024 character caption limit
            if len(enhanced_caption) > 1020:
                max_original = 1020 - len(mediainfo_section) - 5
                if max_original > 0:
                    enhanced_caption = enhanced[:max_original] + "..." + mediainfo_section
                else:
                    enhanced_caption = mediainfo_section
            
            LOGGER.debug(f"✅ Caption generated with FFprobe (final length: {len(enhanced_caption)})")
            return enhanced_caption
        
        LOGGER.warning("⚠️ No metadata lines generated from FFprobe - returning original")
        return enhanced
        
    except Exception as e:
        LOGGER.error(f"💥 Caption generation error: {e}", exc_info=True)
        return original_caption or ""

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
