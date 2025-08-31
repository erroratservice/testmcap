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
from bot.helpers.message_utils import send_message
from bot.database.mongodb import MongoDB
from bot.modules.status import trigger_status_creation

LOGGER = logging.getLogger(__name__)

# Configuration
CHUNK_STEPS = [5, 10, 15]
FULL_DOWNLOAD_LIMIT = 200 * 1024 * 1024
MEDIAINFO_TIMEOUT = 30
FFPROBE_TIMEOUT = 60

async def updatemediainfo_handler(client, message):
    """Handler with database-driven force-processing."""
    try:
        if MongoDB.db is None:
            await send_message(message, "❌ **Error:** Database is not connected. This feature is disabled.")
            return

        is_force_run = len(message.command) > 2 and message.command[2] == '-f'
        
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, "❌ **Usage:**\n• `/updatemediainfo -1001234567890`\n• `/updatemediainfo -1001234567890 -f`")
            return

        channel_id = channels[0]
        
        # Directly create the status message instead of a confirmation
        await trigger_status_creation(message)

        if is_force_run:
            LOGGER.info(f"🚀 Starting FORCE processing for channel {channel_id}")
            asyncio.create_task(force_process_channel(channel_id, message))
        else:
            LOGGER.info(f"🚀 Starting standard scan for channel {channel_id}")
            asyncio.create_task(process_channel_enhanced(channel_id, message))
            
    except Exception as e:
        LOGGER.error(f"💥 Handler error in updatemediainfo: {e}")
        await send_message(message, f"❌ **Error:** {e}")

async def process_channel_enhanced(channel_id, message):
    """Process channel, track scan in DB, and save failed IDs."""
    scan_id = f"scan_{channel_id}_{message.id}"
    user_id = message.from_user.id
    
    try:
        chat = await TgClient.user.get_chat(channel_id)
        
        history_generator = TgClient.user.get_chat_history(chat_id=channel_id, limit=100)
        messages = [msg async for msg in history_generator]
        total_messages = len(messages)
        
        await MongoDB.start_scan(scan_id, channel_id, user_id, total_messages, chat.title, "MediaInfo Scan")

        stats = {
            "processed": 0, "errors": 0, "skipped": 0, 
            "chunk_success": {}, "full_success": 0, "total": 0, "media": 0,
            "failed_ids": []
        }
        
        for i, msg in enumerate(reversed(messages)):
            stats["total"] += 1
            
            if not await has_media(msg) or await already_has_mediainfo(msg):
                stats["skipped"] += 1
                await MongoDB.update_scan_progress(scan_id, stats["total"])
                continue
            
            stats["media"] += 1
            LOGGER.info(f"🎯 Processing media message {msg.id} in {chat.title}")

            try:
                success, method = await process_message_enhanced(TgClient.user, msg)
                if success:
                    stats["processed"] += 1
                    if "chunk" in method:
                        step = int(method.replace('chunk', ''))
                        stats["chunk_success"][step] = stats["chunk_success"].get(step, 0) + 1
                    elif method == "full":
                        stats["full_success"] += 1
                else:
                    stats["errors"] += 1
                    stats["failed_ids"].append(msg.id)
            except Exception as e:
                LOGGER.error(f"❌ Error processing message {msg.id}: {e}")
                stats["errors"] += 1
                stats["failed_ids"].append(msg.id)

            await MongoDB.update_scan_progress(scan_id, stats["total"])

        if stats["failed_ids"]:
            await MongoDB.save_failed_ids(channel_id, stats["failed_ids"])
        
        await send_message(message, f"✅ Scan complete for **{chat.title}**.\nUpdated: {stats['processed']}, Errors: {stats['errors']}")
        LOGGER.info(f"✅ Scan complete for {chat.title}. Updated: {stats['processed']}, Errors: {stats['errors']}")

    except Exception as e:
        LOGGER.error(f"💥 Critical error in channel processing for {channel_id}: {e}")
        await send_message(message, f"❌ A critical error occurred during the scan for **{chat.title}**.")
    finally:
        await MongoDB.end_scan(scan_id)

