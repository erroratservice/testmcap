"""
MediaInfo update with comprehensive debugging and fallback strategies
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
    """Handler with enhanced debugging"""
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
    """Process channel with comprehensive debugging"""
    try:
        # Access channel
        chat = await TgClient.user.get_chat(channel_id)
        LOGGER.info(f"✅ Accessing channel: {chat.title}")
        
        progress_msg = await send_message(message,
            f"🔄 **Processing:** {chat.title}\n"
            f"📊 **Method:** MediaInfo CLI (Enhanced Debug)\n"
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
            
            LOGGER.debug(f"📨 Processing message {message_count}: ID={msg.id}")
            
            # Check for media
            if not await has_media(msg):
                LOGGER.debug(f"⏭️ Skipping message {msg.id}: No media")
                skipped += 1
                continue
            
            # Check if already processed
            if await already_has_mediainfo(msg):
                LOGGER.debug(f"⏭️ Skipping message {msg.id}: Already has MediaInfo")
                skipped += 1
                continue
            
            media_found += 1
            LOGGER.info(f"🎯 Processing media message {msg.id}")
            
            try:
                success, error_details = await process_telegram_media_with_debug(TgClient.user, msg)
                if success:
                    processed += 1
                    LOGGER.info(f"✅ Successfully updated message {msg.id}")
                else:
                    errors += 1
                    LOGGER.error(f"❌ Failed to update message {msg.id}: {error_details}")
                    
            except Exception as e:
                LOGGER.error(f"💥 Exception processing message {msg.id}: {e}", exc_info=True)
                errors += 1
            
            # Progress update
            if message_count % 5 == 0:
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
        LOGGER.info(f"🎉 Final results: Updated={processed}, Errors={errors}, Skipped={skipped}")
        
    except Exception as e:
        LOGGER.error(f"💥 Channel processing error: {e}", exc_info=True)
        await send_message(message, f"❌ **Error:** {str(e)}")

async def process_telegram_media_with_debug(client, message):
    """
    Process Telegram media with comprehensive debugging
    """
    download_path = None
    try:
        LOGGER.info(f"🔄 Starting debug processing for message {message.id}")
        
        # Step 1: Get media object
        media = None
        media_type = None
        if message.video:
            media = message.video
            media_type = "video"
        elif message.audio:
            media = message.audio
            media_type = "audio"
        elif message.document:
            media = message.document
            media_type = "document"
        else:
            LOGGER.error(f"❌ No supported media found in message {message.id}")
            return False, "No supported media type"
        
        filename = str(media.file_name) if media.file_name else f"media_{message.id}"
        size = media.file_size
        
        LOGGER.info(f"📁 Media info: {media_type}, filename={filename}, size={size/1024/1024:.1f}MB")
        
        # Step 2: Create temp file and download
        rand_str = f"debug_{message.id}"
        download_path = f"/tmp/{rand_str}_{filename.replace('/', '_')}"
        
        LOGGER.debug(f"📥 Download path: {download_path}")
        
        # Smart download strategy with enhanced logging
        if int(size) <= 50000000:  # 50MB - full download
            LOGGER.info(f"📥 Full download: {filename} ({size/1024/1024:.1f}MB)")
            try:
                await message.download(download_path)
                LOGGER.info(f"✅ Full download completed")
            except Exception as e:
                LOGGER.error(f"❌ Full download failed: {e}")
                return False, f"Full download failed: {e}"
        else:  # Large files - partial download with more chunks
            LOGGER.info(f"📥 Partial download: {filename} ({size/1024/1024:.1f}MB, 10 chunks)")
            try:
                chunk_count = 0
                async for chunk in client.stream_media(message, limit=10):  # Increased from 5 to 10
                    with open(download_path, "ab") as f:
                        f.write(chunk)
                    chunk_count += 1
                LOGGER.info(f"✅ Partial download completed: {chunk_count} chunks")
            except Exception as e:
                LOGGER.error(f"❌ Partial download failed: {e}")
                return False, f"Partial download failed: {e}"
        
        # Step 3: Verify downloaded file
        if not os.path.exists(download_path):
            LOGGER.error(f"❌ Downloaded file not found: {download_path}")
            return False, "Downloaded file not found"
        
        downloaded_size = os.path.getsize(download_path)
        LOGGER.info(f"📊 Downloaded file size: {downloaded_size/1024/1024:.1f}MB")
        
        if downloaded_size == 0:
            LOGGER.error(f"❌ Downloaded file is empty")
            return False, "Downloaded file is empty"
        
        # Step 4: Extract MediaInfo with enhanced error handling
        LOGGER.debug(f"🔍 Running MediaInfo CLI on: {download_path}")
        
        try:
            # Get both text and JSON output
            mediainfo_text = await async_subprocess_debug(f"mediainfo '{download_path}'")
            mediainfo_json_text = await async_subprocess_debug(f"mediainfo '{download_path}' --Output=JSON")
            
            LOGGER.debug(f"📊 MediaInfo text output length: {len(mediainfo_text) if mediainfo_text else 0}")
            LOGGER.debug(f"📊 MediaInfo JSON output length: {len(mediainfo_json_text) if mediainfo_json_text else 0}")
            
            if not mediainfo_text and not mediainfo_json_text:
                LOGGER.error(f"❌ MediaInfo CLI produced no output")
                return False, "MediaInfo CLI produced no output"
            
            # Show first 500 chars of output for debugging
            if mediainfo_text:
                LOGGER.debug(f"📝 MediaInfo text preview: {mediainfo_text[:500]}...")
            if mediainfo_json_text:
                LOGGER.debug(f"📝 MediaInfo JSON preview: {mediainfo_json_text[:500]}...")
            
        except Exception as e:
            LOGGER.error(f"❌ MediaInfo CLI execution failed: {e}")
            return False, f"MediaInfo CLI execution failed: {e}"
        
        # Step 5: Parse JSON output
        mediainfo_json = None
        if mediainfo_json_text:
            try:
                mediainfo_json = json.loads(mediainfo_json_text)
                track_count = len(mediainfo_json.get("media", {}).get("track", []))
                LOGGER.info(f"✅ Parsed MediaInfo JSON: {track_count} tracks found")
            except json.JSONDecodeError as e:
                LOGGER.error(f"❌ MediaInfo JSON parse failed: {e}")
                return False, f"MediaInfo JSON parse failed: {e}"
        else:
            LOGGER.error(f"❌ No MediaInfo JSON output to parse")
            return False, "No MediaInfo JSON output"
        
        # Step 6: Extract caption metadata
        caption_data = extract_caption_metadata_debug(mediainfo_json, message.id)
        if not caption_data:
            LOGGER.error(f"❌ No usable metadata extracted for caption")
            return False, "No usable metadata extracted"
        
        LOGGER.info(f"✅ Metadata extracted: Video={bool(caption_data.get('video'))}, Audio={len(caption_data.get('audio', []))}")
        
        # Step 7: Generate enhanced caption
        current_caption = message.caption or ""
        enhanced_caption = generate_mediainfo_caption_debug(current_caption, caption_data, message.id)
        
        LOGGER.debug(f"📝 Current caption length: {len(current_caption)}")
        LOGGER.debug(f"📝 Enhanced caption length: {len(enhanced_caption)}")
        
        if current_caption == enhanced_caption:
            LOGGER.warning(f"⚠️ No caption changes detected for message {message.id}")
            return False, "No caption changes detected"
        
        # Step 8: Update caption
        success = await safe_edit_caption_debug(message, current_caption, enhanced_caption)
        
        if success:
            LOGGER.info(f"✅ Caption updated successfully for message {message.id}")
            return True, "Success"
        else:
            LOGGER.warning(f"⚠️ Caption update failed for message {message.id}")
            return False, "Caption update failed"
        
    except Exception as e:
        LOGGER.error(f"💥 Processing exception for message {message.id}: {e}", exc_info=True)
        return False, f"Processing exception: {e}"
    finally:
        # Cleanup
        if download_path and os.path.exists(download_path):
            try:
                os.remove(download_path)
                LOGGER.debug(f"🗑️ Cleaned up: {download_path}")
            except:
                pass

async def async_subprocess_debug(cmd):
    """Run subprocess with enhanced debugging"""
    try:
        LOGGER.debug(f"🔧 Running command: {cmd}")
        
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        LOGGER.debug(f"📊 Command return code: {proc.returncode}")
        
        if stderr:
            stderr_text = stderr.decode()
            LOGGER.warning(f"⚠️ Command stderr: {stderr_text[:500]}...")
        
        if stdout:
            stdout_text = stdout.decode()
            LOGGER.debug(f"✅ Command stdout length: {len(stdout_text)}")
            return stdout_text
        else:
            LOGGER.warning(f"⚠️ Command produced no stdout")
            return ""
        
    except Exception as e:
        LOGGER.error(f"💥 Subprocess error: {e}")
        return ""

def extract_caption_metadata_debug(mediainfo_json, message_id):
    """Extract metadata with detailed debugging"""
    try:
        LOGGER.debug(f"🔍 Extracting metadata for message {message_id}")
        
        if not mediainfo_json:
            LOGGER.error(f"❌ No MediaInfo JSON provided for message {message_id}")
            return None
        
        tracks = mediainfo_json.get("media", {}).get("track", [])
        LOGGER.debug(f"📊 Processing {len(tracks)} tracks")
        
        video_info = None
        audio_tracks = []
        
        for i, track in enumerate(tracks):
            track_type = track.get("@type", "").lower()
            LOGGER.debug(f"🎬 Track {i}: Type={track_type}")
            
            if track_type == "video" and not video_info:
                codec = track.get("Format", "Unknown")
                width = track.get("Width")
                height = track.get("Height")
                
                video_info = {
                    "codec": codec,
                    "width": int(width) if width else None,
                    "height": int(height) if height else None
                }
                LOGGER.debug(f"📹 Video info: {video_info}")
                
            elif track_type == "audio":
                codec = track.get("Format", "Unknown")
                language = track.get("Language", "Unknown")
                channels = track.get("Channels")
                
                audio_track = {
                    "codec": codec,
                    "language": language,
                    "channels": int(channels) if channels else 1
                }
                audio_tracks.append(audio_track)
                LOGGER.debug(f"🎵 Audio track: {audio_track}")
        
        result = {
            "video": video_info,
            "audio": audio_tracks
        }
        
        LOGGER.info(f"✅ Metadata extracted: Video={bool(video_info)}, Audio={len(audio_tracks)} tracks")
        return result
        
    except Exception as e:
        LOGGER.error(f"💥 Metadata extraction error for message {message_id}: {e}")
        return None

def generate_mediainfo_caption_debug(original_caption, metadata, message_id):
    """Generate caption with debugging"""
    try:
        LOGGER.debug(f"✏️ Generating caption for message {message_id}")
        
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
            LOGGER.debug(f"📹 Video line: {video_line}")
        
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
            LOGGER.debug(f"🎵 Audio line: {audio_line}")
        
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
            
            LOGGER.debug(f"✅ Generated caption: {len(enhanced_caption)} chars, {len(mediainfo_lines)} info lines")
            return enhanced_caption
        else:
            LOGGER.warning(f"⚠️ No MediaInfo lines generated for message {message_id}")
            return enhanced
        
    except Exception as e:
        LOGGER.error(f"💥 Caption generation error for message {message_id}: {e}")
        return original_caption or ""

async def safe_edit_caption_debug(msg, current_caption, new_caption):
    """Safe caption editing with debugging"""
    try:
        LOGGER.debug(f"📝 Attempting caption update for message {msg.id}")
        
        if current_caption == new_caption:
            LOGGER.warning(f"⚠️ Captions are identical for message {msg.id}")
            return False
        
        if "Video:" not in new_caption and "Audio:" not in new_caption:
            LOGGER.warning(f"⚠️ No MediaInfo content in caption for message {msg.id}")
            return False
        
        try:
            await TgClient.user.edit_message_caption(
                chat_id=msg.chat.id,
                message_id=msg.id,
                caption=new_caption
            )
            LOGGER.info(f"✅ Caption edit successful for message {msg.id}")
            return True
            
        except MessageNotModified as e:
            LOGGER.warning(f"⚠️ Message not modified for message {msg.id}: {e}")
            return False
        except Exception as e:
            LOGGER.error(f"❌ Caption edit failed for message {msg.id}: {e}")
            return False
        
    except Exception as e:
        LOGGER.error(f"💥 Caption edit exception for message {msg.id}: {e}")
        return False

# Helper functions
async def has_media(msg):
    """Check if message has media"""
    result = bool(msg.video or msg.audio or msg.document)
    LOGGER.debug(f"📱 Message {msg.id} has media: {result}")
    return result

async def already_has_mediainfo(msg):
    """Check if already has MediaInfo"""
    caption = msg.caption or ""
    result = "Video:" in caption and "Audio:" in caption
    LOGGER.debug(f"📝 Message {msg.id} already has MediaInfo: {result}")
    return result

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
    except Exception as e:
        LOGGER.error(f"Channel parsing error: {e}")
        return []
