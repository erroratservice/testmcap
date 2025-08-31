"""
Clean authorization filters for Media Indexing Bot
"""

from pyrogram import filters
from bot.core.config import Config

class AuthFilters:
    """Custom authorization filters"""
    
    @staticmethod
    def authorized_filter(_, __, message):
        """Check if user is authorized"""
        user_id = message.from_user.id if message.from_user else None
        
        if not user_id:
            return False
        
        # Owner is always authorized
        if user_id == Config.OWNER_ID:
            return True
        
        # Check authorized chats
        if Config.AUTHORIZED_CHATS:
            try:
                authorized_ids = [int(x.strip()) for x in Config.AUTHORIZED_CHATS.split(',') if x.strip()]
                return user_id in authorized_ids
            except ValueError:
                pass
        
        # If no restrictions, allow owner only
        return False
    
    authorized = filters.create(authorized_filter)
