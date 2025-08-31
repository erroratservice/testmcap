"""
Authorization filters based on working dual-session repository pattern
"""

from pyrogram.filters import create
from bot.core.config import Config

class AuthFilters:
    """Custom authorization filters using working repository pattern"""
    
    async def owner_filter(self, _, update):
        """Owner authorization filter"""
        user = update.from_user or update.sender_chat
        return user.id == Config.OWNER_ID
    
    owner = create(owner_filter)
    
    async def authorized_user(self, _, update):
        """Authorized user filter"""
        user = update.from_user or update.sender_chat
        uid = user.id
        
        # Owner is always authorized
        if uid == Config.OWNER_ID:
            return True
        
        # Check authorized chats
        if Config.AUTHORIZED_CHATS:
            try:
                authorized_ids = [int(x.strip()) for x in Config.AUTHORIZED_CHATS.split(',') if x.strip()]
                return uid in authorized_ids
            except (ValueError, AttributeError):
                pass
        
        return False
    
    authorized = create(authorized_user)
