"""
Advanced parser for media filenames and captions.
"""
import re

def parse_media_info(filename, caption=None):
    """
    Intelligently parses media info from filename and caption.
    Prioritizes caption for quality/codec/encoder, falls back to filename.
    """
    text_to_parse = caption if caption else filename
    
    # --- Part File Detection ---
    part_match = re.search(r'\.(00\d)\.', filename)
    if part_match and part_match.group(1) != '001':
        return None # Skip non-first part files

    # --- Core Information Extraction (from filename) ---
    clean_name = re.sub(r'[\._\-\[\]\(\)]', ' ', filename)
    
    series_pattern = re.compile(r'(.+?)\s+s(\d{1,2})\s*e(\d{1,3})', re.IGNORECASE)
    movie_pattern = re.compile(r'(.+?)\s+(\d{4})', re.IGNORECASE)

    # --- Metadata Extraction (from caption or filename) ---
    quality = get_quality(text_to_parse)
    codec = get_codec(text_to_parse)
    encoder = get_encoder(text_to_parse)

    series_match = series_pattern.search(clean_name)
    if series_match:
        title, season, episode = series_match.groups()
        return {
            'title': title.strip().title(),
            'season': int(season),
            'episode': int(episode),
            'quality': quality,
            'codec': codec,
            'encoder': encoder,
            'type': 'series'
        }

    movie_match = movie_pattern.search(clean_name)
    if movie_match:
        title, year = movie_match.groups()
        return {
            'title': f"{title.strip().title()} ({year})",
            'year': int(year),
            'quality': quality,
            'codec': codec,
            'encoder': encoder,
            'type': 'movie'
        }
        
    return None

def get_quality(text):
    match = re.search(r'\b(4K|2160p|1080p|720p|540p|480p)\b', text, re.IGNORECASE)
    return match.group(1).upper() if match else 'Unknown'

def get_codec(text):
    if re.search(r'\b(AV1)\b', text, re.IGNORECASE): return 'AV1'
    if re.search(r'\b(VP9)\b', text, re.IGNORECASE): return 'VP9'
    if re.search(r'\b(HEVC|x265)\b', text, re.IGNORECASE): return 'X265'
    if re.search(r'\b(AVC|x264)\b', text, re.IGNORECASE): return 'X264'
    return 'Unknown'

def get_encoder(text):
    # Extracts encoder/release group, often found in brackets or as a final tag
    match = re.search(r'[\(\[-]([A-Za-z0-9\.-]+)[\)\]-]?$', text)
    return match.group(1).upper() if match else 'WEB-DL'
