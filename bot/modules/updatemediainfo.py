"""
High-performance, concurrent MediaInfo processing module with enhanced error logging and FloodWait session debugging.
"""

import asyncio
import logging
import os
import json
import re
import time
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove
from asyncio.exceptions import TimeoutError
from pyrogram.errors import MessageNotModified, FloodWait
from bot.core.client import TgClient
from bot.core.config import Config
from bot.helpers.message_utils import send_message, send_reply
from bot.database.mongodb import MongoDB
from bot.modules.status import trigger_status_creation
from bot.core.tasks import ACTIVE_TASKS
from bot.helpers.channel_utils import stream_messages_by_id_batches

LOGGER = logging.getLogger(__name__)

# Global event to coordinate flood waits across all tasks
flood_wait_event = asyncio.Event()
flood_wait_event.set() # Set it to green (go) by default

# Configuration
CHUNK_STEPS = [5]
FULL_DOWNLOAD_LIMIT = 200 * 1024 * 1024
MEDIAINFO_TIMEOUT = 30
FFPROBE_TIMEOUT = 60
DOWNLOAD_TIMEOUT = 1800 # 30 minutes

# Regex to detect split files like .mkv.001, .001.mkv, and ...part001.mkv
SPLIT_FILE_REGEX = re.compile(r'(\.(mkv|mp4|avi|mov)\.00[1-9]|\.00[1-9]\.(mkv|mp4|avi|mov)|\.part00[1-9]\.(mkv|mp4|avi|mov))$', re.IGNORECASE)

async def updatemediainfo_handler(client, message):
    """Handler that initiates a concurrent scan."""
    flood_wait_event.set()
    try:
        if MongoDB.db is None:
            await send_message(message, "**Error:** Database is not connected.")
            return

        is_force_failed_run = '-f' in message.command
        is_force_rescan = '-rescan' in message.command

        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, "**Usage:** `/updatemediainfo -100123... [-f | -rescan]`")
            return

        channel_id = channels[0]

        await trigger_status_creation(message)

        if is_force_failed_run:
            LOGGER.info(f"Starting CONCURRENT FAILED ID processing for channel {channel_id}")
            scan_id = f"force_scan_{channel_id}_{message.id}"
            task = asyncio.create_task(force_process_channel_concurrently(channel_id, message, scan_id))
            ACTIVE_TASKS[scan_id] = task
        else:
            LOGGER.info(f"Starting CONCURRENT standard scan for channel {channel_id}. Rescan: {is_force_rescan}")
            scan_id = f"scan_{channel_id}_{message.id}"
            task = asyncio.create_task(process_channel_concurrently(channel_id, message, scan_id, force=is_force_rescan))
            ACTIVE_TASKS[scan_id] = task

    except Exception as e:
        LOGGER.error(f"Handler error in updatemediainfo: {e}")
        await send_message(message, f"**Error:** {e}")


async def progress_updater(scan_id, stats, stop_event):
    """A sub-task that updates the database every 10 seconds."""
    while not stop_event.is_set():
        finished_count = stats["processed"] + stats["errors"] + stats["skipped"]
        await MongoDB.update_scan_progress(scan_id, finished_count)
        await asyncio.sleep(10)

