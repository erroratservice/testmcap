"""
Settings command for user preferences
"""

import logging
from bot.helpers.message_utils import send_message
from bot.helpers.keyboard_utils import build_settings_keyboard

LOGGER = logging.getLogger(__name__)

async def settings_handler(client, message):
    """Handler for /settings command"""
    try:
        user_id = message.from_user.id
        
        # Get user preferences (from database in production)
        preferences = get_user_preferences(user_id)
        
        settings_text = f"""⚙️ **User Settings**
👤 **User:** {message.from_user.mention}

**Current Preferences:**
├─ 📹 **MediaInfo Enhancement:** {'✅ Enabled' if preferences.get('mediainfo_enabled', True) else '❌ Disabled'}
├─ 🔔 **Progress Notifications:** {'✅ Enabled' if preferences.get('notifications', True) else '❌ Disabled'}
├─ 📺 **Default Channels:** {len(preferences.get('default_channels', []))} configured
├─ 🎨 **Caption Format:** {preferences.get('caption_format', 'Standard')}
└─ 🌍 **Timezone:** Asia/Kolkata

**Bot Status:**
├─ 🤖 **Version:** v1.0.0
├─ 📊 **Index Channel:** {'✅ Configured' if True else '❌ Not Set'}
└─ 💾 **Database:** {'✅ Connected' if True else '❌ Disconnected'}

Use buttons below to modify settings."""
        
        keyboard = build_settings_keyboard(user_id)
        await send_message(message, settings_text, keyboard)
        
    except Exception as e:
        LOGGER.error(f"Settings handler error: {e}")
        await send_message(message, f"❌ Error loading settings: {e}")

def get_user_preferences(user_id):
    """Get user preferences (placeholder - use database in production)"""
    return {
        'mediainfo_enabled': True,
        'notifications': True,
        'default_channels': [],
        'caption_format': 'Standard'
    }
