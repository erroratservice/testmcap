"""
MediaInfo update with reliable strategy - no hanging issues
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

async def updatemediainfo_handler(client, message):
    """Final handler - reliable and fast"""
    try:
        LOGGER.info("🚀 Starting updatemediainfo with reliable strategy")
        
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, 
                "❌ **Usage:**\n• `/updatemediainfo -1001234567890`")
            return
        
        for channel_id in channels:
            await process_channel_reliable(channel_id, message)
            
    except Exception as e:
        LOGGER.error(f"💥 Handler error: {e}", exc_info=True)
        await send_message(message, f"❌ **Error:** {e}")

async def process_channel_reliable(channel_id, message):
    """Process channel with reliable approach - no hanging"""
    try:
        chat = await TgClient.user.get_chat(channel_id)
        LOGGER.info(f"✅ Processing channel: {chat.title}")
        
        progress_msg = await send_message(message,
            f"🔄 **Processing:** {chat.title}\n"
            f"📊 **Method:** Reliable Strategy (No Hanging)\n"
            f"🎯 **Steps:** 30MB Head → Full Download Fallback\n"
            f"🔍 **Status:** Starting...")
        
        stats = {"processed": 0, "errors": 0, "skipped": 0, 
                "head_success": 0, "full_success": 0, "total": 0, "media": 0}
        
        message_count = 0
        async for msg in TgClient.user.get_chat_history(chat_id=channel_id, limit=100):
            message_count += 1
            stats["total"] += 1
            
            # Skip non-media
            if not await has_media(msg):
                stats["skipped"] += 1
                continue
            
            # Skip already processed
            if await already_has_mediainfo(msg):
                stats["skipped"] += 1
                continue
            
            stats["media"] += 1
            LOGGER.info(f"🎯 Processing media message {msg.id}")
            
            try:
                success, method = await process_message_reliable(TgClient.user, msg)
                if success:
                    stats["processed"] += 1
                    if method == "head":
                        stats["head_success"] += 1
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
                    f"🎯 **Head:** {stats['head_success']} | 📥 **Full:** {stats['full_success']}")
                await asyncio.sleep(0.5)
        
        # Final results
        final_stats = (
            f"✅ **Completed:** {chat.title}\n"
            f"📊 **Total:** {stats['total']} | **Media:** {stats['media']}\n"
            f"✅ **Updated:** {stats['processed']} files\n"
            f"❌ **Errors:** {stats['errors']} | ⏭️ **Skipped:** {stats['skipped']}\n\n"
            f"🎯 **Head Success:** {stats['head_success']}\n"
            f"📥 **Full Success:** {stats['full_success']}"
        )
        
        await edit_message(progress_msg, final_stats)
        LOGGER.info(f"🎉 Completed: {stats['processed']} updated, {stats['errors']} errors")
        
    except Exception as e:
        LOGGER.error(f"💥 Channel processing error: {e}")

async def process_message_reliable(client, message):
    """Reliable processing - no hanging guaranteed"""
    try:
        media = message.video or message.audio or message.document
        if not media:
            return False, "none"
        
        filename = str(media.file_name) if media.file_name else f"media_{message.id}"
        size = media.file_size
        
        LOGGER.info(f"📁 Processing: {filename} ({size/1024/1024:.1f}MB)")
        
        # Strategy 1: Large head chunk (30MB) - catches most files
        LOGGER.debug("🎯 Trying 30MB head chunk")
        success = await download_and_process_chunk(client, message, filename, 30)
        if success:
            return True, "head"
        
        # Strategy 2: Full download fallback (files ≤ 1GB only)
        if size <= 1024 * 1024 * 1024:  # 1GB limit
            LOGGER.debug("📥 Trying full download fallback")
            success = await download_and_process_full(client, message, filename)
            if success:
                return True, "full"
        else:
            LOGGER.warning(f"⚠️ File too large for full download: {size/1024/1024:.1f}MB")
        
        return False, "failed"
        
    except Exception as e:
        LOGGER.error(f"💥 Reliable processing error: {e}")
        return False, "error"

async def download_and_process_chunk(client, message, filename, size_mb):
    """Download head chunk with robust timeout handling"""
    download_path = None
    try:
        # Create temp file
        rand_str = f"chunk_{size_mb}_{message.id}"
        download_path = f"/tmp/{rand_str}_{filename.replace('/', '_').replace(' ', '_')}"
        
        # Download with asyncio.wait_for timeout
        chunk_size = 100 * 1024  # 100KB
        max_chunks = int((size_mb * 1024 * 1024) / chunk_size)
        
        LOGGER.debug(f"📥 Downloading {size_mb}MB ({max_chunks} chunks)")
        
        async def do_download():
            chunk_count = 0
            async for chunk in client.stream_media(message, limit=max_chunks):
                with open(download_path, "ab") as f:
                    f.write(chunk)
                chunk_count += 1
                if chunk_count >= max_chunks:
                    break
            return chunk_count
        
        # Use asyncio.wait_for for timeout
        try:
            chunk_count = await asyncio.wait_for(do_download(), timeout=180.0)  # 3 minute timeout
            if chunk_count == 0:
                return False
        except asyncio.TimeoutError:
            LOGGER.warning(f"⚠️ {size_mb}MB download timed out")
            return False
        
        # Verify file exists and has content
        if not os.path.exists(download_path):
            return False
        
        file_size = os.path.getsize(download_path)
        if file_size == 0:
            return False
        
        LOGGER.debug(f"✅ Downloaded: {file_size/1024/1024:.1f}MB")
        
        # Process with MediaInfo
        return await process_with_mediainfo(download_path, message)
        
    except Exception as e:
        LOGGER.error(f"💥 Chunk download error: {e}")
        return False
    finally:
        if download_path and os.path.exists(download_path):
            try:
                os.remove(download_path)
            except:
                pass

async def download_and_process_full(client, message, filename):
    """Full download with timeout - for smaller files only"""
    download_path = None
    try:
        rand_str = f"full_{message.id}"
        download_path = f"/tmp/{rand_str}_{filename.replace('/', '_').replace(' ', '_')}"
        
        LOGGER.debug("📥 Starting full download")
        
        # Full download with timeout
        try:
            await asyncio.wait_for(message.download(download_path), timeout=600.0)  # 10 minute timeout
        except asyncio.TimeoutError:
            LOGGER.warning("⚠️ Full download timed out")
            return False
        
        if not os.path.exists(download_path):
            return False
        
        file_size = os.path.getsize(download_path)
        LOGGER.debug(f"✅ Full download: {file_size/1024/1024:.1f}MB")
        
        # Process with MediaInfo
        return await process_with_mediainfo(download_path, message)
        
    except Exception as e:
        LOGGER.error(f"💥 Full download error: {e}")
        return False
    finally:
        if download_path and os.path.exists(download_path):
            try:
                os.remove(download_path)
            except:
                pass

async def process_with_mediainfo(file_path, message):
    """Process file with MediaInfo CLI"""
    try:
        # Run MediaInfo with timeout
        cmd = f"mediainfo '{file_path}' --Output=JSON"
        
        async def run_mediainfo():
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            return stdout.decode() if stdout else ""
        
        try:
            output = await asyncio.wait_for(run_mediainfo(), timeout=30.0)
        except asyncio.TimeoutError:
            LOGGER.warning("⚠️ MediaInfo timed out")
            return False
        
        if not output:
            return False
        
        # Parse and extract metadata
        try:
            data = json.loads(output)
            tracks = data.get("media", {}).get("track", [])
            
            video_info = None
            audio_tracks = []
            
            for track in tracks:
                track_type = track.get("@type", "").lower()
                if track_type == "video":
                    video_info = {
                        "codec": track.get("Format", "Unknown"),
                        "height": track.get("Height")
                    }
                elif track_type == "audio":
                    audio_tracks.append({
                        "codec": track.get("Format", "Unknown"),
                        "language": track.get("Language", "Unknown")
                    })
            
            # Check if we have actual streams
            if not video_info and not audio_tracks:
                LOGGER.warning("⚠️ No video/audio streams found")
                return False
            
            LOGGER.info(f"✅ Streams found: Video={bool(video_info)}, Audio={len(audio_tracks)}")
            
            # Generate and update caption
            return await update_caption(message, video_info, audio_tracks)
            
        except json.JSONDecodeError:
            LOGGER.warning("⚠️ MediaInfo JSON parse failed")
            return False
        
    except Exception as e:
        LOGGER.error(f"💥 MediaInfo processing error: {e}")
        return False

async def update_caption(message, video_info, audio_tracks):
    """Update message caption with MediaInfo"""
    try:
        current_caption = message.caption or ""
        lines = []
        
        # Video line
        if video_info:
            codec = video_info.get("codec", "Unknown")
            height = video_info.get("height")
            
            resolution = ""
            if height:
                try:
                    h = int(height)
                    if h >= 2160:
                        resolution = "4K"
                    elif h >= 1440:
                        resolution = "1440p"
                    elif h >= 1080:
                        resolution = "1080p"
                    elif h >= 720:
                        resolution = "720p"
                    else:
                        resolution = f"{h}p"
                except:
                    pass
            
            video_line = f"Video: {codec}"
            if resolution:
                video_line += f" {resolution}"
            lines.append(video_line)
        
        # Audio line
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
            lines.append(audio_line)
        
        if not lines:
            return False
        
        # Create enhanced caption
        enhanced = current_caption.strip()
        mediainfo_section = "\n\n" + "\n".join(lines)
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
            return False
        
        try:
            await TgClient.user.edit_message_caption(
                chat_id=message.chat.id,
                message_id=message.id,
                caption=enhanced_caption
            )
            return True
        except MessageNotModified:
            return False
        
    except Exception as e:
        LOGGER.error(f"💥 Caption update error: {e}")
        return False

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
