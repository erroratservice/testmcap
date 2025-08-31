"""
MediaInfo update using CLI approach (based on proven Telegram implementation)
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

async def updatemediainfo_handler(client, message):
    """Handler using MediaInfo CLI approach"""
    try:
        LOGGER.info("🚀 Starting updatemediainfo with MediaInfo CLI approach")
        
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, 
                "❌ **Usage:**\n• `/updatemediainfo -1001234567890`")
            return
        
        for channel_id in channels:
            await process_channel_with_mediainfo_cli(channel_id, message)
            
    except Exception as e:
        LOGGER.error(f"💥 Handler error: {e}", exc_info=True)
        await send_message(message, f"❌ **Error:** {e}")

async def process_channel_with_mediainfo_cli(channel_id, message):
    """Process channel using MediaInfo CLI approach"""
    try:
        # Access channel
        chat = await TgClient.user.get_chat(channel_id)
        
        progress_msg = await send_message(message,
            f"🔄 **Processing:** {chat.title}\n"
            f"📊 **Method:** MediaInfo CLI (50MB→5MB strategy)\n"
            f"🔍 **Status:** Scanning messages...")
        
        processed = 0
        errors = 0
        skipped = 0
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
            
            try:
                success = await process_telegram_media_with_cli(TgClient.user, msg)
                if success:
                    processed += 1
                    LOGGER.info(f"✅ Updated message {msg.id}")
                else:
                    errors += 1
            except Exception as e:
                LOGGER.error(f"❌ Error processing {msg.id}: {e}")
                errors += 1
            
            # Progress update
            if message_count % 10 == 0:
                await edit_message(progress_msg,
                    f"🔄 **Processing:** {chat.title}\n"
                    f"📊 **Messages:** {total_messages} | **Media:** {media_found}\n"
                    f"✅ **Updated:** {processed} | ❌ **Errors:** {errors} | ⏭️ **Skipped:** {skipped}")
                await asyncio.sleep(0.5)
        
        # Final results
        final_stats = (
            f"✅ **Completed:** {chat.title}\n"
            f"📊 **Total Messages:** {total_messages}\n"
            f"📁 **Media Found:** {media_found}\n"
            f"✅ **Updated:** {processed} files\n"
            f"❌ **Errors:** {errors} files\n"
            f"⏭️ **Skipped:** {skipped} files"
        )
        
        await edit_message(progress_msg, final_stats)
        
    except Exception as e:
        LOGGER.error(f"💥 Channel processing error: {e}")
        await send_message(message, f"❌ **Error:** {str(e)}")

async def process_telegram_media_with_cli(client, message):
    """
    Process Telegram media using MediaInfo CLI (adapted from working implementation)
    """
    try:
        # Get media object
        media = None
        if message.video:
            media = message.video
        elif message.audio:
            media = message.audio
        elif message.document:
            media = message.document
        else:
            return False
        
        filename = str(media.file_name) if media.file_name else f"media_{message.id}"
        size = media.file_size
        
        # Create temp file
        rand_str = f"mediainfo_{message.id}"
        download_path = f"/tmp/{rand_str}_{filename}"
        
        # Smart download strategy (same as proven implementation)
        if int(size) <= 50000000:  # 50MB - full download
            LOGGER.info(f"📥 Full download: {filename} ({size/1024/1024:.1f}MB)")
            await message.download(download_path)
        else:  # Large files - partial download (5 chunks)
            LOGGER.info(f"📥 Partial download: {filename} ({size/1024/1024:.1f}MB, 5 chunks)")
            async for chunk in client.stream_media(message, limit=5):
                with open(download_path, "ab") as f:
                    f.write(chunk)
        
        # Extract MediaInfo using CLI (dual output)
        LOGGER.debug(f"🔍 Running MediaInfo CLI on: {download_path}")
        
        # Get both text and JSON output
        mediainfo_text = await async_subprocess(f"mediainfo '{download_path}'")
        mediainfo_json_text = await async_subprocess(f"mediainfo '{download_path}' --Output=JSON")
        
        if not mediainfo_text or not mediainfo_json_text:
            LOGGER.warning(f"⚠️ MediaInfo failed for {filename}")
            return False
        
        try:
            mediainfo_json = json.loads(mediainfo_json_text)
        except json.JSONDecodeError:
            LOGGER.warning(f"⚠️ MediaInfo JSON parse failed for {filename}")
            return False
        
        # Parse and clean MediaInfo output
        lines = mediainfo_text.splitlines()
        cleaned_lines = []
        
        for line in lines:
            # Remove problematic lines (from proven implementation)
            if "IsTruncated" in line or "FileExtension_Invalid" in line:
                continue
            # Update file size info
            elif "File size" in line:
                readable_size = f"{size/1024/1024:.1f} MiB"
                line = re.sub(r": .+", f": {readable_size}", line)
            # Update complete name
            elif "Complete name" in line:
                line = re.sub(r": .+", f": {filename}", line)
            
            cleaned_lines.append(line)
        
        # Extract essential metadata for caption
        caption_data = extract_caption_metadata(mediainfo_json)
        if not caption_data:
            LOGGER.warning(f"⚠️ No usable metadata extracted from {filename}")
            return False
        
        # Generate enhanced caption
        current_caption = message.caption or ""
        enhanced_caption = generate_mediainfo_caption(current_caption, caption_data)
        
        # Update caption
        success = await safe_edit_caption(message, current_caption, enhanced_caption)
        
        # Cleanup
        try:
            os.remove(download_path)
        except:
            pass
        
        return success
        
    except Exception as e:
        LOGGER.error(f"💥 MediaInfo CLI processing error: {e}")
        return False

async def async_subprocess(cmd):
    """Run subprocess command asynchronously"""
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if stderr:
            LOGGER.warning(f"MediaInfo stderr: {stderr.decode()}")
        
        return stdout.decode() if stdout else ""
        
    except Exception as e:
        LOGGER.error(f"Subprocess error: {e}")
        return ""

def extract_caption_metadata(mediainfo_json):
    """Extract metadata for caption generation"""
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
    """Generate enhanced caption with MediaInfo"""
    try:
        enhanced = original_caption.strip() if original_caption else ""
        mediainfo_lines = []
        
        # Video info
        video = metadata.get("video")
        if video and video.get("codec"):
            codec = video["codec"]
            height = video.get("height")
            
            # Resolution
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
            
            # Languages
            languages = []
            for audio in audio_tracks:
                lang = audio.get("language", "Unknown").upper()
                if lang and lang not in ["UNKNOWN", "UND"] and lang not in languages:
                    # Standardize
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
        LOGGER.error(f"Caption generation error: {e}")
        return original_caption or ""

# ... [Include helper functions: has_media, already_has_mediainfo, safe_edit_caption, get_target_channels] ...

async def has_media(msg):
    """Check if message has media"""
    return bool(msg.video or msg.audio or msg.document)

async def already_has_mediainfo(msg):
    """Check if already has MediaInfo"""
    caption = msg.caption or ""
    return "Video:" in caption and "Audio:" in caption

async def safe_edit_caption(msg, current_caption, new_caption):
    """Safe caption editing"""
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
