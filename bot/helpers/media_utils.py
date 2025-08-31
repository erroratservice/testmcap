"""
Media processing utilities
"""

import asyncio
import logging
from pymediainfo import MediaInfo

LOGGER = logging.getLogger(__name__)

async def extract_mediainfo(file_path):
    """Extract MediaInfo from media file"""
    try:
        # Run MediaInfo extraction in thread pool
        loop = asyncio.get_event_loop()
        media_info = await loop.run_in_executor(None, MediaInfo.parse, file_path)
        
        # Extract relevant information
        result = {
            'video_streams': [],
            'audio_streams': [],
            'subtitle_streams': []
        }
        
        for track in media_info.tracks:
            if track.track_type == 'Video':
                result['video_streams'].append({
                    'codec': track.format or 'Unknown',
                    'width': track.width,
                    'height': track.height,
                    'fps': track.frame_rate
                })
            elif track.track_type == 'Audio':
                result['audio_streams'].append({
                    'codec': track.format or 'Unknown', 
                    'language': track.language or 'Unknown',
                    'channels': track.channel_s
                })
            elif track.track_type == 'Text':
                result['subtitle_streams'].append({
                    'language': track.language or 'Unknown',
                    'format': track.format or 'Unknown'
                })
        
        # Extract primary info
        if result['video_streams']:
            video = result['video_streams'][0]
            result['video_codec'] = video['codec']
            result['width'] = video['width']
            result['height'] = video['height']
        
        return result
        
    except Exception as e:
        LOGGER.error(f"MediaInfo extraction error: {e}")
        return {}
