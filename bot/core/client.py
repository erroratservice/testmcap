"""
Pyrofork client management with peer ID error handling
"""

import logging
from pyrogram import Client
from pyrogram.errors import AuthKeyDuplicated, UserDeactivated
from bot.core.config import Config
import pyrogram.utils as pyroutils

# Fix for new Telegram peer ID formats
pyroutils.MIN_CHAT_ID = -999999999999
pyroutils.MIN_CHANNEL_ID = -100999999999999

LOGGER = logging.getLogger(__name__)

class TgClient:
    """Manages bot and user Telegram clients with Pyrofork"""
    
    bot = None
    user = None
    
    @classmethod
    async def initialize(cls):
        """Initialize both bot and user clients"""
        try:
            cls.bot = Client(
                name="MediaIndexBot",
                api_id=Config.TELEGRAM_API,
                api_hash=Config.TELEGRAM_HASH,
                bot_token=Config.BOT_TOKEN,
                workers=8
            )
            
            cls.user = Client(
                name="MediaIndexUser", 
                api_id=Config.TELEGRAM_API,
                api_hash=Config.TELEGRAM_HASH,
                session_string=Config.USER_SESSION_STRING,
                workers=8
            )
            
            await cls.bot.start()
            bot_info = await cls.bot.get_me()
            LOGGER.info(f"Bot client started as @{bot_info.username}")

            await cls.user.start()
            user_info = await cls.user.get_me()
            LOGGER.info(f"User client started as @{user_info.username}")
            
        except AuthKeyDuplicated:
            LOGGER.error("Auth key duplicated. Please regenerate the user session string.")
            raise
        except UserDeactivated:
            LOGGER.error("User account is deactivated. Check the user session.")
            raise
        except Exception as e:
            LOGGER.error(f"Failed to initialize clients: {e}")
            raise
    
    @classmethod
    async def stop(cls):
        """Stop both clients gracefully"""
        try:
            if cls.bot and cls.bot.is_connected:
                await cls.bot.stop()
            if cls.user and cls.user.is_connected:
                await cls.user.stop()
            LOGGER.info("All clients stopped gracefully.")
        except Exception as e:
            LOGGER.error(f"Error stopping clients: {e}")