async def process_channel_concurrently(channel_id, message, scan_id, force=False):
    """Processes a channel by streaming messages via ID batches and running file tasks concurrently."""
    user_id = message.from_user.id
    chat = None

    try:
        chat = await TgClient.user.get_chat(channel_id)

        total_messages = await TgClient.user.get_chat_history_count(chat_id=channel_id)
        await MongoDB.start_scan(scan_id, channel_id, user_id, total_messages, chat.title, "MediaInfo Scan")

        stats = {"processed": 0, "errors": 0, "skipped": 0}
        failed_ids_internal = []

        semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_TASKS)

        async def worker(msg):
            async with semaphore:
                await asyncio.sleep(5)
                await flood_wait_event.wait()

                media = msg.video or msg.document
                if media and hasattr(media, 'file_name') and media.file_name and SPLIT_FILE_REGEX.search(media.file_name):
                    LOGGER.info(f"Skipping split file: {media.file_name}")
                    stats["skipped"] += 1
                    return

                if not await has_media(msg) or await already_has_mediainfo(msg):
                    stats["skipped"] += 1
                    return

                LOGGER.info(f"Processing media message {msg.id} in {chat.title}")
                try:
                    success, _ = await process_message_enhanced(msg)
                    if success:
                        stats["processed"] += 1
                    else:
                        stats["errors"] += 1
                        failed_ids_internal.append(msg.id)
                except Exception:
                    stats["errors"] += 1
                    failed_ids_internal.append(msg.id)
                    raise

        processed_count = 0
        async for message_batch in stream_messages_by_id_batches(channel_id, force=force):
            if not message_batch:
                continue

            tasks = [worker(msg) for msg in reversed(message_batch)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    LOGGER.error(f"A task failed with an exception in a batch: {result}", exc_info=True)

            processed_count += len(message_batch)
            await MongoDB.update_scan_progress(scan_id, processed_count)

        if failed_ids_internal:
            await MongoDB.save_failed_ids(channel_id, failed_ids_internal)

        summary_text = (f"**Scan Complete: {chat.title}**\n\n"
                        f"- Updated: {stats['processed']} files\n"
                        f"- Errors: {stats['errors']} files\n"
                        f"- Skipped: {stats['skipped']} messages")
        await send_reply(message, summary_text)
        LOGGER.info(f"Scan complete for {chat.title}. Summary sent.")

    except asyncio.CancelledError:
        LOGGER.warning(f"Scan task {scan_id} was cancelled by user.")
        await send_reply(message, f"Scan for **{chat.title if chat else 'Unknown'}** was cancelled.")
    except Exception as e:
        LOGGER.error(f"Critical error in concurrent processing for {channel_id}: {e}")
        await send_reply(message, f"A critical error occurred during the scan for **{chat.title if chat else 'Unknown'}**.")
    finally:
        await MongoDB.end_scan(scan_id)
        ACTIVE_TASKS.pop(scan_id, None)

async def force_process_channel_concurrently(channel_id, message, scan_id):
    """Concurrently processes only the failed message IDs stored in the database."""
    user_id = message.from_user.id
    chat = None

    try:
        failed_ids = await MongoDB.get_failed_ids(channel_id)
        if not failed_ids:
            await send_reply(message, f"No failed IDs found in the database for this channel.")
            return

        chat = await TgClient.user.get_chat(channel_id)
        await MongoDB.start_scan(scan_id, channel_id, user_id, len(failed_ids), chat.title, "Force Scan")

        stats = {"processed": 0, "errors": 0, "skipped": 0}

        messages_to_process = await TgClient.user.get_messages(chat_id=channel_id, message_ids=failed_ids)

        semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_TASKS)
        stop_event = asyncio.Event()
        updater_task = asyncio.create_task(progress_updater(scan_id, stats, stop_event))

        async def worker(msg):
            if not msg:
                stats["skipped"] += 1
                return
            async with semaphore:
                await asyncio.sleep(5)
                await flood_wait_event.wait()
                LOGGER.info(f"Force-processing media message {msg.id} in channel {channel_id}")
                success, _ = await process_message_full_download_only(msg)
                if success:
                    stats["processed"] += 1
                else:
                    stats["errors"] += 1

        tasks = [worker(msg) for msg in messages_to_process]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                LOGGER.error(f"A force-scan task failed with an exception: {result}", exc_info=True)

        stop_event.set()
        await updater_task
        await MongoDB.update_scan_progress(scan_id, len(failed_ids))

        await MongoDB.clear_failed_ids(channel_id)
        summary_text = (f"**Force Scan Complete: {chat.title}**\n\n"
                        f"- Updated: {stats['processed']} files\n"
                        f"- Errors: {stats['errors']} files")
        await send_reply(message, summary_text)
        LOGGER.info(f"Force-processing complete for channel {channel_id}.")
    except asyncio.CancelledError:
        LOGGER.warning(f"Force scan task {scan_id} was cancelled by user.")
        await send_reply(message, f"Force scan for **{chat.title if chat else 'Unknown'}** was cancelled.")
    except Exception as e:
        LOGGER.error(f"Critical error in force processing for {channel_id}: {e}")
        await send_reply(message, f"A critical error occurred during the force scan for channel **{chat.title if chat else 'Unknown'}**.")
    finally:
        await MongoDB.end_scan(scan_id)
        ACTIVE_TASKS.pop(scan_id, None)


