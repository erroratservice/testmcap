"""
High-performance, concurrent MediaInfo processing module with enhanced error logging.
"""

import asyncio
import logging
import os
import json
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove
from pyrogram.errors import MessageNotModified
from bot.core.client import TgClient
from bot.core.config import Config
from bot.helpers.message_utils import send_message, send_reply
from bot.database.mongodb import MongoDB
from bot.modules.status import trigger_status_creation
from bot.core.tasks import ACTIVE_TASKS

LOGGER = logging.getLogger(__name__)

# Configuration
CHUNK_STEPS = [5, 10, 15]
FULL_DOWNLOAD_LIMIT = 200 * 1024 * 1024
MEDIAINFO_TIMEOUT = 30
FFPROBE_TIMEOUT = 60

async def updatemediainfo_handler(client, message):
    """Handler that initiates a concurrent scan."""
    try:
        if MongoDB.db is None:
            await send_message(message, "❌ **Error:** Database is not connected.")
            return

        is_force_run = len(message.command) > 2 and message.command[2] == '-f'
        
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, "❌ **Usage:** `/updatemediainfo -100123... [-f]`")
            return

        channel_id = channels[0]
        
        await trigger_status_creation(message)

        if is_force_run:
            LOGGER.info(f"🚀 Starting CONCURRENT FORCE processing for channel {channel_id}")
            scan_id = f"force_scan_{channel_id}_{message.id}"
            task = asyncio.create_task(force_process_channel_concurrently(channel_id, message, scan_id))
            ACTIVE_TASKS[scan_id] = task
        else:
            LOGGER.info(f"🚀 Starting CONCURRENT standard scan for channel {channel_id}")
            scan_id = f"scan_{channel_id}_{message.id}"
            task = asyncio.create_task(process_channel_concurrently(channel_id, message, scan_id))
            ACTIVE_TASKS[scan_id] = task
            
    except Exception as e:
        LOGGER.error(f"💥 Handler error in updatemediainfo: {e}")
        await send_message(message, f"❌ **Error:** {e}")


async def progress_updater(scan_id, stats, stop_event):
    """A sub-task that updates the database every 10 seconds."""
    while not stop_event.is_set():
        finished_count = stats["processed"] + stats["errors"] + stats["skipped"]
        await MongoDB.update_scan_progress(scan_id, finished_count)
        await asyncio.sleep(10)

async def process_channel_concurrently(channel_id, message, scan_id):
    """Processes a channel by running multiple file tasks at the same time."""
    user_id = message.from_user.id
    chat = None
    
    try:
        chat = await TgClient.user.get_chat(channel_id)
        
        history_generator = TgClient.user.get_chat_history(chat_id=channel_id)
        messages = [msg async for msg in history_generator]
        total_messages = len(messages)
        
        await MongoDB.start_scan(scan_id, channel_id, user_id, total_messages, chat.title, "MediaInfo Scan")

        stats = {"processed": 0, "errors": 0, "skipped": 0}
        failed_ids_internal = []
        
        semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_TASKS)
        stop_event = asyncio.Event()

        updater_task = asyncio.create_task(progress_updater(scan_id, stats, stop_event))

        async def worker(msg):
            async with semaphore:
                if not await has_media(msg) or await already_has_mediainfo(msg):
                    stats["skipped"] += 1
                    return

                LOGGER.info(f"🎯 Processing media message {msg.id} in {chat.title}")
                try:
                    success, _ = await process_message_enhanced(TgClient.user, msg)
                    if success:
                        stats["processed"] += 1
                    else:
                        stats["errors"] += 1
                        failed_ids_internal.append(msg.id)
                except Exception as e:
                    LOGGER.error(f"❌ Worker error on message {msg.id}: {e}")
                    stats["errors"] += 1
                    failed_ids_internal.append(msg.id)
                    # Raise the exception so asyncio.gather can catch it
                    raise

        tasks = [worker(msg) for msg in reversed(messages)]
        # --- MODIFIED: Capture and log results from asyncio.gather ---
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                LOGGER.error(f"A task failed with an exception: {result}", exc_info=True)

        stop_event.set()
        await updater_task
        await MongoDB.update_scan_progress(scan_id, total_messages)

        if failed_ids_internal:
            await MongoDB.save_failed_ids(channel_id, failed_ids_internal)
        
        summary_text = (f"✅ **Scan Complete: {chat.title}**\n\n"
                        f"- **Updated:** {stats['processed']} files\n"
                        f"- **Errors:** {stats['errors']} files\n"
                        f"- **Skipped:** {stats['skipped']} messages")
        await send_reply(message, summary_text)
        LOGGER.info(f"✅ Scan complete for {chat.title}. Summary sent.")

    except asyncio.CancelledError:
        LOGGER.warning(f"Scan task {scan_id} was cancelled by user.")
        await send_reply(message, f"❌ Scan for **{chat.title if chat else 'Unknown'}** was cancelled.")
    except Exception as e:
        LOGGER.error(f"💥 Critical error in concurrent processing for {channel_id}: {e}")
        await send_reply(message, f"❌ A critical error occurred during the scan for **{chat.title if chat else 'Unknown'}**.")
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
            await send_reply(message, f"✅ No failed IDs found in the database for this channel.")
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
                LOGGER.info(f"🎯 Force-processing media message {msg.id} in channel {channel_id}")
                success, _ = await process_message_full_download_only(TgClient.user, msg)
                if success:
                    stats["processed"] += 1
                else:
                    stats["errors"] += 1
        
        tasks = [worker(msg) for msg in messages_to_process]
        # --- MODIFIED: Capture and log results from asyncio.gather ---
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                LOGGER.error(f"A force-scan task failed with an exception: {result}", exc_info=True)

        stop_event.set()
        await updater_task
        await MongoDB.update_scan_progress(scan_id, len(failed_ids))
        
        await MongoDB.clear_failed_ids(channel_id)
        summary_text = (f"✅ **Force Scan Complete: {chat.title}**\n\n"
                        f"- **Updated:** {stats['processed']} files\n"
                        f"- **Errors:** {stats['errors']} files")
        await send_reply(message, summary_text)
        LOGGER.info(f"✅ Force-processing complete for channel {channel_id}.")
    except asyncio.CancelledError:
        LOGGER.warning(f"Force scan task {scan_id} was cancelled by user.")
        await send_reply(message, f"❌ Force scan for **{chat.title if chat else 'Unknown'}** was cancelled.")
    except Exception as e:
        LOGGER.error(f"💥 Critical error in force processing for {channel_id}: {e}")
        await send_reply(message, f"❌ A critical error occurred during the force scan for channel **{chat.title if chat else 'Unknown'}**.")
    finally:
        await MongoDB.end_scan(scan_id)
        ACTIVE_TASKS.pop(scan_id, None)

# ... (The rest of the file remains the same)
