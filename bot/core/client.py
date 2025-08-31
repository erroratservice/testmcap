"""
Enhanced Telegram client management with error handling
"""

import asyncio
import logging
from pyrogram import Client, enums, utils as pyroutils
from pyrogram.errors import AuthKeyDuplicated, UserDeactivated, PeerIdInvalid
from bot.core.config import Config

LOGGER = logging.getLogger(__name__)

pyroutils.MIN_CHAT_ID = -999999999999
pyroutils.MIN_CHANNEL_ID = -100999999999999
class TgClient:
    """Manages bot and user Telegram clients with enhanced error handling"""
    
    bot = None
    user = None
    
    @classmethod
    async def initialize(cls):
        """Initialize both bot and user clients with error handling"""
        try:
            # Bot client
            cls.bot = Client(
                name="MediaIndexBot",
                api_id=Config.TELEGRAM_API,
                api_hash=Config.TELEGRAM_HASH,
                bot_token=Config.BOT_TOKEN,
                workers=8
            )
            
            # User client for channel access with error handling
            cls.user = Client(
                name="MediaIndexUser", 
                api_id=Config.TELEGRAM_API,
                api_hash=Config.TELEGRAM_HASH,
                session_string=Config.USER_SESSION_STRING,
                workers=8,
                # Add error handling for peer resolution
                parse_mode=None
            )
            
            await cls.bot.start()
            await cls.user.start()
            
            # Add global error handler for peer issues
            cls.user.add_handler(cls._error_handler, group=-1)
            
            bot_info = await cls.bot.get_me()
            user_info = await cls.user.get_me()
            
            LOGGER.info(f"✅ Bot client started: @{bot_info.username}")
            LOGGER.info(f"✅ User client started: @{user_info.username}")
            
        except AuthKeyDuplicated:
            LOGGER.error("❌ Auth key duplicated. Please regenerate session string.")
            raise
        except UserDeactivated:
            LOGGER.error("❌ User account deactivated. Check user session.")
            raise
        except Exception as e:
            LOGGER.error(f"❌ Failed to initialize clients: {e}")
            raise
    
    @staticmethod
    async def _error_handler(client, update, exception):
        """Global error handler for peer ID issues"""
        if isinstance(exception, (PeerIdInvalid, ValueError)) and "Peer id invalid" in str(exception):
            # Extract peer ID from error message
            peer_id = str(exception).split(":")[-1].strip() if ":" in str(exception) else "unknown"
            LOGGER.warning(f"⚠️ Ignoring inaccessible peer: {peer_id}")
            return  # Silently ignore
        
        # Log other errors normally
        LOGGER.error(f"❌ Unhandled error: {exception}")
    
    @classmethod
    async def stop(cls):
        """Stop both clients gracefully"""
        try:
            if cls.bot:
                await cls.bot.stop()
            if cls.user:
                await cls.user.stop()
            LOGGER.info("✅ All clients stopped gracefully")
        except Exception as e:
            LOGGER.error(f"❌ Error stopping clients: {e}")
