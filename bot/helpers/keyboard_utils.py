"""
Inline keyboard utility functions
"""

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def build_status_keyboard(process_id):
    """Build status control keyboard"""
    buttons = [
        [InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_{process_id}"),
         InlineKeyboardButton("⏹️ Cancel", callback_data=f"cancel_{process_id}")],
        [InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{process_id}")]
    ]
    return InlineKeyboardMarkup(buttons)

def build_settings_keyboard(user_id):
    """Build settings control keyboard"""
    buttons = [
        [InlineKeyboardButton("📹 Toggle MediaInfo", callback_data=f"toggle_mediainfo_{user_id}")],
        [InlineKeyboardButton("🔔 Toggle Notifications", callback_data=f"toggle_notifications_{user_id}")],
        [InlineKeyboardButton("📺 Manage Channels", callback_data=f"manage_channels_{user_id}")],
        [InlineKeyboardButton("🔄 Reset Settings", callback_data=f"reset_settings_{user_id}")]
    ]
    return InlineKeyboardMarkup(buttons)
