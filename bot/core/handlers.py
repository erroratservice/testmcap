"""
Pyrofork command handlers registration
"""

import logging
import asyncio
from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot.core.client import TgClient
from bot.helpers.auth_filters import AuthFilters
from bot.modules.updatemediainfo import updatemediainfo_handler
from bot.modules.indexfiles import indexfiles_handler
from bot.modules.status import status_handler
from bot.modules.settings import settings_handler
from bot.modules.help import help_handler
from bot.core.tasks import ACTIVE_TASKS

LOGGER = logging.getLogger(__name__)

async def start_handler(client, message):
    """Welcome message handler"""
    welcome_text = """🤖 **Media Indexing Bot** *(Powered by Pyrofork)*

🎯 **Purpose:** Extract MediaInfo and organize channel content

📋 **Available Commands:**
• `/updatemediainfo` - Enhance video captions with MediaInfo
• `/indexfiles` - Create organized content indexes
• `/status` - View processing progress
• `/settings` - Configure preferences
• `/help` - Detailed help

🚀 **Ready to index your media content!**"""
    
    await message.reply_text(welcome_text)

async def cancel_task_callback(client, callback_query):
    """Handles the 'Cancel' button press for a running task."""
    scan_id = callback_query.data.split("_", 1)[1]
    
    task_to_cancel = ACTIVE_TASKS.get(scan_id)
    
    if task_to_cancel:
        task_to_cancel.cancel()
        try:
            await callback_query.answer("Sent cancellation request for the task.", show_alert=True)
        except:
            pass
    else:
        try:
            await callback_query.answer("This task is no longer running or may have already completed.", show_alert=True)
        except:
            pass

def register_handlers():
    """Register all command and callback handlers with Pyrofork"""
    bot = TgClient.bot
    
    command_handlers = [
        MessageHandler(start_handler, filters.command("start") & AuthFilters.authorized),
        MessageHandler(updatemediainfo_handler, filters.command("updatemediainfo") & AuthFilters.authorized),
        MessageHandler(indexfiles_handler, filters.command("indexfiles") & AuthFilters.authorized),
        MessageHandler(status_handler, filters.command("status") & AuthFilters.authorized),
        MessageHandler(settings_handler, filters.command("settings") & AuthFilters.authorized),
        MessageHandler(help_handler, filters.command("help") & AuthFilters.authorized),
    ]
    
    for handler in command_handlers:
        bot.add_handler(handler)
    
    callback_handlers = [
        CallbackQueryHandler(cancel_task_callback, filters.regex("^cancel_")),
    ]

    for handler in callback_handlers:
        bot.add_handler(handler)

    LOGGER.info("✅ All command and callback handlers registered successfully")
