"""
File processing utilities with robust text file reading.
"""
import re
import os
import aiofiles
import logging
from datetime import datetime

LOGGER = logging.getLogger(__name__)

async def extract_channel_list(reply_message):
    """Extract channel IDs from text file with robust encoding handling."""
    try:
        if reply_message.document:
            file_path = await reply_message.download(in_memory=True)
            content = file_path.getvalue().decode('utf-8', errors='ignore')
        else:
            content = reply_message.text or ""
        
        channels = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith('-100') and line.lstrip('-').isdigit():
                channels.append(int(line))
        
        return channels
    except Exception as e:
        LOGGER.error(f"Channel list extraction error: {e}")
        return []

async def download_media_chunk(message, chunk_size=5*1024*1024):
    """Download small media chunk for analysis"""
    try:
        temp_file = f"/tmp/mediainfo_{message.id}_{int(datetime.now().timestamp())}"
        
        async for chunk in message.stream_media(limit=1):
            async with aiofiles.open(temp_file, 'wb') as f:
                await f.write(chunk)
            break
        
        return temp_file
    except Exception as e:
        LOGGER.error(f"Chunk download error: {e}")
        return None
