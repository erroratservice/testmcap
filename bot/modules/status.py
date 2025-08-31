"""
Status command for creating the central status message
"""

import logging
from bot.helpers.message_utils import send_message
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

async def status_handler(client, message):
    """Handler for /status command that creates the central status message."""
    try:
        if MongoDB.db is None:
            await send_message(message, "❌ Database is not connected. Status tracking is disabled.")
            return

        initial_text = "📊 **Live Task Status**\n\nInitializing..."
        
        status_message = await send_message(message, initial_text)
        
        if status_message:
            await MongoDB.set_status_message(status_message.chat.id, status_message.id)
            await message.reply_text("✅ Central status message created. It will now update automatically.", quote=True)
        else:
            await send_message(message, "❌ Could not create the status message.")
            
    except Exception as e:
        LOGGER.error(f"Status handler error: {e}")
        await send_message(message, f"❌ Error creating status message: {e}")
