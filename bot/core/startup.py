"""
Clean bot startup sequence
"""

import asyncio
import logging
import os
from pyrogram.errors import MessageNotModified, MessageDeleteForbidden
from bot.core.config import Config
from bot.core.client import TgClient
from bot.core.handlers import register_handlers
from bot.database.mongodb import MongoDB
from bot.helpers.message_utils import edit_message

LOGGER = logging.getLogger(__name__)

async def update_status_periodically():
    """A background task that periodically updates the central status message."""
    was_active = False
    while True:
        await asyncio.sleep(5)
        if MongoDB.db is None:
            continue

        status_message_doc = await MongoDB.get_status_message()
        if not status_message_doc:
            was_active = False
            continue

        chat_id = status_message_doc.get('chat_id')
        message_id = status_message_doc.get('message_id')
        
        try:
            active_scans = await MongoDB.get_active_scans()
            
            is_active_now = bool(active_scans)
            if was_active and not is_active_now:
                try:
                    await TgClient.bot.delete_messages(chat_id, message_id)
                    await MongoDB.delete_status_message_tracker()
                except (MessageDeleteForbidden, AttributeError):
                    pass 
                except Exception as e:
                    LOGGER.warning(f"Could not delete final status message: {e}")
                was_active = False
                continue
            was_active = is_active_now

            text = "📊 **Live Task Status**\n\n"
            if not active_scans:
                text += "✅ Bot is currently idle. No active tasks."
            else:
                for i, scan in enumerate(active_scans, 1):
                    operation = scan.get('operation', 'Processing').title()
                    channel = scan.get('chat_title', 'Unknown')
                    current = scan.get('processed_messages', 0)
                    total = scan.get('total_messages', 0)
                    progress = (current / total * 100) if total > 0 else 0
                    bar = f"[{'█' * int(progress / 10)}{'░' * (10 - int(progress / 10))}] {progress:.1f}%"
                    
                    text += f"**{i}. {operation}:** `{channel}`\n"
                    text += f"   `{bar}`\n"
                    text += f"   `Processed: {current} / {total}`\n\n"

            class DummyMessage:
                def __init__(self, cid, mid):
                    self.chat = type('Chat', (), {'id': cid})()
                    self.id = mid

            await edit_message(DummyMessage(chat_id, message_id), text)

        except MessageNotModified:
            pass
        except Exception as e:
            LOGGER.error(f"Could not update status message: {e}")

async def check_and_notify_interrupted_scans():
    if not Config.DATABASE_URL or MongoDB.db is None:
        return
    
    interrupted = await MongoDB.get_active_scans()
    if interrupted:
        notification_text = "⚠️ **Bot Restarted with Interrupted Scans** ⚠️\n\nThe following scans were interrupted and did not complete:\n"
        for scan in interrupted:
            progress = f"{scan.get('processed_messages', 0)} / {scan.get('total_messages', 'N/A')}"
            notification_text += (
                f"\n- **Channel:** {scan.get('chat_title', 'Unknown')}\n"
                f"  **Progress:** {progress} messages\n"
            )
        
        try:
            await TgClient.bot.send_message(Config.OWNER_ID, notification_text)
        except Exception as e:
            LOGGER.warning(f"Failed to send interruption notification: {e}")
        
        await MongoDB.clear_all_scans()

async def main():
    try:
        Config.load()
        Config.validate()
        LOGGER.info("✅ Configuration loaded.")
        
        os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
        
        if Config.DATABASE_URL:
            try:
                await MongoDB.initialize()
            except Exception as e:
                LOGGER.warning(f"⚠️ DB connection failed: {e}")
        
        await TgClient.initialize()
        
        await check_and_notify_interrupted_scans()
        
        register_handlers()

        asyncio.create_task(update_status_periodically())
        LOGGER.info("✅ Started background status updater.")
        
        LOGGER.info("🚀 Media Indexing Bot started successfully!")
        
        await asyncio.Future()
        
    except KeyboardInterrupt:
        LOGGER.info("👋 Bot stopped by user.")
    except Exception as e:
        LOGGER.error(f"💥 Startup failed: {e}")
        raise
    finally:
        await TgClient.stop()
        if Config.DATABASE_URL:
            await MongoDB.close()
