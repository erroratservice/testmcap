"""
Pyrofork inline keyboard utilities
"""

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def build_settings_keyboard():
    """Builds the main settings keyboard."""
    buttons = [
        [
            InlineKeyboardButton("Set Index Channel", callback_data="set_index_channel"),
            InlineKeyboardButton("Set Max Tasks", callback_data="set_max_tasks")
        ],
        [
            InlineKeyboardButton("Toggle TVMaze Titles", callback_data="set_use_tvmaze"),
            InlineKeyboardButton("Set Auth Chats", callback_data="set_auth_chats")
        ]
    ]
    return InlineKeyboardMarkup(buttons)
