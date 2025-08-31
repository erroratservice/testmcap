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
    """
    Parse media filename for metadata using more flexible regex.
    Handles various separators and optional parts.
    """
    # Sanitize filename by replacing various separators with a space
    clean_name = re.sub(r'[\._\-\[\]\(\)]', ' ', filename)
    
    # Pattern for TV Series (e.g., "Show Name S01 E01", "Show.Name.S01E01")
    series_pattern = re.compile(
        r'(.+?)\s+'          # Title (non-greedy)
        r's(\d{1,2})\s*'     # Season number (S01)
        r'e(\d{1,3})'        # Episode number (E01)
        r'(.*)',             # Rest of the string
        re.IGNORECASE
    )
    
    # Pattern for Movies (e.g., "Movie Name 2023", "Movie.Name.(2023)")
    movie_pattern = re.compile(
        r'(.+?)\s+'          # Title (non-greedy)
        r'(\d{4})'           # Year (2023)
        r'(.*)',             # Rest of the string
        re.IGNORECASE
    )

    series_match = series_pattern.search(clean_name)
    if series_match:
        title, season, episode, rest = series_match.groups()
        quality = get_quality(rest)
        codec = get_codec(rest)
        return {
            'title': title.strip(),
            'season': int(season),
            'episode': int(episode), 
            'quality': quality,
            'codec': codec,
            'type': 'series'
        }

    movie_match = movie_pattern.search(clean_name)
    if movie_match:
        title, year, rest = movie_match.groups()
        quality = get_quality(rest)
        codec = get_codec(rest)
        return {
            'title': title.strip(),
            'year': int(year),
            'quality': quality,
            'codec': codec,
            'type': 'movie'
        }
    
    return None

def get_quality(text):
    """Extracts video quality (e.g., 1080p, 720p) from text."""
    match = re.search(r'(\d{3,4}p)', text, re.IGNORECASE)
    return match.group(1) if match else 'Unknown'

def get_codec(text):
    """Extracts video codec (e.g., x264, x265, HEVC) from text."""
    if re.search(r'x265|hevc', text, re.IGNORECASE):
        return 'x265'
    if re.search(r'x264', text, re.IGNORECASE):
        return 'x264'
    return 'Unknown'
