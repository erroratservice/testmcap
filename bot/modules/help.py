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
  
Original Caption Here

Video: H264 1080p
Audio: 2 (ENG, HIN)


━━━━━━━━━━━━━━━━━━━━

**📁 Content Indexing:**

**Usage:**
• `/indexfiles -1001234567890` - Index specific channel
• `/indexfiles` (reply to file) - Bulk index channels

**What it does:**
✅ Scans all media files in channel
✅ Organizes by title → season → episode
✅ Groups by quality and codec variants
✅ Posts organized index to configured channel

**Example Organized Index:**
📺 Channel Name - Content Index
📅 Generated: 30/08/2025 18:07 IST
📁 Total Files: 1,247
🎬 Total Titles: 85

🎬 Breaking Bad
📺 Season 1
└── Episode 1: 1080p (x265) | 720p (x264)
└── Episode 2: 1080p (x265)

━━━━━━━━━━━━━━━━━━━━

**📝 Bulk Processing File Format:**

Create a text file with channel IDs (one per line):
-1001234567890
-1009876543210
-1001122334455

Then reply to this file with your command.

━━━━━━━━━━━━━━━━━━━━

**📊 Progress Tracking:**

Use `/status` to monitor active operations:
• Real-time progress updates
• Processing speed and ETA
• Interactive pause/resume controls
• Error reporting and statistics

━━━━━━━━━━━━━━━━━━━━

**🔧 Requirements:**

**For MediaInfo Updates:**
• Bot must be admin in target channels (for caption editing)
• User session must have message editing permissions

**For Content Indexing:**
• User session must have read access to channels
• Bot needs access to configured index channel

━━━━━━━━━━━━━━━━━━━━

**⚡ Features:**

✅ **Lightning Fast:** Optimized for minimal resource usage
✅ **Reliable:** Built-in error handling and retry logic
✅ **Smart Processing:** Only downloads what's needed
✅ **Bulk Operations:** Process hundreds of channels efficiently
✅ **Progress Tracking:** Real-time updates with interactive controls
✅ **User Preferences:** Customizable settings and notifications

━━━━━━━━━━━━━━━━━━━━

**💡 Pro Tips:**

• Use bulk operations for multiple channels to save time
• Check `/status` regularly during long operations
• Configure settings once to customize behavior
• MediaInfo extraction works best on video files
• Index generation creates hierarchical organization

**🆘 Support:** Contact bot owner for technical assistance
**📚 Version:** v1.0.0 - Built for media indexing excellence!"""
    
    await send_message(message, help_text)
