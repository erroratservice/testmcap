"""
Corrected authorization filters for Pyrofork with proper signature
"""

from pyrogram import filters
from bot.core.config import Config

class AuthFilters:
    """Custom authorization filters with correct Pyrofork signature"""
    
    @staticmethod
    async def authorized_filter(flt, client, message):
        """
        Authorization filter - MUST have exactly 3 parameters:
        flt: filter instance
        client: client instance  
        message: message object
        """
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
        
        return False
    
    # Create the filter using the correct function
    authorized = filters.create(authorized_filter)
