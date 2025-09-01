"""
Pyrofork inline keyboard utilities
"""

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def build_settings_keyboard():
    """Builds the main settings keyboard."""
    buttons = [
        [InlineKeyboardButton("Set Index Channel", callback_data="set_index_channel")],
    ]
    return InlineKeyboardMarkup(buttons)
