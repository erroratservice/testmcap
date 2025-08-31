"""
Clean command handlers registration
"""

import logging
from pyrogram import filters
from pyrogram.handlers import MessageHandler

from bot.core.client import TgClient
from bot.helpers.auth_filters import AuthFilters
from bot.modules.updatemediainfo import updatemediainfo_handler
from bot.modules.indexfiles import indexfiles_handler
from bot.modules.status import status_handler
from bot.modules.settings import settings_handler
from bot.modules.help import help_handler

LOGGER = logging.getLogger(__name__)

async def start_handler(client, message):
    """Welcome message handler"""
    welcome_text = """🤖 **Media Indexing Bot**

🎯 **Purpose:** Extract MediaInfo and organize channel content

📋 **Available Commands:**
• `/updatemediainfo` - Enhance video captions with MediaInfo
• `/indexfiles` - Create organized content indexes
• `/status` - View processing progress
• `/settings` - Configure preferences
• `/help` - Detailed help

🚀 **Ready to index your media content!**"""
    
    await message.reply(welcome_text)

def register_handlers():
    """Register all command handlers"""
    bot = TgClient.bot
    
    handlers = [
        (MessageHandler(start_handler, filters.command("start") & AuthFilters.authorized), "start"),
        (MessageHandler(updatemediainfo_handler, filters.command("updatemediainfo") & AuthFilters.authorized), "updatemediainfo"),
        (MessageHandler(indexfiles_handler, filters.command("indexfiles") & AuthFilters.authorized), "indexfiles"),
        (MessageHandler(status_handler, filters.command("status") & AuthFilters.authorized), "status"),
        (MessageHandler(settings_handler, filters.command("settings") & AuthFilters.authorized), "settings"),
        (MessageHandler(help_handler, filters.command("help") & AuthFilters.authorized), "help"),
    ]
    
    for handler, name in handlers:
        bot.add_handler(handler)
        LOGGER.info(f"✅ Registered handler: /{name}")
    
    LOGGER.info("✅ All command handlers registered successfully")
