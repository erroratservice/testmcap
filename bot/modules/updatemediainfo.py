"""
Enhanced MediaInfo with multi-chunk extraction and clean output
"""

import asyncio
import logging
import os
import json
import tempfile
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove
from pyrogram.errors import MessageNotModified
from bot.core.client import TgClient
from bot.helpers.message_utils import send_message, edit_message

LOGGER = logging.getLogger(__name__)

# Enhanced Configuration
CHUNK_SIZE_MB = 50  # 50MB per chunk
MAX_CHUNKS = 3      # Maximum 3 chunks (150MB total)
FULL_DOWNLOAD_LIMIT = 200 * 1024 * 1024  # 200MB for full download fallback
MEDIAINFO_TIMEOUT = 30

async def updatemediainfo_handler(client, message):
    """Enhanced handler with multi-chunk extraction"""
    try:
        LOGGER.info("🚀 Starting enhanced multi-chunk MediaInfo processing")
        
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
    """Process channel with enhanced multi-chunk approach"""
    try:
        chat = await TgClient.user.get_chat(channel_id)
        LOGGER.info(f"✅ Processing channel: {chat.title}")
        
        progress_msg = await send_message(message,
            f"🔄 **Processing:** {chat.title}\n"
            f"📊 **Method:** Multi-Chunk Enhanced\n"
            f"🎯 **Strategy:** 3 Chunks × 50MB = 150MB Max\n"
            f"📝 **Output:** Clean & Essential\n"
            f"🔍 **Status:** Starting...")
        
        stats = {
            "processed": 0, "errors": 0, "skipped": 0, 
            "chunk1_success": 0, "chunk2_success": 0, "chunk3_success": 0,
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
                    if method == "chunk1":
                        stats["chunk1_success"] += 1
                    elif method == "chunk2":
                        stats["chunk2_success"] += 1
                    elif method == "chunk3":
                        stats["chunk3_success"] += 1
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
                await edit_message(progress_msg,
                    f"🔄 **Processing:** {chat.title}\n"
                    f"📊 **Messages:** {stats['total']} | **Media:** {stats['media']}\n"
                    f"✅ **Updated:** {stats['processed']} | ❌ **Errors:** {stats['errors']}\n"
                    f"📦 **C1:** {stats['chunk1_success']} | **C2:** {stats['chunk2_success']} | **C3:** {stats['chunk3_success']} | **Full:** {stats['full_success']}")
                await asyncio.sleep(0.5)
        
        # Final results
        final_stats = (
            f"✅ **Completed:** {chat.title}\n"
            f"📊 **Total:** {stats['total']} | **Media:** {stats['media']}\n"
            f"✅ **Updated:** {stats['processed']} files\n"
            f"❌ **Errors:** {stats['errors']} | ⏭️ **Skipped:** {stats['skipped']}\n\n"
            f"📦 **Chunk 1:** {stats['chunk1_success']} files\n"
            f"📦 **Chunk 2:** {stats['chunk2_success']} files\n"
            f"📦 **Chunk 3:** {stats['chunk3_success']} files\n"
            f"📥 **Full:** {stats['full_success']} files"
        )
        
        await edit_message(progress_msg, final_stats)
        LOGGER.info(f"🎉 Enhanced processing complete: {stats['processed']} updated")
        
    except Exception as e:
        LOGGER.error(f"💥 Channel processing error: {e}")

async def process_message_enhanced(client, message):
    """Process message with multi-chunk strategy"""
    temp_files = []
    try:
        # Get media info
        media = message.video or message.audio or message.document
        if not media:
            return False, "none"
        
        filename = str(media.file_name) if media.file_name else f"media_{message.id}"
        file_size = media.file_size
        
        LOGGER.info(f"📁 Processing: {filename} ({file_size/1024/1024:.1f}MB)")
        
        # Create temp directory
        temp_dir = "temp_mediainfo"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # Multi-chunk strategy (up to 3 chunks = 150MB total)
        for chunk_num in range(1, MAX_CHUNKS + 1):
            LOGGER.info(f"📦 Trying chunk {chunk_num}/3 ({CHUNK_SIZE_MB}MB)")
            
            # Download chunk
            chunk_path = await download_chunk(client, message, chunk_num, temp_dir)
            if not chunk_path:
                continue
            
            temp_files.append(chunk_path)
            
            # Try to extract MediaInfo from accumulated chunks
            combined_path = await combine_chunks(temp_files, temp_dir, message.id)
            if combined_path:
                metadata = await extract_mediainfo_from_file(combined_path)
                if metadata:
                    video_info, audio_tracks = parse_essential_metadata(metadata)
                    if video_info or audio_tracks:
                        success = await update_caption_clean(message, video_info, audio_tracks)
                        if success:
                            await cleanup_files([combined_path] + temp_files)
                            return True, f"chunk{chunk_num}"
                
                # Clean up combined file
                if os.path.exists(combined_path):
                    os.remove(combined_path)
        
        # Final attempt: Full download for smaller files
        if file_size <= FULL_DOWNLOAD_LIMIT:
            LOGGER.info(f"📥 Final attempt: Full download ({file_size/1024/1024:.1f}MB)")
            
            full_path = os.path.join(temp_dir, f"full_{message.id}_{filename.replace('/', '_')}")
            try:
                await asyncio.wait_for(message.download(full_path), timeout=300.0)
                
                metadata = await extract_mediainfo_from_file(full_path)
                if metadata:
                    video_info, audio_tracks = parse_essential_metadata(metadata)
                    if video_info or audio_tracks:
                        success = await update_caption_clean(message, video_info, audio_tracks)
                        temp_files.append(full_path)
                        if success:
                            await cleanup_files(temp_files)
                            return True, "full"
                
                temp_files.append(full_path)
                
            except asyncio.TimeoutError:
                LOGGER.warning("⚠️ Full download timed out")
        
        await cleanup_files(temp_files)
        return False, "failed"
        
    except Exception as e:
        LOGGER.error(f"💥 Enhanced processing error: {e}")
        await cleanup_files(temp_files)
        return False, "error"

async def download_chunk(client, message, chunk_num, temp_dir):
    """Download a single chunk"""
    try:
        chunk_path = os.path.join(temp_dir, f"chunk_{message.id}_{chunk_num}.tmp")
        
        # Calculate chunk limit
        chunk_size = CHUNK_SIZE_MB * 1024 * 1024  # Convert to bytes
        max_chunks = int(chunk_size / (100 * 1024))  # 100KB per pyrogram chunk
        
        LOGGER.debug(f"📥 Downloading chunk {chunk_num}: max {max_chunks} pyrogram chunks")
        
        chunk_count = 0
        async for chunk in client.stream_media(message, limit=max_chunks):
            async with aiopen(chunk_path, "ab") as f:
                await f.write(chunk)
            chunk_count += 1
            if chunk_count >= max_chunks:
                break
        
        if chunk_count > 0 and os.path.exists(chunk_path):
            file_size = os.path.getsize(chunk_path)
            LOGGER.info(f"✅ Chunk {chunk_num} downloaded: {file_size/1024/1024:.1f}MB ({chunk_count} chunks)")
            return chunk_path
        
        return None
        
    except Exception as e:
        LOGGER.error(f"💥 Chunk {chunk_num} download error: {e}")
        return None

async def combine_chunks(chunk_paths, temp_dir, message_id):
    """Combine multiple chunks into single file"""
    try:
        if not chunk_paths:
            return None
        
        combined_path = os.path.join(temp_dir, f"combined_{message_id}.tmp")
        
        async with aiopen(combined_path, "wb") as combined_file:
            for chunk_path in chunk_paths:
                if os.path.exists(chunk_path):
                    async with aiopen(chunk_path, "rb") as chunk_file:
                        content = await chunk_file.read()
                        await combined_file.write(content)
        
        if os.path.exists(combined_path):
            total_size = os.path.getsize(combined_path)
            LOGGER.debug(f"📦 Combined file: {total_size/1024/1024:.1f}MB from {len(chunk_paths)} chunks")
            return combined_path
        
        return None
        
    except Exception as e:
        LOGGER.error(f"💥 Chunk combining error: {e}")
        return None

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