async def force_process_channel(channel_id, message):
    """Process only the failed message IDs stored in the database."""
    scan_id = f"force_scan_{channel_id}_{message.id}"
    user_id = message.from_user.id
    
    try:
        failed_ids = await MongoDB.get_failed_ids(channel_id)
        if not failed_ids:
            await send_message(message, f"✅ No failed IDs found in the database for this channel.")
            return
        
        chat = await TgClient.user.get_chat(channel_id)
        await MongoDB.start_scan(scan_id, channel_id, user_id, len(failed_ids), chat.title, "Force Scan")
        
        stats = {"processed": 0, "errors": 0}
        
        messages_to_process = await TgClient.user.get_messages(chat_id=channel_id, message_ids=failed_ids)
        
        for i, msg in enumerate(messages_to_process):
            if not msg:
                await MongoDB.update_scan_progress(scan_id, i + 1)
                continue
            
            LOGGER.info(f"🎯 Force-processing media message {msg.id} in channel {channel_id}")
            success, _ = await process_message_full_download_only(TgClient.user, msg)
            if success:
                stats["processed"] += 1
            else:
                stats["errors"] += 1
            
            await MongoDB.update_scan_progress(scan_id, i + 1)

        await MongoDB.clear_failed_ids(channel_id)
        await send_message(message, f"✅ Force processing complete for **{chat.title}**!\nUpdated: {stats['processed']}, Errors: {stats['errors']}")
        LOGGER.info(f"✅ Force-processing complete for channel {channel_id}.")
    except Exception as e:
        LOGGER.error(f"💥 Critical error in force processing for {channel_id}: {e}")
        await send_message(message, f"❌ A critical error occurred during the force scan for channel **{channel_id}**.")
    finally:
        await MongoDB.end_scan(scan_id)

async def process_message_full_download_only(client, message):
    """A simplified processor that only attempts a full download with ffprobe fallback."""
    temp_file = None
    try:
        media = message.video or message.audio or message.document
        if not media: return False, "no_media"

        filename = str(media.file_name) if media.file_name else f"media_{message.id}"
        temp_dir = "temp_mediainfo"
        if not os.path.exists(temp_dir): os.makedirs(temp_dir)
        temp_file = os.path.join(temp_dir, f"temp_{message.id}.tmp")

        await asyncio.wait_for(message.download(temp_file), timeout=300.0)
        
        metadata = await extract_mediainfo_from_file(temp_file)
        video_info, audio_tracks = None, []
        if metadata:
            video_info, audio_tracks = parse_essential_metadata(metadata)
        
        if not video_info and not audio_tracks:
            LOGGER.warning(f"MediaInfo failed for {filename}. Trying ffprobe as a fallback.")
            ffprobe_metadata = await extract_metadata_with_ffprobe(temp_file)
            if ffprobe_metadata:
                video_info, audio_tracks = parse_ffprobe_metadata(ffprobe_metadata)
        
        if video_info or audio_tracks:
            if await update_caption_clean(message, video_info, audio_tracks):
                await cleanup_files([temp_file])
                return True, "full"
        
        return False, "failed"
    except Exception as e:
        LOGGER.error(f"Full download processing error for message {message.id}: {e}")
        return False, "error"
    finally:
        await cleanup_files([temp_file])

async def process_message_enhanced(client, message):
    """Process message with iterative chunk strategy and ffprobe fallback."""
    temp_file = None
    try:
        media = message.video or message.audio or message.document
        if not media: return False, "none"

        filename = str(media.file_name) if media.file_name else f"media_{message.id}"
        file_size = media.file_size
        
        temp_dir = "temp_mediainfo"
        if not os.path.exists(temp_dir): os.makedirs(temp_dir)
        temp_file = os.path.join(temp_dir, f"temp_{message.id}.tmp")

        for step in CHUNK_STEPS:
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
                            if await update_caption_clean(message, video_info, audio_tracks):
                                await cleanup_files([temp_file])
                                return True, f"chunk{step}"
            except Exception as e:
                LOGGER.warning(f"Chunk-based processing failed for message {message.id} at step {step}: {e}")
                pass

        if file_size <= FULL_DOWNLOAD_LIMIT:
            try:
                await asyncio.wait_for(message.download(temp_file), timeout=300.0)
                
                metadata = await extract_mediainfo_from_file(temp_file)
                video_info, audio_tracks = None, []
                if metadata:
                    video_info, audio_tracks = parse_essential_metadata(metadata)

                if not video_info and not audio_tracks:
                    LOGGER.warning(f"MediaInfo failed for {filename}. Trying ffprobe as a fallback.")
                    ffprobe_metadata = await extract_metadata_with_ffprobe(temp_file)
                    if ffprobe_metadata:
                        video_info, audio_tracks = parse_ffprobe_metadata(ffprobe_metadata)
                
                if video_info or audio_tracks:
                    if await update_caption_clean(message, video_info, audio_tracks):
                        await cleanup_files([temp_file])
                        return True, "full"

            except asyncio.TimeoutError:
                LOGGER.warning(f"Full download timed out for message {message.id}")
                pass
        
        return False, "failed"
    except Exception as e:
        LOGGER.error(f"Enhanced processing error for message {message.id}: {e}")
        return False, "error"
    finally:
        await cleanup_files([temp_file])

