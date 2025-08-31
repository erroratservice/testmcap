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
        
        await send_message(message, f"✅ Task for channel `{channel_id}` has been queued. See /status for live progress.")

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
                continue
            
            stats["media"] += 1
            LOGGER.info(f"🎯 Processing media message {msg.id} in {chat.title}")

            try:
                success, method = await process_message_enhanced(TgClient.user, msg)
                if success:
                    stats["processed"] += 1
                    if "chunk" in method: stats["chunk_success"][int(method.replace('chunk', ''))] += 1
                    elif method == "full": stats["full_success"] += 1
                else:
                    stats["errors"] += 1
                    stats["failed_ids"].append(msg.id)
            except Exception as e:
                LOGGER.error(f"❌ Error processing message {msg.id}: {e}")
                stats["errors"] += 1
                stats["failed_ids"].append(msg.id)

            if i % 5 == 0:
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
            if not msg: continue
            
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

# ... (The rest of the file, including ffprobe helpers, remains the same)
