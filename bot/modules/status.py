"""
Status command for tracking processing progress from the database
"""

import logging
from bot.helpers.message_utils import send_message
from bot.database.mongodb import MongoDB
from bot.helpers.keyboard_utils import build_status_keyboard

LOGGER = logging.getLogger(__name__)

async def status_handler(client, message):
    """Handler for /status command that reads from the database."""
    try:
        if MongoDB.db is None:
            await send_message(message, "📊 **Status:** Bot is idle\n\nDatabase is not connected, so no tasks can be tracked.")
            return

        # Fetch all active scans from the database
        active_scans = await MongoDB.get_interrupted_scans() # This function gets all active scans
        
        if not active_scans:
            await send_message(message,
                "📊 **Status:** Bot is idle\n\n"
                "No active operations are running.\n\n"
                "**Available Commands:**\n"
                "• `/updatemediainfo` - Extract MediaInfo\n"
                "• `/indexfiles` - Organize content\n\n"
                "Use `/help` for detailed instructions.")
            return
        
        # Display each active scan found in the database
        status_reply = "📊 **Active Media Processing Scans**\n\n"
        for scan in active_scans:
            status_reply += build_status_message(scan)
        
        await send_message(message, status_reply)
            
    except Exception as e:
        LOGGER.error(f"Status handler error: {e}")
        await send_message(message, f"❌ Error retrieving status: {e}")

def build_status_message(scan_data):
    """Build detailed status message from a database scan document."""
    channel_name = scan_data.get('chat_title', 'Unknown Channel')
    current = scan_data.get('processed_messages', 0)
    total = scan_data.get('total_messages', 0)
    scan_id = scan_data.get('_id')
    
    # Calculate progress
    progress = (current / total * 100) if total > 0 else 0
    
    # Build progress bar
    bar_length = 20
    filled = int(bar_length * progress / 100)
    progress_bar = f"[{'█' * filled}{'░' * (bar_length - filled)}] {progress:.1f}%"
    
    # The keyboard is currently for display; cancellation is the next step.
    # keyboard = build_status_keyboard(scan_id)
    
    return (
        f"📺 **Channel:** {channel_name}\n"
        f"📈 **Progress:** {current:,} / {total:,} messages\n"
        f"{progress_bar}\n"
        f"🔄 **Status:** 🟢 Running\n\n"
    )
