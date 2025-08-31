"""
MediaInfo update with optimized head+tail strategy (no hanging)
"""

import asyncio
import logging
import os
import tempfile
import json
import re
from datetime import datetime
from pyrogram.errors import MessageNotModified
from bot.core.client import TgClient
from bot.helpers.message_utils import send_message, edit_message

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

async def updatemediainfo_handler(client, message):
    """Handler with optimized head+tail strategy"""
    try:
        LOGGER.info("🚀 Starting updatemediainfo with optimized head+tail strategy")
        
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, 
                "❌ **Usage:**\n• `/updatemediainfo -1001234567890`")
            return
        
        for channel_id in channels:
            await process_channel_optimized(channel_id, message)
            
    except Exception as e:
        LOGGER.error(f"💥 Handler error: {e}", exc_info=True)
        await send_message(message, f"❌ **Error:** {e}")

async def process_channel_optimized(channel_id, message):
    """Process channel with optimized approach"""
    try:
        # Access channel
        chat = await TgClient.user.get_chat(channel_id)
        LOGGER.info(f"✅ Accessing channel: {chat.title}")
        
        progress_msg = await send_message(message,
            f"🔄 **Processing:** {chat.title}\n"
            f"📊 **Method:** Optimized Head+Tail Strategy\n"
            f"🎯 **Fix:** No hanging on large files\n"
            f"🔍 **Status:** Scanning messages...")
        
        processed = 0
        errors = 0
        skipped = 0
        head_success = 0
        large_head_success = 0
        full_success = 0
        total_messages = 0
        media_found = 0
        
        message_count = 0
        async for msg in TgClient.user.get_chat_history(chat_id=channel_id, limit=100):
            message_count += 1
            total_messages += 1
            
            # Check for media
            if not await has_media(msg):
                skipped += 1
                continue
            
            # Check if already processed
            if await already_has_mediainfo(msg):
                skipped += 1
                continue
            
            media_found += 1
            LOGGER.info(f"🎯 Processing media message {msg.id}")
            
            try:
                success, method = await process_with_optimized_strategy(TgClient.user, msg)
                if success:
                    processed += 1
                    if method == "head":
                        head_success += 1
                    elif method == "large_head":
                        large_head_success += 1
                    elif method == "full":
                        full_success += 1
                    LOGGER.info(f"✅ Updated message {msg.id} using {method}")
                else:
                    errors += 1
                    LOGGER.error(f"❌ Failed to update message {msg.id}")
            except Exception as e:
                LOGGER.error(f"💥 Exception processing {msg.id}: {e}")
                errors += 1
            
            # Progress update
            if message_count % 5 == 0:
                await edit_message(progress_msg,
                    f"🔄 **Processing:** {chat.title}\n"
                    f"📊 **Messages:** {total_messages} | **Media:** {media_found}\n"
                    f"✅ **Updated:** {processed} | ❌ **Errors:** {errors}\n"
                    f"🎯 **Head:** {head_success} | 📈 **Large Head:** {large_head_success} | 📥 **Full:** {full_success}")
                await asyncio.sleep(0.5)
        
        # Final results
        final_stats = (
            f"✅ **Completed:** {chat.title}\n"
            f"📊 **Total Messages:** {total_messages}\n"
            f"📁 **Media Found:** {media_found}\n"
            f"✅ **Updated:** {processed} files\n"
            f"❌ **Errors:** {errors} files\n"
            f"⏭️ **Skipped:** {skipped} files\n\n"
            f"🎯 **Head Success:** {head_success}\n"
            f"📈 **Large Head Success:** {large_head_success}\n"
            f"📥 **Full Success:** {full_success}"
        )
        
        await edit_message(progress_msg, final_stats)
        
    except Exception as e:
        LOGGER.error(f"💥 Channel processing error: {e}")
        await send_message(message, f"❌ **Error:** {str(e)}")