async def process_message_full_download_only(message):
    """A simplified processor that only attempts a full download using the BOT session."""
    temp_file = None
    try:
        media = message.video or message.audio or message.document
        if not media: return False, "no_media"

        filename = str(media.file_name) if media.file_name else f"media_{message.id}"
        temp_dir = "temp_mediainfo"
        if not os.path.exists(temp_dir): os.makedirs(temp_dir)
        temp_file = os.path.join(temp_dir, f"temp_{message.id}.tmp")

        try:
            await flood_wait_event.wait()
            await asyncio.wait_for(TgClient.bot.download_media(message, file_name=temp_file), timeout=DOWNLOAD_TIMEOUT)
        except FloodWait as e:
            # --- DEBUG LOGGING ADDED ---
            LOGGER.warning(f"BOT session FloodWait of {e.value}s on message {message.id} during full download. Pausing ALL tasks...")
            flood_wait_event.clear()

            scan_id_list = [key for key, task in ACTIVE_TASKS.items() if task is asyncio.current_task()]
            scan_id = scan_id_list[0] if scan_id_list else None
            
            if scan_id:
                await MongoDB.set_scan_flood_wait(scan_id, time.time() + e.value)
            else:
                LOGGER.warning("Could not find active scan ID. Status will not show flood wait.")

            await asyncio.sleep(e.value + 5)

            if scan_id:
                await MongoDB.clear_scan_flood_wait(scan_id)
            
            LOGGER.info("Resuming ALL tasks after flood wait.")
            flood_wait_event.set()
            
            LOGGER.warning(f"Task for message {message.id} failed due to FloodWait. It will be marked as an error.")
            return False, "flood_wait_handled"
        
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
    except TimeoutError:
        LOGGER.error(f"Download timed out for message {message.id} due to network issues.")
        return False, "timeout"
    except Exception as e:
        LOGGER.error(f"Full download processing error for message {message.id}: {e}", exc_info=True)
        return False, "error"
    finally:
        await cleanup_files([temp_file])

