"""
Enhanced MediaInfo with multi-chunk extraction and clean output
"""

import asyncio
import logging
import os
import json
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove
from pyrogram.errors import MessageNotModified
from bot.core.client import TgClient
from bot.helpers.message_utils import send_message, edit_message

LOGGER = logging.getLogger(__name__)

# Enhanced Configuration
CHUNK_STEPS = [5, 10, 15]  # Number of chunks to try in sequence
FULL_DOWNLOAD_LIMIT = 200 * 1024 * 1024  # 200MB for full download fallback
MEDIAINFO_TIMEOUT = 30

async def updatemediainfo_handler(client, message):
    """Handler with iterative chunk-based MediaInfo extraction"""
    try:
        LOGGER.info("🚀 Starting iterative chunk-based MediaInfo processing")
        
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, "❌ **Usage:** `/updatemediainfo -1001234567890`")
            return
        
        for channel_id in channels:
            await process_channel_enhanced(channel_id, message)
            
    except Exception as e:
        LOGGER.error(f"💥 Handler error: {e}", exc_info=True)
        await send_message(message, f"❌ **Error:** {e}")

async def process_channel_enhanced(channel_id, message):
    """Process channel with iterative chunk approach"""
    try:
        chat = await TgClient.user.get_chat(channel_id)
        LOGGER.info(f"✅ Processing channel: {chat.title}")
        
        progress_msg = await send_message(message,
            f"🔄 **Processing:** {chat.title}\n"
            f"📊 **Method:** Iterative Chunks ({', '.join(map(str, CHUNK_STEPS))})\n"
            f"📝 **Output:** Clean & Essential\n"
            f"🔍 **Status:** Starting...")
        
        stats = {
            "processed": 0, "errors": 0, "skipped": 0, 
            "chunk_success": {step: 0 for step in CHUNK_STEPS},
            "full_success": 0, "total": 0, "media": 0
        }
        
        message_count = 0
        async for msg in TgClient.user.get_chat_history(chat_id=channel_id, limit=100):
            message_count += 1
            stats["total"] += 1
            
            if not await has_media(msg):
                stats["skipped"] += 1
                continue
            
            if await already_has_mediainfo(msg):
                stats["skipped"] += 1
                continue
            
            stats["media"] += 1
            LOGGER.info(f"🎯 Processing media message {msg.id}")
            
            try:
                success, method = await process_message_enhanced(TgClient.user, msg)
                if success:
                    stats["processed"] += 1
                    if "chunk" in method:
                        step = int(method.replace('chunk', ''))
                        stats["chunk_success"][step] += 1
                    elif method == "full":
                        stats["full_success"] += 1
                    LOGGER.info(f"✅ Updated message {msg.id} using {method}")
                else:
                    stats["errors"] += 1
            except Exception as e:
                LOGGER.error(f"❌ Error processing {msg.id}: {e}")
                stats["errors"] += 1
            
            # Progress update
            if message_count % 5 == 0:
                chunk_stats = " | ".join([f"C{k}:{v}" for k, v in stats['chunk_success'].items()])
                await edit_message(progress_msg,
                    f"🔄 **Processing:** {chat.title}\n"
                    f"📊 **Messages:** {stats['total']} | **Media:** {stats['media']}\n"
                    f"✅ **Updated:** {stats['processed']} | ❌ **Errors:** {stats['errors']}\n"
                    f"📦 **Chunks:** {chunk_stats} | **Full:** {stats['full_success']}")
                await asyncio.sleep(0.5)
        
        # Final results
        chunk_stats = "\n".join([f"📦 **{k} Chunks:** {v} files" for k, v in stats['chunk_success'].items()])
        final_stats = (
            f"✅ **Completed:** {chat.title}\n"
            f"📊 **Total:** {stats['total']} | **Media:** {stats['media']}\n"
            f"✅ **Updated:** {stats['processed']} files\n"
            f"❌ **Errors:** {stats['errors']} | ⏭️ **Skipped:** {stats['skipped']}\n\n"
            f"{chunk_stats}\n"
            f"📥 **Full:** {stats['full_success']} files"
        )
        
        await edit_message(progress_msg, final_stats)
        LOGGER.info(f"🎉 Enhanced processing complete: {stats['processed']} updated")
        
    except Exception as e:
        LOGGER.error(f"💥 Channel processing error: {e}")

