"""
Clean bot startup sequence
"""

import asyncio
import os
from bot.core.config import Config
from bot.core.client import TgClient
from bot.core.handlers import register_handlers
from bot.database.mongodb import MongoDB

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
        except Exception:
            # Fails silently if owner chat is not reachable
            pass
        
        # Clear the decks for the new session
        await MongoDB.clear_all_scans()

async def main():
    """Main startup function"""
    try:
        Config.load()
        Config.validate()
        
        os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
        
        if Config.DATABASE_URL:
            try:
                await MongoDB.initialize()
            except Exception:
                # Bot can run without DB, but some features will be disabled
                pass
        
        await TgClient.initialize()
        
        # Check for interrupted scans after clients are ready
        await check_and_notify_interrupted_scans()
        
        register_handlers()
        
        await asyncio.Future()
        
    except KeyboardInterrupt:
        pass
    except Exception:
        raise
    finally:
        await TgClient.stop()
        if Config.DATABASE_URL:
            await MongoDB.close()
