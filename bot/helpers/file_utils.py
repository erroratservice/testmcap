"""
File processing utilities
"""

import re
import os
import aiofiles
import logging
from datetime import datetime

LOGGER = logging.getLogger(__name__)

async def extract_channel_list(reply_message):
    """Extract channel IDs from text file"""
    try:
        if reply_message.document:
            file_path = await reply_message.download(in_memory=True)
            content = file_path.getvalue().decode('utf-8')
        else:
            content = reply_message.text or ""
        
        channels = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith('-100') and line.isdigit():
                channels.append(int(line))
        
        return channels
    except Exception as e:
        LOGGER.error(f"Channel list extraction error: {e}")
        return []

async def download_media_chunk(message, chunk_size=5*1024*1024):
    """Download small media chunk for analysis"""
    try:
        temp_file = f"/tmp/mediainfo_{message.id}_{int(datetime.now().timestamp())}"
        
        # Download first chunk only
        async for chunk in message.stream_media(limit=1):
            async with aiofiles.open(temp_file, 'wb') as f:
                await f.write(chunk)
            break
        
        return temp_file
    except Exception as e:
        LOGGER.error(f"Chunk download error: {e}")
        return None

def parse_media_filename(filename):
    """Parse media filename for metadata"""
    patterns = [
        # TV Series: Show.Name.S01E01.Quality.Codec
        r'(.+?)\.S(\d+)E(\d+)\..*?(\d{3,4}p).*?\.(x264|x265|HEVC)',
        # Movie: Movie.Name.Year.Quality.Codec  
        r'(.+?)\.(\d{4})\..*?(\d{3,4}p).*?\.(x264|x265|HEVC)',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, filename, re.IGNORECASE)
        if match and 'S' in pattern and 'E' in pattern:
            return {
                'title': match.group(1).replace('.', ' ').strip(),
                'season': int(match.group(2)),
                'episode': int(match.group(3)), 
                'quality': match.group(4),
                'codec': match.group(5),
                'type': 'series'
            }
        elif match:
            return {
                'title': match.group(1).replace('.', ' ').strip(),
                'year': int(match.group(2)),
                'quality': match.group(3),
                'codec': match.group(4),
                'type': 'movie'
            }
    
    return None