async def process_message_enhanced(client, message):
    """Process message with iterative chunk strategy"""
    temp_file = None
    try:
        media = message.video or message.audio or message.document
        if not media:
            return False, "none"

        filename = str(media.file_name) if media.file_name else f"media_{message.id}"
        file_size = media.file_size
        
        temp_dir = "temp_mediainfo"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        temp_file = os.path.join(temp_dir, f"temp_{message.id}.tmp")

        # Iterative chunk download strategy
        for step in CHUNK_STEPS:
            LOGGER.info(f"📦 Trying with {step} chunks for {filename}")
            try:
                async with aiopen(temp_file, "wb") as f:
                    chunk_count = 0
                    async for chunk in client.stream_media(message, limit=step):
                        await f.write(chunk)
                        chunk_count += 1
                
                if chunk_count > 0:
                    metadata = await extract_mediainfo_from_file(temp_file)
                    if metadata:
                        video_info, audio_tracks = parse_essential_metadata(metadata)
                        if video_info or audio_tracks:
                            success = await update_caption_clean(message, video_info, audio_tracks)
                            if success:
                                await cleanup_files([temp_file])
                                return True, f"chunk{step}"
            except Exception as e:
                LOGGER.warning(f"⚠️ Error during {step}-chunk attempt: {e}")

        # Fallback: Full download for smaller files
        if file_size <= FULL_DOWNLOAD_LIMIT:
            LOGGER.info(f"📥 Fallback: Full download for {filename} ({file_size/1024/1024:.1f}MB)")
            try:
                await asyncio.wait_for(message.download(temp_file), timeout=300.0)
                metadata = await extract_mediainfo_from_file(temp_file)
                if metadata:
                    video_info, audio_tracks = parse_essential_metadata(metadata)
                    if video_info or audio_tracks:
                        success = await update_caption_clean(message, video_info, audio_tracks)
                        if success:
                            await cleanup_files([temp_file])
                            return True, "full"
            except asyncio.TimeoutError:
                LOGGER.warning("⚠️ Full download timed out")
        
        await cleanup_files([temp_file])
        return False, "failed"
        
    except Exception as e:
        LOGGER.error(f"💥 Enhanced processing error: {e}")
        await cleanup_files([temp_file])
        return False, "error"

async def extract_mediainfo_from_file(file_path):
    """Extract MediaInfo from file"""
    try:
        proc = await asyncio.create_subprocess_shell(
            f'mediainfo "{file_path}" --Output=JSON',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=MEDIAINFO_TIMEOUT)
        
        if stdout:
            return json.loads(stdout.decode())
        
        return None
        
    except Exception as e:
        LOGGER.debug(f"MediaInfo extraction error: {e}")
        return None

def parse_essential_metadata(metadata):
    """Parse only essential metadata for clean output"""
    try:
        tracks = metadata.get("media", {}).get("track", [])
        
        video_info = None
        audio_tracks = []
        
        for track in tracks:
            track_type = track.get("@type", "").lower()
            
            # Extract video info (codec + resolution)
            if track_type == "video" and not video_info:
                codec = track.get("Format", "Unknown").split('/')[0].strip().upper()
                
                # Get height for quality determination
                height = None
                height_str = track.get("Height", "")
                if height_str:
                    try:
                        height = int(''.join(filter(str.isdigit, str(height_str))))
                    except:
                        pass
                
                video_info = {
                    "codec": codec,
                    "height": height
                }
                
            # Extract audio info (language only, filter out undefined)
            elif track_type == "audio":
                language = track.get("Language", "").upper()
                
                # Filter out undefined/unknown languages
                if language and language not in ["UND", "UNDEFINED", "UNKNOWN", "N/A", ""]:
                    # Standardize common language codes
                    lang_map = {
                        "EN": "ENG", "ENGLISH": "ENG",
                        "HI": "HIN", "HINDI": "HIN", 
                        "ES": "SPA", "SPANISH": "SPA",
                        "FR": "FRA", "FRENCH": "FRA",
                        "DE": "GER", "GERMAN": "GER"
                    }
                    language = lang_map.get(language, language)
                    audio_tracks.append({"language": language})
                else:
                    # Count audio tracks even without language
                    audio_tracks.append({"language": None})
        
        LOGGER.debug(f"📊 Parsed: video={video_info}, audio_tracks={len(audio_tracks)}")
        return video_info, audio_tracks
        
    except Exception as e:
        LOGGER.error(f"💥 Metadata parsing error: {e}")
        return None, []

