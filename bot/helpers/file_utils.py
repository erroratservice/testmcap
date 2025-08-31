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

def parse_media_info(filename, caption=None):
    """
    Intelligently parses media info, prioritizing the caption and falling back to the filename.
    """
    # 1. First, try to get quality and codec from the caption
    caption_quality = None
    caption_codec = None
    if caption:
        # Regex to find "Video: CODEC QUALITY"
        video_line_match = re.search(r'Video:\s*([A-Z0-9]+)\s*(\d{3,4}p|4K)', caption, re.IGNORECASE)
        if video_line_match:
            caption_codec = video_line_match.group(1).upper()
            caption_quality = video_line_match.group(2)

    # 2. Sanitize and parse the filename for title, season, year etc.
    clean_name = re.sub(r'[\._\-\[\]\(\)]', ' ', filename)
    
    series_pattern = re.compile(r'(.+?)\s+s(\d{1,2})\s*e(\d{1,3})', re.IGNORECASE)
    movie_pattern = re.compile(r'(.+?)\s+(\d{4})', re.IGNORECASE)

    series_match = series_pattern.search(clean_name)
    if series_match:
        title, season, episode = series_match.groups()
        # Use caption data if available, otherwise parse from filename
        quality = caption_quality or get_quality_from_text(filename)
        codec = caption_codec or get_codec_from_text(filename)
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
        title, year = movie_match.groups()
        # Use caption data if available, otherwise parse from filename
        quality = caption_quality or get_quality_from_text(filename)
        codec = caption_codec or get_codec_from_text(filename)
        return {
            'title': title.strip(),
            'year': int(year),
            'quality': quality,
            'codec': codec,
            'type': 'movie'
        }
    
    return None

def get_quality_from_text(text):
    """Extracts video quality (e.g., 1080p, 720p, 4K) from text."""
    match = re.search(r'(\d{3,4}p|4K)', text, re.IGNORECASE)
    return match.group(1) if match else 'Unknown'

def get_codec_from_text(text):
    """Extracts video codec (e.g., x264, x265, HEVC) from text."""
    if re.search(r'x265|hevc', text, re.IGNORECASE):
        return 'x265'
    if re.search(r'x264|h264|avc', text, re.IGNORECASE):
        return 'x264'
    return 'Unknown'
