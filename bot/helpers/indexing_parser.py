"""
Advanced parser for media filenames and captions with improved movie/series detection.
"""
import re

KNOWN_ENCODERS = {
    'GHOST', 'AMBER', 'ELITE', 'BONE', 'CELDRA', 'MEGUSTA', 'EDGE2020',
    'PAHE', 'DARKFLIX', 'D3G', 'PHOCIS', 'ZTR', 'TIPEX', 'PRIMEFIX',
    'CODSWALLOP', 'RAWR', 'STAR', 'JFF', 'HEEL', 'CBFM', 'XWT', 'STC',
    'KITSUNE', 'AFG', 'EDITH', 'MSD', 'SDH', 'AOC', 'G66', 'PSA',
    'Tigole', 'QxR', 'TEPES', 'VXT', 'Vyndros', 'Telly', 'HQMUX',
    'W4NK3R', 'BETA', 'BHDStudio', 'FraMeSToR', 'DON', 'DRONES', 'FGT',
    'SPARKS', 'NoGroup', 'KiNGDOM', 'NTb', 'NTG', 'KOGi', 'SKG', 'EVO',
    'iON10', 'mSD', 'CMRG', 'KiNGS', 'MiNX', 'FUM', 'GalaxyRG',
    'GalaxyTV', 'EMBER', 'QOQ', 'BaoBao', 'YTS', 'YIFY', 'RARBG', 'ETRG',
    'DHD', 'MkvCage', 'RARBGx', 'RGXT', 'TGx', 'SAiNT', 'DpR', 'KaKa',
    'S4KK', 'D-Z0N3', 'PTer', 'BBL', 'BMF', 'FASM', 'SC4R', '4KiNGS',
    'HDX', 'DEFLATE', 'TERMiNAL', 'PTP', 'ROKiT', 'SWTYBLZ', 'HOMELANDER',
    'TombDoc', 'Walter', 'RZEROX'
}

IGNORED_TAGS = {
    'WEB-DL', 'WEBDL', 'WEBRIP', 'WEB', 'BRRIP', 'BLURAY', 'BD', 'BDRIP',
    'DVDRIP', 'DVD', 'HDTV', 'PDTV', 'SDTV', 'REMUX', 'UNTOUCHED',
    'AMZN', 'NF', 'NETFLIX', 'HULU', 'ATVP', 'DSNP', 'MAX', 'CRAV', 'PCOCK',
    'RTE', 'EZTV', 'ETTV', 'HDR', 'HDR10', 'DV', 'DOLBY', 'VISION', 'ATMOS',
    'DTS', 'AAC', 'DDP', 'DDP2', 'DDP5', 'OPUS', 'AC3', '10BIT', 'UHD',
    'PROPER', 'COMPLETE', 'FULL SERIES', 'INT', 'RIP', 'MULTI', 'GB', 'XVID'
}

def parse_media_info(filename, caption=None):
    """
    Intelligently parses and merges media info from both the filename and caption.
    """
    base_name, is_split = get_base_name(filename)

    filename_info = extract_info_from_text(base_name)
    caption_info = extract_info_from_text(caption or "")

    # If filename parsing completely fails, we can't proceed
    if not filename_info or not filename_info.get('type'):
        return None

    # Prioritize caption info if it's valid, otherwise use filename info.
    caption_quality = caption_info.get('quality', 'Unknown') if caption_info else 'Unknown'
    final_quality = caption_quality if caption_quality != 'Unknown' else filename_info.get('quality', 'Unknown')

    caption_codec = caption_info.get('codec', 'Unknown') if caption_info else 'Unknown'
    final_codec = caption_codec if caption_codec != 'Unknown' else filename_info.get('codec', 'Unknown')

    caption_encoder = caption_info.get('encoder', 'Unknown') if caption_info else 'Unknown'
    final_encoder = caption_encoder if caption_encoder != 'Unknown' else filename_info.get('encoder', 'Unknown')


    if filename_info['type'] == 'series':
        return {
            'title': filename_info['title'],
            'season': filename_info['season'],
            'episodes': filename_info.get('episodes', []),
            'quality': final_quality,
            'codec': final_codec,
            'encoder': final_encoder,
            'type': 'series',
            'is_split': is_split,
            'base_name': base_name
        }
    elif filename_info['type'] == 'movie':
        return {
            'title': filename_info['title'],
            'year': filename_info['year'],
            'quality': final_quality,
            'codec': final_codec,
            'encoder': final_encoder,
            'type': 'movie',
            'is_split': is_split,
            'base_name': base_name
        }
    return None

def get_base_name(filename):
    """Identifies split files and returns their base name."""
    match = re.search(r'^(.*)\.(mkv|mp4|avi|mov)\.(\d{3})$', filename, re.IGNORECASE)
    if match:
        return f"{match.group(1)}.{match.group(2)}", True
    return filename, False

def extract_info_from_text(text):
    """A helper function to parse a single string (filename or caption)."""
    if not text:
        return None

    series_pattern = re.compile(
        r'(.+?)[ ._\[\(-][sS](\d{1,2})[ ._]?[eE](\d{1,3})(?:-[eE]?(\d{1,3}))?',
        re.IGNORECASE
    )
    movie_pattern = re.compile(r'(.+?)[ ._\[\(](\d{4})[ ._\]\)]', re.IGNORECASE)

    series_match = series_pattern.search(text)
    movie_match = movie_pattern.search(text)

    # Heuristic: If it has a season/episode marker, it's a series.
    if series_match:
        title_part, season_str, start_ep_str, end_ep_str = series_match.groups()
        title = re.sub(r'[\._]', ' ', title_part).strip().title()
        season = int(season_str)
        start_ep = int(start_ep_str)
        episodes = list(range(start_ep, int(end_ep_str) + 1)) if end_ep_str else [start_ep]
        return {
            'title': title, 'season': season, 'episodes': episodes,
            'quality': get_quality(text), 'codec': get_codec(text),
            'encoder': get_encoder(text), 'type': 'series'
        }

    # If no series match, check for a movie match.
    if movie_match:
        title, year = movie_match.groups()
        return {
            'title': title.replace('.', ' ').strip().title(),
            'year': int(year), 'quality': get_quality(text),
            'codec': get_codec(text), 'encoder': get_encoder(text),
            'type': 'movie'
        }

    return None

def get_quality(text):
    match = re.search(r'\b(4K|2160p|1080p|720p|576p|540p|480p)\b', text, re.IGNORECASE)
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
    """Smarter encoder detection that properly splits tags."""
    # Split the text by common delimiters to get individual tags
    potential_tags = re.split(r'[ ._\[\]()\-]+', text)
    
    found_encoder = 'Unknown'
    # Iterate from the end of the filename backwards
    for tag in reversed(potential_tags):
        if not tag:  # Skip empty strings that can result from splitting
            continue
            
        tag_upper = tag.upper()
        
        # If it's a known encoder, we're done.
        if tag_upper in KNOWN_ENCODERS:
            return tag_upper
            
        # Otherwise, check if it's a potential encoder (and not an ignored tag)
        if tag_upper not in IGNORED_TAGS and not tag_upper.isdigit():
            if any(c.isalpha() for c in tag_upper):
                # Don't overwrite a potential encoder with parts of the series title
                # A simple heuristic: if it contains season/episode markers, stop.
                if re.search(r'S\d{1,2}E\d{1,3}', tag_upper):
                    break
                found_encoder = tag_upper
                
    return found_encoder
