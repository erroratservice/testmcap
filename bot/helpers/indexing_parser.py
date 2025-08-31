"""
Advanced parser for media filenames and captions.
Handles complex, real-world naming conventions.
"""
import re

KNOWN_ENCODERS = {
    'PSA', 'RARBG', 'YIFY', 'YTS', 'EZTV', 'ETTV', 'TGX', 'ION10',
    'SPARKS', 'CMRG', 'FGT', 'STRiFE', 'KILLERS', 'DIMENSION', 'KONTRAST',
    'AMZN', 'NF', 'HULU', 'ATVP', 'DSNP', 'MAX', 'WEB-DL', 'PrimeFix'
}

def parse_media_info(filename, caption=None):
    """
    Intelligently parses media info from filename and caption.
    """
    text_to_parse = caption if caption and 's' in caption.lower() and 'e' in caption.lower() else filename
    
    # --- Part File Detection ---
    part_match = re.search(r'\.(00\d)\.', filename)
    if part_match and part_match.group(1) != '001':
        return None

    # --- Metadata Extraction ---
    quality = get_quality(text_to_parse)
    codec = get_codec(text_to_parse)
    encoder = get_encoder(text_to_parse)

    # --- Core Information Extraction (Title, Season, Episode) ---
    # Create a cleaner version of the name for title extraction
    clean_name = re.sub(r'[\._\-\[\]\(\)]', ' ', filename)
    # Remove all known metadata tags to isolate the title and S/E info
    for tag in [quality, codec, encoder]:
        if tag != 'Unknown':
            clean_name = re.sub(r'\b' + re.escape(tag) + r'\b', '', clean_name, flags=re.IGNORECASE)
    
    series_pattern = re.compile(r'(.+?)\s+s(\d{1,2})\s*e(\d{1,3})', re.IGNORECASE)
    movie_pattern = re.compile(r'(.+?)\s+(\d{4})', re.IGNORECASE)

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
    if match:
        quality = match.group(1).upper()
        return "4K" if "2160" in quality else quality
    return 'Unknown'

def get_codec(text):
    if re.search(r'\b(AV1)\b', text, re.IGNORECASE): return 'AV1'
    if re.search(r'\b(VP9)\b', text, re.IGNORECASE): return 'VP9'
    if re.search(r'\b(HEVC|x265|H\s*265)\b', text, re.IGNORECASE): return 'X265'
    if re.search(r'\b(AVC|x264|H\s*264)\b', text, re.IGNORECASE): return 'X264'
    return 'Unknown'

def get_encoder(text):
    """
    Smarter encoder detection that prioritizes known groups and specific patterns.
    """
    # Pattern 1: Look for a hyphenated group at the end (e.g., "-PSA")
    match = re.search(r'-([a-zA-Z0-9]+)$', text.replace('.mkv', '').replace('.mp4', ''))
    if match and match.group(1).upper() not in ["DUAL", "AUDIO"]:
        return match.group(1).upper()

    # Pattern 2: Look for known encoder tags anywhere in the string
    # We reverse the string to find the last occurrence first, which is usually the encoder
    reversed_text = text[::-1]
    for encoder in KNOWN_ENCODERS:
        if re.search(r'\b' + re.escape(encoder[::-1]) + r'\b', reversed_text, re.IGNORECASE):
            return encoder
            
    return 'Unknown'
