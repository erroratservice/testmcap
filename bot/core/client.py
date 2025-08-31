"""
Pyrofork client management with peer ID error handling
"""

from pyrogram import Client
from pyrogram.errors import AuthKeyDuplicated, UserDeactivated
from bot.core.config import Config
import pyrogram.utils as pyroutils

# Fix for new Telegram peer ID formats
pyroutils.MIN_CHAT_ID = -999999999999
pyroutils.MIN_CHANNEL_ID = -100999999999999

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
            await cls.user.start()
            
        except (AuthKeyDuplicated, UserDeactivated):
            raise
        except Exception:
            raise
    
    @classmethod
    async def stop(cls):
        """Stop both clients gracefully"""
        try:
            if cls.bot:
                await cls.bot.stop()
            if cls.user:
                await cls.user.stop()
        except Exception:
            pass
