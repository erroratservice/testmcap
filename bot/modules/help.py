"""
Help command with comprehensive documentation
"""

import logging
from bot.helpers.message_utils import send_message

LOGGER = logging.getLogger(__name__)

async def help_handler(client, message):
    """Handler for /help command"""
    help_text = """🤖 **Media Indexing Bot - Complete Guide**

**🎯 Purpose:**
This bot extracts MediaInfo from video files and creates organized content indexes for Telegram channels.

**📋 Available Commands:**

🏠 `/start` - Initialize bot and show welcome message
📹 `/updatemediainfo` - Extract MediaInfo and enhance captions  
📁 `/indexfiles` - Scan and organize channel content
📊 `/status` - Show current processing progress  
⚙️ `/settings` - Configure your preferences
❓ `/help` - Show this comprehensive guide

━━━━━━━━━━━━━━━━━━━━

**📹 MediaInfo Enhancement:**

**Usage:**
• `/updatemediainfo -1001234567890` - Process specific channel
• `/updatemediainfo` (reply to file) - Bulk process channels

**What it does:**
✅ Downloads small chunks for MediaInfo analysis (5MB max)
✅ Extracts video codec, resolution, audio tracks, languages
✅ Updates captions with clean MediaInfo data
✅ Preserves original captions and adds technical details

**Example Enhanced Caption:**
  