async def extract_mediainfo_from_file(file_path):
    try:
        proc = await asyncio.create_subprocess_shell(
            f'mediainfo "{file_path}" --Output=JSON',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=MEDIAINFO_TIMEOUT)
        return json.loads(stdout.decode()) if stdout else None
    except Exception as e:
        LOGGER.error(f"MediaInfo extraction error on file {file_path}: {e}")
        return None

async def extract_metadata_with_ffprobe(file_path):
    """Extract media metadata using ffprobe."""
    try:
        command = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            f'"{file_path}"'
        ]
        proc = await asyncio.create_subprocess_shell(
            ' '.join(command),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=FFPROBE_TIMEOUT)
        return json.loads(stdout.decode()) if stdout else None
    except Exception as e:
        LOGGER.error(f"FFprobe extraction error on file {file_path}: {e}")
        return None

def parse_ffprobe_metadata(metadata):
    """Parse ffprobe JSON output into the bot's standard format."""
    try:
        video_info, audio_tracks = None, []
        streams = metadata.get("streams", [])
        
        for stream in streams:
            codec_type = stream.get("codec_type")
            if codec_type == "video" and not video_info:
                video_info = {
                    "codec": stream.get("codec_name", "Unknown").upper(),
                    "height": stream.get("height")
                }
            elif codec_type == "audio":
                lang_tag = stream.get("tags", {}).get("language", "und")
                language = lang_tag.upper() if lang_tag != "und" else None
                audio_tracks.append({"language": language})
        
        return video_info, audio_tracks
    except Exception as e:
        LOGGER.error(f"FFprobe metadata parsing error: {e}")
        return None, []

def parse_essential_metadata(metadata):
    try:
        tracks = metadata.get("media", {}).get("track", [])
        video_info, audio_tracks = None, []
        
        for track in tracks:
            track_type = track.get("@type", "").lower()
            if track_type == "video" and not video_info:
                codec = track.get("Format", "Unknown").split('/')[0].strip().upper()
                height_str = track.get("Height", "")
                height = int(''.join(filter(str.isdigit, str(height_str)))) if height_str else None
                video_info = {"codec": codec, "height": height}
            elif track_type == "audio":
                language = track.get("Language", "").upper()
                if language and language not in ["UND", "UNDEFINED", "UNKNOWN", "N/A", ""]:
                    lang_map = {"EN": "ENG", "HI": "HIN", "ES": "SPA", "FR": "FRA", "DE": "GER"}
                    audio_tracks.append({"language": lang_map.get(language, language)})
                else:
                    audio_tracks.append({"language": None})
        return video_info, audio_tracks
    except Exception as e:
        LOGGER.error(f"Metadata parsing error: {e}")
        return None, []

async def update_caption_clean(message, video_info, audio_tracks):
    try:
        current_caption = message.caption or ""
        mediainfo_lines = []
        
        if video_info and video_info.get("codec"):
            codec, height = video_info["codec"], video_info.get("height")
            quality = ""
            if height:
                if height >= 2160: quality = "4K"
                elif height >= 1080: quality = "1080p"
                elif height >= 720: quality = "720p"
                else: quality = f"{height}p"
            video_line = f"Video: {codec.upper()} {quality}".strip()
            mediainfo_lines.append(video_line)
        
        if audio_tracks:
            languages = sorted(list(set(t['language'] for t in audio_tracks if t['language'])))
            audio_line = f"Audio: {len(audio_tracks)}"
            if languages: audio_line += f" ({', '.join(languages)})"
            mediainfo_lines.append(audio_line)
        
        if not mediainfo_lines: return False
        
        mediainfo_section = "\n\n" + "\n".join(mediainfo_lines)
        enhanced_caption = current_caption.strip() + mediainfo_section
        
        if len(enhanced_caption) > 1024:
            enhanced_caption = enhanced_caption[:1020] + "..."
        
        if current_caption == enhanced_caption: return False
        
        await TgClient.user.edit_message_caption(
            chat_id=message.chat.id, message_id=message.id, caption=enhanced_caption
        )
        return True
    except MessageNotModified:
        return False
    except Exception as e:
        LOGGER.error(f"Caption update error for message {message.id}: {e}")
        return False

async def cleanup_files(file_paths):
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                await aioremove(file_path)
        except Exception as e:
            LOGGER.warning(f"File cleanup warning for {file_path}: {e}")
            pass

async def has_media(msg):
    return bool(msg.video or msg.audio or msg.document)

async def already_has_mediainfo(msg):
    caption = msg.caption or ""
    return "Video:" in caption and "Audio:" in caption

async def get_target_channels(message):
    try:
        if len(message.command) > 1:
            channel_id = message.command[1]
            if channel_id.startswith('-100'): return [int(channel_id)]
            elif channel_id.isdigit(): return [int(f"-100{channel_id}")]
            else: return [channel_id]
        return []
    except:
        return []
