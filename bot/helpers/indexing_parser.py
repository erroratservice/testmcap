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
    'TombDoc', 'Walter', 'RZEROX',
    'V3SP4EV3R'
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

    # Step 1: Get all possible info from the filename.
    filename_info = extract_info_from_text(base_name)
    
    # If the filename itself is unparsable for basic info (title, type), we can't continue.
    if not filename_info:
        return None

    # Step 2: Get all possible info from the caption.
    caption_info = extract_info_from_text(caption or "")

    # Step 3: Intelligently merge the results.
    
    # The filename is the source of truth for title, season, episodes, and year.
    final_info = filename_info.copy()
    
    # For quality and codec, prioritize caption info if it's valid, otherwise use filename info.
    filename_quality = filename_info.get('quality', 'Unknown')
    caption_quality = caption_info.get('quality', 'Unknown') if caption_info else 'Unknown'
    final_info['quality'] = caption_quality if caption_quality != 'Unknown' else filename_quality

    filename_codec = filename_info.get('codec', 'Unknown')
    caption_codec = caption_info.get('codec', 'Unknown') if caption_info else 'Unknown'
    final_info['codec'] = caption_codec if caption_codec != 'Unknown' else filename_codec
    
    # Encoder information is most reliable from the filename.
    final_info['encoder'] = filename_info.get('encoder', 'Unknown')

    # Add back metadata about the file itself.
    final_info['is_split'] = is_split
    final_info['base_name'] = base_name
    
    return final_info


def get_base_name(filename):
    """Identifies split files and returns their base name."""
    match = re.search(r'^(.*)\.(mkv|mp4|avi|mov)\.(\d{3})$', filename, re.IGNORECASE)
    if match:
        return f"{match.group(1)}.{match.group(2)}", True
    return filename, False

def extract_info_from_text(text):
    """A comprehensive helper to parse a string (filename or caption) for all media info."""
    if not text:
        return None

    series_pattern = re.compile(
        r'(.+?)[ ._\[\(-][sS](\d{1,2})[ ._]?[eE](\d{1,3})(?:-[eE]?(\d{1,3}))?',
        re.IGNORECASE
    )
    movie_pattern = re.compile(r'(.+?)[ ._\[\(](\d{4})[ ._\]\)]', re.IGNORECASE)

    series_match = series_pattern.search(text)
    movie_match = movie_pattern.search(text)
    
    quality = get_quality(text)
    codec = get_codec(text)
    encoder = get_encoder(text)

    # Heuristic: If it has a season/episode marker, it's a series.
    if series_match:
        title_part, season_str, start_ep_str, end_ep_str = series_match.groups()
        title = re.sub(r'[\._]', ' ', title_part).strip().title()
        season = int(season_str)
        start_ep = int(start_ep_str)
        episodes = list(range(start_ep, int(end_ep_str) + 1)) if end_ep_str else [start_ep]
        return {
            'title': title, 'season': season, 'episodes': episodes,
            'quality': quality, 'codec': codec,
            'encoder': encoder, 'type': 'series'
        }

    # If no series match, check for a movie match.
    if movie_match:
        title, year = movie_match.groups()
        return {
            'title': title.replace('.', ' ').strip().title(),
            'year': int(year), 'quality': quality,
            'codec': codec, 'encoder': encoder,
            'type': 'movie'
        }
    
    # Fallback for captions that might only contain quality/codec info
    if quality != 'Unknown' or codec != 'Unknown':
        return {'quality': quality, 'codec': codec}

    return None

def get_quality(text):
    # This regex now also handles the simple "Video: ... 404p" format from captions
    match = re.search(r'\b(4K|2160p|1080p|720p|576p|540p|480p|404p)\b', text, re.IGNORECASE)
    if match:
        quality = match.group(1).upper()
        return "4K" if "2160" in quality else quality
    return 'Unknown'

def get_codec(text):
    # This regex now also handles the simple "Video: H264" format from captions
    if re.search(r'\b(AV1)\b', text, re.IGNORECASE): return 'AV1'
    if re.search(r'\b(VP9)\b', text, re.IGNORECASE): return 'VP9'
    if re.search(r'\b(HEVC|x265|H\s*265)\b', text, re.IGNORECASE): return 'X265'
    if re.search(r'\b(AVC|x264|H\s*264)\b', text, re.IGNORECASE): return 'X264'
    return 'Unknown'

def get_encoder(text):
    """Strict encoder detection that only returns known encoders."""
    potential_tags = re.split(r'[ ._\[\]()\-]+', text)
    
    for tag in reversed(potential_tags):
        if not tag:
            continue
            
        tag_upper = tag.upper()
        
        if tag_upper in KNOWN_ENCODERS:
            return tag_upper
            
    return 'Unknown'
