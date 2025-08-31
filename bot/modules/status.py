"""
Status command for creating the central status message
"""

import logging
from bot.core.client import TgClient
from bot.helpers.message_utils import send_message
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

async def status_handler(client, message):
    """
    Handler for /status command.
    Creates a new central status message and deletes the old one.
    """
    try:
        if MongoDB.db is None:
            await send_message(message, "❌ Database is not connected. Status tracking is disabled.")
            return

        # Get the old status message details to delete it later
        old_status_message = await MongoDB.get_status_message()

        # Send the new message
        initial_text = "📊 **Live Task Status**\n\nInitializing..."
        new_status_message = await send_message(message, initial_text)
        
        if new_status_message:
            # Save the new message's location as the one to be updated
            await MongoDB.set_status_message(new_status_message.chat.id, new_status_message.id)

            # If an old message existed, try to delete it
            if old_status_message:
                try:
                    await TgClient.bot.delete_messages(
                        chat_id=old_status_message.get('chat_id'),
                        message_ids=old_status_message.get('message_id')
                    )
                except Exception:
                    # Fails silently if the message is already deleted or not accessible
                    pass
        else:
            await send_message(message, "❌ Could not create the status message.")
            
    except Exception as e:
        LOGGER.error(f"Status handler error: {e}")
        await send_message(message, f"❌ Error creating status message: {e}")
