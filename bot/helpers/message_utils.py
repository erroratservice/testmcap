"""
Message utility functions for clean communication
"""

import asyncio
import logging
from pyrogram.errors import FloodWait, MessageNotModified
from bot.core.client import TgClient

LOGGER = logging.getLogger(__name__)

async def send_message(message, text, keyboard=None):
    """Send message with flood control"""
    try:
        return await TgClient.bot.send_message(
            chat_id=message.chat.id,
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    except FloodWait as e:
        LOGGER.warning(f"FloodWait: {e.value} seconds")
        await asyncio.sleep(e.value)
        return await send_message(message, text, keyboard)
    except Exception as e:
        LOGGER.error(f"Send message error: {e}")
        return None

async def edit_message(message, text, keyboard=None):
    """Edit message with error handling"""
    try:
        if hasattr(message, 'edit_text'):
            return await message.edit_text(text, reply_markup=keyboard)
        else:
            return await TgClient.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.id,
                text=text,
                reply_markup=keyboard
            )
    except (FloodWait, MessageNotModified) as e:
        if isinstance(e, FloodWait):
            await asyncio.sleep(e.value)
            return await edit_message(message, text, keyboard)
    except Exception as e:
        LOGGER.error(f"Edit message error: {e}")
        return None
