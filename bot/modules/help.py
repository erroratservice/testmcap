"""
Help command with comprehensive documentation
"""

import logging
from bot.helpers.message_utils import send_message

LOGGER = logging.getLogger(__name__)

async def help_handler(client, message):
    """Handler for /help command"""
    help_text = """**Media Indexing Bot - Complete Guide**

**Purpose:**
This bot extracts MediaInfo from video files and creates organized content indexes for Telegram channels.

**Available Commands:**

`/start` - Initialize bot and show welcome message
`/updatemediainfo` - Extract MediaInfo and enhance captions  
`/indexfiles` - Scan and organize channel content
`/status` - Show current processing progress  
`/settings` - Configure your preferences
`/help` - Show this comprehensive guide
`/findencoders` - Find new, unknown encoder tags in a channel

━━━━━━━━━━━━━━━━━━━━

**MediaInfo Enhancement:**

**Usage:**
• `/updatemediainfo -1001234567890` - Process specific channel. Use `-f` to retry failed files with a full download, and `-rescan` to process all files again.
• `/updatemediainfo` (reply to file) - Bulk process channels from a text file.

**What it does:**
- Downloads small chunks for efficient MediaInfo analysis.
- Extracts video codec, resolution, and audio track details.
- Updates captions with clean, standardized MediaInfo.
- Preserves the original caption text.

**Example Enhanced Caption:**
  
Original Caption Here

Video: X265 1080p
Audio: 2 (ENG, HIN)

━━━━━━━━━━━━━━━━━━━━

**Content Indexing:**

**Usage:**
• `/indexfiles -1001234567890` - Index a specific channel. Use `-rescan` to clear old data and re-index.
• `/indexfiles` (reply to file) - Bulk index channels from a text file.

**What it does:**
- Scans all media files in the target channel.
- Organizes content by title, season, and episode.
- Groups different quality and codec versions under the same title.
- Posts a cleanly formatted index to your configured index channel.

**Example Index Post:**
Motherland꞉ Fort Salem (2020) -

Season 1 (8 Episodes)
└─ 1080P X265 (GHOST): E02, E04-E10
Season 2 (9 Episodes)
└─ 1080P X265 (GHOST): E01-E04, E06-E10

━━━━━━━━━━━━━━━━━━━━

**Encoder Discovery:**

**Usage:**
• `/findencoders -1001234567890` - Find potential new encoders in a channel.

**What it does:**
- Scans every filename in the specified channel.
- Filters out all encoders and tags already known to the bot.
- Generates an `encoders.txt` file listing all potential new encoder tags and how many times they appeared.
- This helps you discover new tags to add to your list, improving indexing accuracy.

━━━━━━━━━━━━━━━━━━━━

**Bulk Processing File Format:**

Create a text file with one Telegram Channel ID per line:
-1001234567890
-1009876543210
-1001122334455

Then, simply reply to this file with your desired command (`/indexfiles` or `/updatemediainfo`).

━━━━━━━━━━━━━━━━━━━━

**Progress Tracking:**

Use `/status` to monitor active operations with real-time progress updates, ETA, and interactive controls.

━━━━━━━━━━━━━━━━━━━━

**Requirements:**

- **Bot:** Must be an admin in target channels to edit captions.
- **User Session:** Must have read access to source channels and write access to the index channel.

━━━━━━━━━━━━━━━━━━━━

**Features:**

**Lightning Fast:** Optimized for minimal resource usage.
**Reliable:** Built-in error handling and retry logic.
**Smart Processing:** Uses chunked downloads and falls back to full downloads only when necessary.
**Bulk Operations:** Process hundreds of channels efficiently.
**Progress Tracking:** Real-time updates with interactive controls.

**Support:** Contact the bot owner for technical assistance.
**Version:** v1.0.0 - Built for media indexing excellence!"""
    
    await send_message(message, help_text)