async def process_with_optimized_strategy(client, message):
    """Process with optimized strategy - no hanging tail downloads"""
    try:
        media = None
        if message.video:
            media = message.video
        elif message.audio:
            media = message.audio
        elif message.document:
            media = message.document
        else:
            return False, "none"
        
        filename = str(media.file_name) if media.file_name else f"media_{message.id}"
        size = media.file_size
        
        LOGGER.info(f"📁 Processing: {filename} ({size/1024/1024:.1f}MB)")
        
        # Strategy 1: Try 15MB head chunk (increased from 10MB)
        LOGGER.info("🎯 Strategy 1: Trying 15MB head chunk")
        success = await try_head_chunk_processing(client, message, filename, 15)
        if success:
            return True, "head"
        
        # Strategy 2: Try 50MB head chunk for stubborn files (replaces problematic tail)
        if size > 100 * 1024 * 1024:  # Only for files > 100MB
            LOGGER.info("🎯 Strategy 2: Trying 50MB large head chunk")
            success = await try_head_chunk_processing(client, message, filename, 50)
            if success:
                return True, "large_head"
        
        # Strategy 3: Full download for smaller files (< 500MB)
        if size <= 500 * 1024 * 1024:
            LOGGER.info("🎯 Strategy 3: Full download for complete metadata")
            success = await try_full_download_processing(client, message, filename)
            if success:
                return True, "full"
        else:
            LOGGER.warning(f"⚠️ File too large for full download: {size/1024/1024:.1f}MB")
        
        LOGGER.warning("⚠️ All strategies failed - no usable metadata found")
        return False, "failed"
        
    except Exception as e:
        LOGGER.error(f"💥 Optimized processing error: {e}")
        return False, "error"

async def try_head_chunk_processing(client, message, filename, size_mb):
    """Try processing with head chunk of specified size"""
    download_path = None
    try:
        LOGGER.debug(f"📥 Downloading {size_mb}MB head chunk")
        
        # Create temp file
        rand_str = f"head_{size_mb}_{message.id}"
        download_path = f"/tmp/{rand_str}_{filename.replace('/', '_')}"
        
        # Download head chunk with timeout
        chunk_size = 100 * 1024  # 100KB per chunk
        max_chunks = int((size_mb * 1024 * 1024) / chunk_size)
        
        chunk_count = 0
        
        # Add timeout for download
        try:
            async with asyncio.timeout(120):  # 2 minute timeout
                async for chunk in client.stream_media(message, limit=max_chunks):
                    with open(download_path, "ab") as f:
                        f.write(chunk)
                    chunk_count += 1
                    if chunk_count >= max_chunks:
                        break
        except asyncio.TimeoutError:
            LOGGER.warning(f"⚠️ {size_mb}MB head download timed out")
            return False
        
        if chunk_count == 0:
            LOGGER.warning(f"⚠️ No chunks downloaded for {size_mb}MB head")
            return False
        
        file_size = os.path.getsize(download_path) if os.path.exists(download_path) else 0
        LOGGER.debug(f"✅ Head chunk downloaded: {file_size/1024/1024:.1f}MB")
        
        # Process with MediaInfo
        return await process_file_with_mediainfo_optimized(download_path, message)
        
    except Exception as e:
        LOGGER.error(f"💥 Head chunk processing error ({size_mb}MB): {e}")
        return False
    finally:
        if download_path and os.path.exists(download_path):
            try:
                os.remove(download_path)
            except:
                pass

async def try_full_download_processing(client, message, filename):
    """Try processing with full download"""
    download_path = None
    try:
        LOGGER.debug("📥 Starting full download")
        
        rand_str = f"full_{message.id}"
        download_path = f"/tmp/{rand_str}_{filename.replace('/', '_')}"
        
        # Full download with timeout
        try:
            async with asyncio.timeout(300):  # 5 minute timeout
                await message.download(download_path)
        except asyncio.TimeoutError:
            LOGGER.warning("⚠️ Full download timed out")
            return False
        
        if not os.path.exists(download_path):
            LOGGER.warning("⚠️ Full download failed - file not found")
            return False
        
        file_size = os.path.getsize(download_path)
        LOGGER.debug(f"✅ Full download completed: {file_size/1024/1024:.1f}MB")
        
        # Process with MediaInfo
        return await process_file_with_mediainfo_optimized(download_path, message)
        
    except Exception as e:
        LOGGER.error(f"💥 Full download processing error: {e}")
        return False
    finally:
        if download_path and os.path.exists(download_path):
            try:
                os.remove(download_path)
            except:
                pass

async def process_file_with_mediainfo_optimized(file_path, message):
    """Process file with MediaInfo and update caption"""
    try:
        # Run MediaInfo with timeout
        try:
            async with asyncio.timeout(30):  # 30 second timeout
                mediainfo_json_text = await async_subprocess(f"mediainfo '{file_path}' --Output=JSON")
        except asyncio.TimeoutError:
            LOGGER.warning("⚠️ MediaInfo CLI timed out")
            return False
        
        if not mediainfo_json_text:
            LOGGER.warning("⚠️ MediaInfo produced no output")
            return False
        
        # Parse JSON
        try:
            mediainfo_json = json.loads(mediainfo_json_text)
        except json.JSONDecodeError as e:
            LOGGER.warning(f"⚠️ MediaInfo JSON parse failed: {e}")
            return False
        
        # Extract metadata
        caption_data = extract_caption_metadata(mediainfo_json)
        if not caption_data:
            LOGGER.warning("⚠️ No caption data extracted")
            return False
        
        # Check for actual streams
        video = caption_data.get("video")
        audio = caption_data.get("audio", [])
        
        if not video and not audio:
            LOGGER.warning("⚠️ No video or audio streams found")
            return False
        
        LOGGER.info(f"✅ Found streams: Video={bool(video)}, Audio={len(audio)}")
        
        # Generate caption
        current_caption = message.caption or ""
        enhanced_caption = generate_mediainfo_caption(current_caption, caption_data)
        
        if current_caption == enhanced_caption:
            LOGGER.warning("⚠️ No caption changes generated")
            return False
        
        # Update caption
        return await safe_edit_caption(message, current_caption, enhanced_caption)
        
    except Exception as e:
        LOGGER.error(f"💥 MediaInfo processing error: {e}")
        return False

