"""
Enhanced MediaInfo update with head+tail chunk download for moov atom handling
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

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

async def updatemediainfo_handler(client, message):
    """Enhanced handler with head+tail chunk download strategy"""
    try:
        LOGGER.info("🚀 Starting updatemediainfo command with head+tail chunk strategy")
        
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, 
                "❌ **Usage:**\n• `/updatemediainfo -1001234567890`\n• Reply to file with channel IDs")
            return
        
        LOGGER.info(f"📋 Processing {len(channels)} channels: {channels}")
        
        for i, channel_id in enumerate(channels):
            LOGGER.info(f"🔄 Processing channel {i+1}/{len(channels)}: {channel_id}")
            await process_channel_with_head_tail_strategy(channel_id, message)
            
    except Exception as e:
        LOGGER.error(f"💥 UpdateMediaInfo handler error: {e}", exc_info=True)
        await send_message(message, f"❌ **Fatal Error:** {e}")

async def process_channel_with_head_tail_strategy(channel_id, message):
    """Process channel with head+tail chunk download for moov atoms"""
    try:
        # Access channel
        try:
            chat = await TgClient.user.get_chat(channel_id)
            LOGGER.info(f"✅ Successfully accessed: {chat.title}")
        except Exception as e:
            await send_message(message, f"❌ **Access Error:** Cannot access {channel_id}\n**Reason:** {str(e)}")
            return
        
        progress_msg = await send_message(message,
            f"🔄 **Processing:** {chat.title}\n"
            f"📊 **Method:** Head+Tail chunk download\n"
            f"🎯 **Strategy:** 10MB head → 5MB tail → 50MB fallback\n"
            f"🔍 **Status:** Scanning messages...")
        
        # Statistics tracking
        processed = 0
        errors = 0
        skipped_no_media = 0
        skipped_already_processed = 0
        head_success = 0
        tail_success = 0
        fallback_success = 0
        total_messages = 0
        media_found = 0
        
        try:
            message_count = 0
            async for msg in TgClient.user.get_chat_history(chat_id=channel_id, limit=100):
                message_count += 1
                total_messages += 1
                
                LOGGER.debug(f"📨 Message {message_count}: ID={msg.id}")
                
                # Check for media
                media_check_result = await detailed_media_check(msg)
                if not media_check_result['has_media']:
                    skipped_no_media += 1
                    continue
                
                # Check if already processed
                if await already_has_mediainfo(msg):
                    skipped_already_processed += 1
                    continue
                
                media_found += 1
                LOGGER.info(f"🎯 Processing media message {msg.id}: {media_check_result['filename']}")
                
                # Head+Tail processing
                try:
                    result, method_used = await process_message_head_tail_strategy(msg, media_check_result)
                    
                    if result == "success":
                        processed += 1
                        if method_used == "head":
                            head_success += 1
                        elif method_used == "tail":
                            tail_success += 1
                        elif method_used == "fallback":
                            fallback_success += 1
                        LOGGER.info(f"✅ Successfully updated message {msg.id} using {method_used}")
                    else:
                        errors += 1
                        LOGGER.warning(f"⚠️ Failed to update message {msg.id}")
                        
                except Exception as e:
                    LOGGER.error(f"❌ Error processing message {msg.id}: {e}")
                    errors += 1
                
                # Progress update
                if message_count % 10 == 0:
                    await edit_message(progress_msg,
                        f"🔄 **Processing:** {chat.title}\n"
                        f"📊 **Messages:** {total_messages} | **Media:** {media_found}\n"
                        f"✅ **Updated:** {processed} | ❌ **Errors:** {errors}\n"
                        f"🎯 **Head:** {head_success} | 🎯 **Tail:** {tail_success} | 🎯 **Fallback:** {fallback_success}")
                    await asyncio.sleep(0.5)
        
        except Exception as e:
            LOGGER.error(f"💥 Message scan error: {e}")
            return
        
        # Final results
        final_stats = (
            f"✅ **Completed:** {chat.title}\n"
            f"📊 **Total Messages:** {total_messages}\n"
            f"📁 **Media Found:** {media_found}\n"
            f"✅ **Updated:** {processed} files\n"
            f"❌ **Errors:** {errors} files\n\n"
            f"🎯 **Head Chunk Success:** {head_success}\n"
            f"🎯 **Tail Chunk Success:** {tail_success}\n"
            f"🎯 **Fallback Success:** {fallback_success}\n"
            f"⏭️ **Skipped:** {skipped_no_media + skipped_already_processed}"
        )
        
        await edit_message(progress_msg, final_stats)
        LOGGER.info(f"🎉 Processing complete: Head={head_success}, Tail={tail_success}, Fallback={fallback_success}")
        
    except Exception as e:
        LOGGER.error(f"💥 Channel processing error: {e}")
        await send_message(message, f"❌ **Channel Error:** {str(e)}")

async def process_message_head_tail_strategy(msg, media_info):
    """Process message with head+tail chunk strategy for moov atoms"""
    temp_file_head = None
    temp_file_tail = None
    temp_file_fallback = None
    
    try:
        LOGGER.info(f"🔄 Head+Tail processing for message {msg.id}: {media_info['filename']}")
        file_size = media_info['file_size']
        
        # Method 1: Try 10MB head chunk first
        LOGGER.debug("🎯 Method 1: Trying 10MB head chunk")
        temp_file_head = await download_head_chunk(msg, media_info, 10 * 1024 * 1024)  # 10MB
        if temp_file_head:
            ffprobe_data = await extract_metadata_with_enhanced_ffprobe(temp_file_head)
            if ffprobe_data and ffprobe_data.get('has_content'):
                success = await update_caption_with_metadata(msg, ffprobe_data)
                if success:
                    return "success", "head"
            
            # Cleanup head file
            if os.path.exists(temp_file_head):
                os.unlink(temp_file_head)
                temp_file_head = None
        
        # Method 2: Try 5MB tail chunk (moov atom at end)
        LOGGER.debug("🎯 Method 2: Trying 5MB tail chunk")
        temp_file_tail = await download_tail_chunk(msg, media_info, 5 * 1024 * 1024)  # 5MB from end
        if temp_file_tail:
            ffprobe_data = await extract_metadata_with_enhanced_ffprobe(temp_file_tail)
            if ffprobe_data and ffprobe_data.get('has_content'):
                success = await update_caption_with_metadata(msg, ffprobe_data)
                if success:
                    return "success", "tail"
            
            # Cleanup tail file
            if os.path.exists(temp_file_tail):
                os.unlink(temp_file_tail)
                temp_file_tail = None
        
        # Method 3: Try combined head+tail approach
        LOGGER.debug("🎯 Method 3: Trying combined head+tail")
        temp_file_combined = await download_head_tail_combined(msg, media_info, 
                                                               head_size=10*1024*1024, 
                                                               tail_size=5*1024*1024)
        if temp_file_combined:
            ffprobe_data = await extract_metadata_with_enhanced_ffprobe(temp_file_combined)
            if ffprobe_data and ffprobe_data.get('has_content'):
                success = await update_caption_with_metadata(msg, ffprobe_data)
                if success:
                    return "success", "combined"
            
            # Cleanup combined file
            if os.path.exists(temp_file_combined):
                os.unlink(temp_file_combined)
        
        # Method 4: Large fallback (50MB from head) for stubborn files
        if file_size > 100 * 1024 * 1024:  # Only for files > 100MB
            LOGGER.debug("🎯 Method 4: Large fallback (50MB)")
            temp_file_fallback = await download_head_chunk(msg, media_info, 50 * 1024 * 1024)  # 50MB
            if temp_file_fallback:
                ffprobe_data = await extract_metadata_with_enhanced_ffprobe(temp_file_fallback)
                if ffprobe_data and ffprobe_data.get('has_content'):
                    success = await update_caption_with_metadata(msg, ffprobe_data)
                    if success:
                        return "success", "fallback"
        
        return "error", "none"
        
    except Exception as e:
        LOGGER.error(f"💥 Head+Tail processing error: {e}")
        return "error", "none"
    finally:
        # Cleanup all temp files
        for temp_file in [temp_file_head, temp_file_tail, temp_file_fallback]:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass

async def download_head_chunk(msg, media_info, size_bytes):
    """Download chunk from beginning of file"""
    try:
        LOGGER.debug(f"📥 Downloading {size_bytes/1024/1024:.1f}MB head chunk")
        
        # Create temp file
        file_ext = os.path.splitext(media_info['filename'])[1] or '.tmp'
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_path = temp_file.name
        
        # Calculate chunks needed for head
        chunk_size = 100 * 1024  # 100KB per chunk
        max_chunks = int(size_bytes / chunk_size)
        
        chunk_count = 0
        async for chunk in TgClient.user.stream_media(msg, limit=max_chunks):
            with open(temp_path, "ab") as f:
                f.write(chunk)
            chunk_count += 1
            if chunk_count >= max_chunks:
                break
        
        if chunk_count > 0 and os.path.exists(temp_path):
            final_size = os.path.getsize(temp_path)
            LOGGER.info(f"✅ Head chunk downloaded: {final_size/1024/1024:.1f}MB")
            return temp_path
        
        return None
        
    except Exception as e:
        LOGGER.error(f"💥 Head chunk download error: {e}")
        return None

async def download_tail_chunk(msg, media_info, size_bytes):
    """Download chunk from end of file using offset calculation"""
    try:
        LOGGER.debug(f"📥 Downloading {size_bytes/1024/1024:.1f}MB tail chunk")
        
        file_size = media_info['file_size']
        if file_size <= size_bytes:
            # File too small, download entire file
            return await download_head_chunk(msg, media_info, file_size)
        
        # Calculate offset to start downloading from end
        start_offset = file_size - size_bytes
        
        # Create temp file
        file_ext = os.path.splitext(media_info['filename'])[1] or '.tmp'
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_path = temp_file.name
        
        # Calculate chunks to skip and chunks to download
        chunk_size = 100 * 1024  # 100KB per chunk
        chunks_to_skip = int(start_offset / chunk_size)
        max_chunks_to_download = int(size_bytes / chunk_size)
        
        LOGGER.debug(f"📊 Skipping {chunks_to_skip} chunks, downloading {max_chunks_to_download} chunks")
        
        chunk_count = 0
        downloaded_count = 0
        
        async for chunk in TgClient.user.stream_media(msg, limit=chunks_to_skip + max_chunks_to_download):
            chunk_count += 1
            
            # Skip chunks until we reach the tail section
            if chunk_count <= chunks_to_skip:
                continue
            
            # Download tail chunks
            with open(temp_path, "ab") as f:
                f.write(chunk)
            downloaded_count += 1
            
            if downloaded_count >= max_chunks_to_download:
                break
        
        if downloaded_count > 0 and os.path.exists(temp_path):
            final_size = os.path.getsize(temp_path)
            LOGGER.info(f"✅ Tail chunk downloaded: {final_size/1024/1024:.1f}MB from offset {start_offset}")
            return temp_path
        
        return None
        
    except Exception as e:
        LOGGER.error(f"💥 Tail chunk download error: {e}")
        return None

async def download_head_tail_combined(msg, media_info, head_size, tail_size):
    """Download and combine head+tail chunks into single file"""
    try:
        LOGGER.debug(f"📥 Downloading combined head ({head_size/1024/1024:.1f}MB) + tail ({tail_size/1024/1024:.1f}MB)")
        
        # Download head chunk
        head_file = await download_head_chunk(msg, media_info, head_size)
        if not head_file:
            return None
        
        # Download tail chunk  
        tail_file = await download_tail_chunk(msg, media_info, tail_size)
        if not tail_file:
            if os.path.exists(head_file):
                os.unlink(head_file)
            return None
        
        # Combine head and tail into single file
        file_ext = os.path.splitext(media_info['filename'])[1] or '.tmp'
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            combined_path = temp_file.name
        
        # Copy head chunk
        with open(head_file, 'rb') as head_f, open(combined_path, 'wb') as combined_f:
            combined_f.write(head_f.read())
        
        # Append tail chunk
        with open(tail_file, 'rb') as tail_f, open(combined_path, 'ab') as combined_f:
            combined_f.write(tail_f.read())
        
        # Cleanup individual files
        for temp_file in [head_file, tail_file]:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        final_size = os.path.getsize(combined_path)
        LOGGER.info(f"✅ Combined head+tail file: {final_size/1024/1024:.1f}MB")
        return combined_path
        
    except Exception as e:
        LOGGER.error(f"💥 Combined download error: {e}")
        return None

async def extract_metadata_with_enhanced_ffprobe(file_path):
    """Enhanced FFprobe with better partial file handling"""
    try:
        LOGGER.debug(f"🔍 Running enhanced FFprobe on: {file_path}")
        
        # Enhanced FFprobe command with maximum tolerance
        cmd = [
            "ffprobe",
            "-v", "error",
            "-analyzeduration", "30000000",     # 30 seconds analysis
            "-probesize", "30000000",           # 30MB probe size
            "-fflags", "+igndts+ignidx+genpts", # Ignore errors, generate PTS
            "-read_intervals", "%+#200",        # Read up to 200 packets
            "-skip_frame", "nokey",             # Skip non-keyframes
            "-show_entries", "format=duration,bit_rate,size:stream=codec_type,codec_name,width,height,channels,sample_rate,bit_rate,tags",
            "-print_format", "json",
            file_path
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        # Enhanced error tolerance
        if stderr:
            stderr_text = stderr.decode().strip()
            
            # Log but continue with known issues
            if any(keyword in stderr_text.lower() for keyword in [
                'moov atom not found', 'invalid data', 'incomplete', 'truncated', 
                'end of file', 'no space left', 'premature end'
            ]):
                LOGGER.warning(f"⚠️ FFprobe partial file warning (continuing): {stderr_text[:200]}...")
            else:
                LOGGER.warning(f"⚠️ FFprobe stderr: {stderr_text[:200]}...")
        
        # Process partial results even with errors
        if proc.returncode != 0:
            if not stdout:
                LOGGER.error(f"❌ Enhanced FFprobe failed completely")
                return None
            else:
                LOGGER.warning(f"⚠️ Enhanced FFprobe partial success (return code {proc.returncode})")
        
        try:
            data = json.loads(stdout.decode())
        except json.JSONDecodeError as e:
            LOGGER.error(f"❌ Failed to parse FFprobe JSON: {e}")
            return None
        
        # Extract streams
        video_info = None
        audio_tracks = []
        
        for i, stream in enumerate(data.get('streams', [])):
            codec_type = stream.get('codec_type')
            
            if codec_type == "video" and not video_info:
                codec_name = stream.get('codec_name', 'Unknown')
                width = stream.get('width')
                height = stream.get('height')
                
                video_info = {
                    'codec_name': codec_name,
                    'codec': codec_name,
                    'width': width,
                    'height': height,
                    'bit_rate': stream.get('bit_rate')
                }
                LOGGER.debug(f"📹 Video found: {video_info}")
                
            elif codec_type == "audio":
                codec_name = stream.get('codec_name', 'Unknown')
                channels = stream.get('channels', 1)
                
                # Extract language
                tags = stream.get('tags', {}) or {}
                language = None
                for key in ['language', 'lang', 'LANGUAGE']:
                    if key in tags:
                        language = tags[key]
                        break
                
                audio_track = {
                    'codec_name': codec_name,
                    'codec': codec_name,
                    'channels': channels,
                    'language': language or 'Unknown'
                }
                audio_tracks.append(audio_track)
                LOGGER.debug(f"🎵 Audio found: {audio_track}")
        
        has_content = bool(video_info) or bool(audio_tracks)
        
        result = {
            'video': video_info,
            'audio': audio_tracks,
            'has_content': has_content
        }
        
        if has_content:
            LOGGER.info(f"✅ Enhanced FFprobe success: Video={bool(video_info)}, Audio={len(audio_tracks)} tracks")
        else:
            LOGGER.warning(f"⚠️ Enhanced FFprobe found no streams")
        
        return result
        
    except Exception as e:
        LOGGER.error(f"💥 Enhanced FFprobe error: {e}")
        return None

async def update_caption_with_metadata(msg, metadata):
    """Update caption with metadata"""
    try:
        current_caption = msg.caption or ""
        enhanced_caption = generate_caption_with_metadata(current_caption, metadata)
        
        return await safe_edit_caption(msg, current_caption, enhanced_caption)
        
    except Exception as e:
        LOGGER.error(f"❌ Caption update error: {e}")
        return False

def generate_caption_with_metadata(original_caption, metadata):
    """Generate caption with metadata"""
    try:
        if not metadata or not metadata.get('has_content'):
            return original_caption or ""
        
        enhanced = original_caption.strip() if original_caption else ""
        mediainfo_lines = []
        
        # Video information
        video = metadata.get('video')
        if video and video.get('codec_name'):
            codec = video.get('codec_name', 'Unknown')
            width = video.get('width')
            height = video.get('height')
            
            # Resolution
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
            
            video_line = f"Video: {codec.upper()}"
            if resolution:
                video_line += f" {resolution}"
            
            mediainfo_lines.append(video_line)
        
        # Audio information
        audio_tracks = metadata.get('audio', [])
        if audio_tracks:
            audio_count = len(audio_tracks)
            
            # Languages
            languages = []
            for audio in audio_tracks:
                lang = audio.get('language', 'Unknown').upper()
                
                if lang and lang not in ['UNKNOWN', 'UND', 'UNDEFINED', 'N/A', '']:
                    lang_map = {
                        'EN': 'ENG', 'ENGLISH': 'ENG',
                        'HI': 'HIN', 'HINDI': 'HIN',
                        'ES': 'SPA', 'SPANISH': 'SPA',
                        'FR': 'FRA', 'FRENCH': 'FRA',
                        'DE': 'GER', 'GERMAN': 'GER'
                    }
                    lang = lang_map.get(lang, lang)
                    
                    if lang not in languages:
                        languages.append(lang)
            
            audio_line = f"Audio: {audio_count}"
            if languages:
                lang_display = ', '.join(languages[:3])
                if len(languages) > 3:
                    lang_display += f" (+{len(languages)-3})"
                audio_line += f" ({lang_display})"
            
            mediainfo_lines.append(audio_line)
        
        # Combine
        if mediainfo_lines:
            mediainfo_section = "\n\n" + "\n".join(mediainfo_lines)
            enhanced_caption = enhanced + mediainfo_section
            
            # Telegram limit
            if len(enhanced_caption) > 1020:
                max_original = 1020 - len(mediainfo_section) - 5
                if max_original > 0:
                    enhanced_caption = enhanced[:max_original] + "..." + mediainfo_section
                else:
                    enhanced_caption = mediainfo_section
            
            return enhanced_caption
        
        return enhanced
        
    except Exception as e:
        LOGGER.error(f"💥 Caption generation error: {e}")
        return original_caption or ""

# ... [Keep all existing helper functions: detailed_media_check, already_has_mediainfo, 
#      safe_edit_caption, get_target_channels] ...

async def detailed_media_check(msg):
    """Detailed media checking"""
    try:
        result = {
            'has_media': False,
            'type': None,
            'filename': None,
            'file_size': 0,
            'reason': 'No media detected'
        }
        
        if msg.video:
            result.update({
                'has_media': True,
                'type': 'video',
                'filename': msg.video.file_name or f"video_{msg.id}.mp4",
                'file_size': msg.video.file_size or 0,
                'reason': 'Video file detected'
            })
            return result
        
        if msg.audio:
            result.update({
                'has_media': True,
                'type': 'audio',
                'filename': msg.audio.file_name or f"audio_{msg.id}.mp3",
                'file_size': msg.audio.file_size or 0,
                'reason': 'Audio file detected'
            })
            return result
        
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
                return result
        
        return result
        
    except Exception as e:
        LOGGER.error(f"❌ Media check error: {e}")
        return result

async def already_has_mediainfo(msg):
    """Check if already has MediaInfo"""
    try:
        caption = msg.caption or ""
        return "Video:" in caption and "Audio:" in caption
    except:
        return False

async def safe_edit_caption(msg, current_caption, new_caption):
    """Safe caption editing"""
    try:
        if current_caption == new_caption:
            return False
        
        if "Video:" not in new_caption and "Audio:" not in new_caption:
            return False
        
        try:
            await TgClient.user.edit_message_caption(
                chat_id=msg.chat.id,
                message_id=msg.id,
                caption=new_caption
            )
            return True
        except MessageNotModified:
            return False
            
    except Exception as e:
        LOGGER.error(f"❌ Caption edit error: {e}")
        return False

async def get_target_channels(message):
    """Extract channel IDs"""
    try:
        if len(message.command) > 1:
            channel_id = message.command[1]
            if channel_id.startswith('-100'):
                return [int(channel_id)]
            elif channel_id.isdigit():
                return [int(f"-100{channel_id}")]
            else:
                return [channel_id]
        return []
    except:
        return []
