"""
Interactive settings command for updating various bot configurations.
"""

import logging
from bot.core.config import Config
from bot.helpers.message_utils import send_message, edit_message
from bot.helpers.keyboard_utils import build_settings_keyboard
from bot.core.tasks import USER_STATES

LOGGER = logging.getLogger(__name__)

# A dictionary to hold information about each setting
SETTINGS = {
    "index_channel": {"prompt": "Please send the new Index Channel ID (e.g., -1001234567890).", "type": int},
    "max_tasks": {"prompt": "Please send the new max concurrent tasks value (e.g., 3).", "type": int},
    "use_tvmaze": {"prompt": "Should TVMaze titles be used? Send `true` or `false`.", "type": bool},
    "auth_chats": {"prompt": "Please send the new list of Authorized Chat IDs, separated by commas (e.g., 123,456).", "type": str}
}

async def settings_handler(client, message):
    """Handler for the /settings command."""
    try:
        # Build the text with all current settings
        settings_text = (
            f"**Bot Settings**\n\n"
            f"Here you can manage the bot's configuration.\n\n"
            f"**Current Settings:**\n"
            f"- Index Channel ID: `{Config.INDEX_CHANNEL_ID or 'Not Set'}`\n"
            f"- Max Concurrent Tasks: `{Config.MAX_CONCURRENT_TASKS}`\n"
            f"- Use TVMaze Titles: `{Config.USE_TVMAZE_TITLES}`\n"
            f"- Authorized Chats: `{Config.AUTHORIZED_CHATS or 'Not Set'}`"
        )
        
        keyboard = build_settings_keyboard()
        await send_message(message, settings_text, keyboard)
        
    except Exception as e:
        LOGGER.error(f"Settings handler error: {e}")
        await send_message(message, f"❌ Error loading settings: {e}")

async def set_setting_callback(client, callback_query):
    """Handles all 'Set' button presses from the settings menu."""
    user_id = callback_query.from_user.id
    setting_key = callback_query.data.split("set_")[1] # e.g., "index_channel"
    
    if setting_key in SETTINGS:
        state_info = SETTINGS[setting_key]
        # Set the user's state to expect the next message for this specific setting
        USER_STATES[user_id] = f"awaiting_{setting_key}"
        
        await callback_query.answer(state_info["prompt"], show_alert=True)
        await edit_message(callback_query.message, f"Okay, I'm ready for the new value.\n\n{state_info['prompt']}")

async def receive_setting_handler(client, message):
    """Handles the message containing the new value for any setting."""
    user_id = message.from_user.id
    new_value_text = message.text.strip()
    
    # Determine which setting we are waiting for
    state = USER_STATES.get(user_id, "")
    setting_key = state.replace("awaiting_", "")
    
    if setting_key not in SETTINGS:
        return # Should not happen, but as a safeguard

    setting_info = SETTINGS[setting_key]
    
    try:
        new_value = None
        # Validate and convert the input based on the setting's type
        if setting_info["type"] == int:
            new_value = int(new_value_text)
        elif setting_info["type"] == bool:
            if new_value_text.lower() not in ["true", "false"]:
                raise ValueError("Value must be 'true' or 'false'.")
            new_value = new_value_text.lower() == "true"
        else: # String
            new_value = new_value_text

        # Dynamically get the config attribute name (e.g., INDEX_CHANNEL_ID)
        config_key_map = {
            "index_channel": "INDEX_CHANNEL_ID",
            "max_tasks": "MAX_CONCURRENT_TASKS",
            "use_tvmaze": "USE_TVMAZE_TITLES",
            "auth_chats": "AUTHORIZED_CHATS"
        }
        config_key = config_key_map[setting_key]

        # Update the config in memory
        Config.set(config_key, new_value)
        
        await send_message(message, f"**Success!** `{config_key}` has been updated to `{new_value}`.")
        
    except ValueError as e:
        await send_message(message, f"**Error:** That doesn't look like a valid value. {e}. Please try again.")
    except Exception as e:
        LOGGER.error(f"Error setting new value: {e}")
        await send_message(message, "An unexpected error occurred. Please try again.")
    finally:
        # Clean up the user's state
        if user_id in USER_STATES:
            del USER_STATES[user_id]