async def async_subprocess(cmd):
    """Run subprocess command with timeout"""
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode() if stdout else ""
    except Exception as e:
        LOGGER.error(f"Subprocess error: {e}")
        return ""

def extract_caption_metadata(mediainfo_json):
    """Extract metadata from MediaInfo JSON"""
    try:
        tracks = mediainfo_json.get("media", {}).get("track", [])
        
        video_info = None
        audio_tracks = []
        
        for track in tracks:
            track_type = track.get("@type", "").lower()
            
            if track_type == "video" and not video_info:
                codec = track.get("Format", "Unknown")
                width = track.get("Width")
                height = track.get("Height")
                
                video_info = {
                    "codec": codec,
                    "width": int(width) if width else None,
                    "height": int(height) if height else None
                }
                
            elif track_type == "audio":
                codec = track.get("Format", "Unknown")
                language = track.get("Language", "Unknown")
                channels = track.get("Channels")
                
                audio_tracks.append({
                    "codec": codec,
                    "language": language,
                    "channels": int(channels) if channels else 1
                })
        
        return {
            "video": video_info,
            "audio": audio_tracks
        }
        
    except Exception as e:
        LOGGER.error(f"Metadata extraction error: {e}")
        return None

def generate_mediainfo_caption(original_caption, metadata):
    """Generate enhanced caption"""
    try:
        enhanced = original_caption.strip() if original_caption else ""
        mediainfo_lines = []
        
        # Video info
        video = metadata.get("video")
        if video and video.get("codec"):
            codec = video["codec"]
            height = video.get("height")
            
            resolution = ""
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
            
            video_line = f"Video: {codec}"
            if resolution:
                video_line += f" {resolution}"
            
            mediainfo_lines.append(video_line)
        
        # Audio info
        audio_tracks = metadata.get("audio", [])
        if audio_tracks:
            count = len(audio_tracks)
            
            languages = []
            for audio in audio_tracks:
                lang = audio.get("language", "Unknown").upper()
                if lang and lang not in ["UNKNOWN", "UND"] and lang not in languages:
                    lang_map = {"EN": "ENG", "HI": "HIN", "ES": "SPA"}
                    lang = lang_map.get(lang, lang)
                    languages.append(lang)
            
            audio_line = f"Audio: {count}"
            if languages:
                audio_line += f" ({', '.join(languages[:3])})"
            
            mediainfo_lines.append(audio_line)
        
        # Combine
        if mediainfo_lines:
            mediainfo_section = "\n\n" + "\n".join(mediainfo_lines)
            enhanced_caption = enhanced + mediainfo_section
            
            if len(enhanced_caption) > 1020:
                max_original = 1020 - len(mediainfo_section) - 5
                if max_original > 0:
                    enhanced_caption = enhanced[:max_original] + "..." + mediainfo_section
                else:
                    enhanced_caption = mediainfo_section
            
            return enhanced_caption
        
        return enhanced
        
    except Exception as e:
        LOGGER.error(f"Caption generation error: {e}")
        return original_caption or ""

# Helper functions (same as before)
async def has_media(msg):
    return bool(msg.video or msg.audio or msg.document)

async def already_has_mediainfo(msg):
    caption = msg.caption or ""
    return "Video:" in caption and "Audio:" in caption

async def safe_edit_caption(msg, current_caption, new_caption):
    try:
        if current_caption == new_caption:
            return False
        
        if "Video:" not in new_caption and "Audio:" not in new_caption:
            return False
        
        await TgClient.user.edit_message_caption(
            chat_id=msg.chat.id,
            message_id=msg.id,
            caption=new_caption
        )
        return True
        
    except MessageNotModified:
        return False
    except Exception as e:
        LOGGER.error(f"Caption edit error: {e}")
        return False

async def get_target_channels(message):
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
