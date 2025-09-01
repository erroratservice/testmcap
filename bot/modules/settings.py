"""
Interactive settings command for updating the index channel.
"""

import logging
from bot.core.config import Config
from bot.helpers.message_utils import send_message, edit_message
from bot.helpers.keyboard_utils import build_settings_keyboard
from bot.core.tasks import USER_STATES # Import from the new location

LOGGER = logging.getLogger(__name__)

async def settings_handler(client, message):
    """Handler for the /settings command."""
    try:
        current_id = Config.INDEX_CHANNEL_ID if Config.INDEX_CHANNEL_ID != 0 else "Not Set"
        
        settings_text = (f"**Bot Settings**\n\n"
                         f"Here you can manage the bot's configuration.\n\n"
                         f"**Current Index Channel ID:** `{current_id}`")
        
        keyboard = build_settings_keyboard()
        await send_message(message, settings_text, keyboard)
        
    except Exception as e:
        LOGGER.error(f"Settings handler error: {e}")
        await send_message(message, f"❌ Error loading settings: {e}")

async def set_index_channel_callback(client, callback_query):
    """Handles the 'Set Index Channel' button press."""
    user_id = callback_query.from_user.id
    
    # Set the user's state to expect the next message to be the channel ID
    USER_STATES[user_id] = "awaiting_index_channel"
    
    await callback_query.answer("Please send the new Index Channel ID.", show_alert=True)
    await edit_message(callback_query.message, 
                       (f"Okay, I'm ready for the new Index Channel ID.\n\n"
                        f"Please send the ID now (e.g., `-1001234567890`)."))

async def receive_channel_id_handler(client, message):
    """Handles the message containing the new channel ID."""
    user_id = message.from_user.id
    new_id_text = message.text.strip()
    
    try:
        # Validate that the ID is a valid integer
        new_id = int(new_id_text)
        
        # A simple check to ensure it looks like a channel ID
        if not new_id_text.startswith("-100"):
            await send_message(message, "**Invalid ID:** Channel IDs should be negative and usually start with `-100`. Please try again.")
            return

        # Update the config in memory
        Config.set('INDEX_CHANNEL_ID', new_id)
        
        await send_message(message, f"**Success!** Index Channel ID has been updated to `{new_id}`.")
        
    except ValueError:
        await send_message(message, "**Error:** That doesn't look like a valid number. Please send only the channel ID.")
    except Exception as e:
        LOGGER.error(f"Error setting new channel ID: {e}")
        await send_message(message, "An unexpected error occurred. Please try again.")
    finally:
        # Clean up the user's state
        if user_id in USER_STATES:
            del USER_STATES[user_id]