async def update_caption_clean(message, video_info, audio_tracks):
    """Update caption with clean, minimal format"""
    try:
        current_caption = message.caption or ""
        mediainfo_lines = []
        
        # Clean Video line: "Video: H264 1080p"
        if video_info and video_info.get("codec"):
            codec = video_info["codec"]
            height = video_info.get("height")
            
            # Determine quality
            quality = ""
            if height:
                if height >= 2160:
                    quality = "4K"
                elif height >= 1440:
                    quality = "1440p"
                elif height >= 1080:
                    quality = "1080p"
                elif height >= 720:
                    quality = "720p"
                elif height >= 480:
                    quality = "480p"
                else:
                    quality = f"{height}p"
            
            # Build clean video line
            video_line = f"Video: {codec}"
            if quality:
                video_line += f" {quality}"
            
            mediainfo_lines.append(video_line)
            LOGGER.info(f"📹 Clean video line: {video_line}")
        
        # Clean Audio line: "Audio: 2 (ENG, SPA)" or "Audio: 1"
        if audio_tracks:
            track_count = len(audio_tracks)
            
            # Get unique languages (filter out None)
            languages = []
            for track in audio_tracks:
                lang = track.get("language")
                if lang and lang not in languages:
                    languages.append(lang)
            
            # Build clean audio line
            audio_line = f"Audio: {track_count}"
            if languages:
                audio_line += f" ({', '.join(languages)})"
            
            mediainfo_lines.append(audio_line)
            LOGGER.info(f"🎵 Clean audio line: {audio_line}")
        
        if not mediainfo_lines:
            LOGGER.warning("⚠️ No MediaInfo lines generated")
            return False
        
        # Create clean enhanced caption
        enhanced = current_caption.strip()
        mediainfo_section = "\n\n" + "\n".join(mediainfo_lines)
        enhanced_caption = enhanced + mediainfo_section
        
        # Telegram length limit
        if len(enhanced_caption) > 1020:
            max_original = 1020 - len(mediainfo_section) - 5
            if max_original > 0:
                enhanced_caption = enhanced[:max_original] + "..." + mediainfo_section
            else:
                enhanced_caption = mediainfo_section
        
        # Update if changed
        if current_caption == enhanced_caption:
            LOGGER.warning("⚠️ Caption unchanged")
            return False
        
        try:
            await TgClient.user.edit_message_caption(
                chat_id=message.chat.id,
                message_id=message.id,
                caption=enhanced_caption
            )
            LOGGER.info("✅ Clean caption updated successfully")
            return True
            
        except MessageNotModified:
            LOGGER.info("ℹ️ Message not modified by Telegram")
            return False
        
    except Exception as e:
        LOGGER.error(f"💥 Clean caption update error: {e}")
        return False

async def cleanup_files(file_paths):
    """Clean up temporary files"""
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                await aioremove(file_path)
                LOGGER.debug(f"🗑️ Cleaned up: {file_path}")
        except Exception as e:
            LOGGER.debug(f"Cleanup warning: {e}")

# Helper functions
async def has_media(msg):
    return bool(msg.video or msg.audio or msg.document)

async def already_has_mediainfo(msg):
    caption = msg.caption or ""
    return "Video:" in caption and "Audio:" in caption

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
