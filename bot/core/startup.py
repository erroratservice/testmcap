"""
Clean bot startup sequence
"""

import asyncio
import logging
import os
from pyrogram.errors import MessageNotModified
from bot.core.config import Config
from bot.core.client import TgClient
from bot.core.handlers import register_handlers
from bot.database.mongodb import MongoDB
from bot.helpers.message_utils import edit_message

LOGGER = logging.getLogger(__name__)

async def update_status_periodically():
    """A background task that periodically updates the central status message."""
    while True:
        await asyncio.sleep(5) # Update every 5 seconds
        if MongoDB.db is None:
            continue

        status_message_doc = await MongoDB.get_status_message()
        if not status_message_doc:
            continue

        chat_id = status_message_doc.get('chat_id')
        message_id = status_message_doc.get('message_id')
        
        try:
            active_scans = await MongoDB.get_interrupted_scans()
            
            text = "📊 **Live Task Status**\n\n"
            if not active_scans:
                text += "✅ Bot is currently idle. No active tasks."
            else:
                # Add numbering to the tasks
                for i, scan in enumerate(active_scans, 1):
                    operation = scan.get('operation', 'Processing').title()
                    channel = scan.get('chat_title', 'Unknown')
                    current = scan.get('processed_messages', 0)
                    total = scan.get('total_messages', 0)
                    progress = (current / total * 100) if total > 0 else 0
                    bar = f"[{'█' * int(progress / 10)}{'░' * (10 - int(progress / 10))}] {progress:.1f}%"
                    
                    text += f"**{i}. {operation}:** `{channel}`\n"
                    text += f"   `{bar}`\n"
                    text += f"   `{current} / {total} items processed.`\n\n"

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
    """Check for interrupted scans and notify the owner."""
    if not Config.DATABASE_URL or MongoDB.db is None:
        return
    
    interrupted = await MongoDB.get_interrupted_scans()
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
    """Main startup function"""
    try:
        Config.load()
        Config.validate()
        LOGGER.info("✅ Configuration loaded and validated.")
        
        os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
        
        if Config.DATABASE_URL:
            try:
                await MongoDB.initialize()
            except Exception as e:
                LOGGER.warning(f"⚠️ Database connection failed: {e}. Some features will be disabled.")
        
        await TgClient.initialize()
        
        await check_and_notify_interrupted_scans()
        
        register_handlers()

        # Start the background task for status updates
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