async def process_message_enhanced(message):
    """Process message with chunking using BOT session and ffprobe fallback."""
    temp_file = None
    try:
        media = message.video or message.audio or message.document
        if not media: return False, "none"

        filename = str(media.file_name) if media.file_name else f"media_{message.id}"
        file_size = media.file_size
        
        temp_dir = "temp_mediainfo"
        if not os.path.exists(temp_dir): os.makedirs(temp_dir)
        temp_file = os.path.join(temp_dir, f"temp_{message.id}.tmp")

        try:
            await flood_wait_event.wait()
            async with aiopen(temp_file, "wb") as f:
                chunk_count = 0
                async for chunk in TgClient.bot.stream_media(message, limit=CHUNK_STEPS[0]):
                    await f.write(chunk)
                    chunk_count += 1
            
            if chunk_count > 0:
                metadata = await extract_mediainfo_from_file(temp_file)
                if metadata:
                    video_info, audio_tracks = parse_essential_metadata(metadata)
                    if video_info or audio_tracks:
                        if await update_caption_clean(message, video_info, audio_tracks):
                            await cleanup_files([temp_file])
                            return True, f"chunk{CHUNK_STEPS[0]}"
        except FloodWait as e:
            # --- DEBUG LOGGING ADDED ---
            LOGGER.warning(f"BOT session FloodWait of {e.value}s on message {message.id} during chunk stream. Pausing ALL tasks...")
            flood_wait_event.clear()

            scan_id_list = [key for key, task in ACTIVE_TASKS.items() if task is asyncio.current_task()]
            scan_id = scan_id_list[0] if scan_id_list else None
            
            if scan_id:
                await MongoDB.set_scan_flood_wait(scan_id, time.time() + e.value)
            else:
                LOGGER.warning("Could not find active scan ID. Status will not show flood wait.")

            await asyncio.sleep(e.value + 5)

            if scan_id:
                await MongoDB.clear_scan_flood_wait(scan_id)
            
            LOGGER.info("Resuming ALL tasks after flood wait.")
            flood_wait_event.set()
            
            LOGGER.warning(f"Task for message {message.id} failed due to FloodWait. It will be marked as an error.")
            return False, "flood_wait_handled"
        except TimeoutError:
            LOGGER.warning(f"Chunk download timed out for message {message.id}.")
        except Exception as e:
            LOGGER.warning(f"Chunk-based processing failed for message {message.id}: {e}")
            pass

        if file_size <= FULL_DOWNLOAD_LIMIT:
            try:
                await flood_wait_event.wait()
                await asyncio.wait_for(TgClient.bot.download_media(message, file_name=temp_file), timeout=DOWNLOAD_TIMEOUT)
                
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

            except TimeoutError:
                LOGGER.warning(f"Full download timed out for message {message.id}")
                return False, "timeout"
        
        return False, "failed"
    except Exception as e:
        LOGGER.error(f"Enhanced processing error for message {message.id}: {e}")
        return False, "error"
    finally:
        await cleanup_files([temp_file])

async def update_caption_clean(message, video_info, audio_tracks):
    """
    Intelligently updates captions using the USER session, with specific FloodWait logging.
    """
    try:
        current_caption = message.caption or ""
        
        main_caption = current_caption.split('\n\n')[0].strip()
        
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
        
        if not mediainfo_lines: 
            return False
        
        mediainfo_section = "\n\n" + "\n".join(mediainfo_lines)
        enhanced_caption = main_caption + mediainfo_section
        
        if len(enhanced_caption) > 1024:
            enhanced_caption = enhanced_caption[:1020] + "..."
        
        if current_caption == enhanced_caption: 
            return False
        
        await TgClient.user.edit_message_caption(
            chat_id=message.chat.id, message_id=message.id, caption=enhanced_caption
        )
        await asyncio.sleep(5)
        return True
    except MessageNotModified:
        return False
    except FloodWait as e:
        # --- DEBUG LOGGING ADDED ---
        LOGGER.warning(f"USER session FloodWait of {e.value}s on message {message.id} during caption edit. Pausing ALL tasks...")
        flood_wait_event.clear()
        await asyncio.sleep(e.value + 5)
        flood_wait_event.set()
        LOGGER.info("Resuming ALL tasks after flood wait.")
        # Return False as the edit failed this time
        return False
    except Exception as e:
        LOGGER.error(f"Caption update error for message {message.id}: {e}")
        return False

# --- The rest of the helper functions remain unchanged ---

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
    video_tags = re.findall(r'Video\s*[:\-]', caption, re.IGNORECASE)
    audio_tags = re.findall(r'Audio\s*[:\-]', caption, re.IGNORECASE)
    if len(video_tags) > 1 or len(audio_tags) > 1:
        return False
    if len(video_tags) == 1 and len(audio_tags) == 1:
        return True
    return False

async def get_target_channels(message):
    known_flags = ['-rescan', '-f']
    args = [arg for arg in message.command[1:] if arg not in known_flags]
    
    if args:
        channel_id = args[0]
        try:
            if channel_id.startswith('-100'):
                return [int(channel_id)]
            elif channel_id.isdigit():
                 return [int(f"-100{channel_id}")]
        except (ValueError, IndexError):
            pass

    return []
