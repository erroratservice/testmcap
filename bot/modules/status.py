"""
Status command for creating the central status message
"""

import logging
from bot.core.client import TgClient
from bot.helpers.message_utils import send_message
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

async def trigger_status_creation(message):
    """
    Creates a new central status message and deletes the old one.
    This function can be called by any command.
    """
    if MongoDB.db is None:
        await send_message(message, "❌ Database is not connected. Status tracking is disabled.")
        return

    old_status_message = await MongoDB.get_status_message()

    initial_text = "📊 **Live Task Status**\n\nInitializing..."
    new_status_message = await send_message(message, initial_text)
    
    if new_status_message:
        await MongoDB.set_status_message(new_status_message.chat.id, new_status_message.id)

        if old_status_message:
            try:
                await TgClient.bot.delete_messages(
                    chat_id=old_status_message.get('chat_id'),
                    message_ids=old_status_message.get('message_id')
                )
            except Exception:
                pass
    else:
        await send_message(message, "❌ Could not create the status message.")

async def status_handler(client, message):
    """Handler for /status command that creates the central status message."""
    try:
        await trigger_status_creation(message)
    except Exception as e:
        LOGGER.error(f"Status handler error: {e}")
        await send_message(message, f"❌ Error creating status message: {e}")
