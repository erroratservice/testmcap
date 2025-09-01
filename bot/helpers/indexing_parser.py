"""
Advanced parser for media filenames and captions with expanded format support.
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
    Intelligently parses media info by isolating the title first.
    """
    if caption and ('.mkv' in caption.split('\n')[0] or '.mp4' in caption.split('\n')[0]):
        text_to_parse = caption.split('\n')[0]
    else:
        text_to_parse = filename

    base_name, is_split = get_base_name(text_to_parse)
    
    # --- MODIFIED: Use a more robust extraction function ---
    info = extract_structural_info(base_name)
    if not info:
        return None

    # Extract metadata from the full string
    combined_metadata_text = f"{base_name} {caption or ''}"
    info['quality'] = get_quality(combined_metadata_text)
    info['codec'] = get_codec(combined_metadata_text)
    info['encoder'] = get_encoder(combined_metadata_text)
    
    info['is_split'] = is_split
    info['base_name'] = base_name
    
    return info

def extract_structural_info(text):
    """Extracts Title, Season, and Episode(s) using multiple patterns."""
    
    # --- MODIFIED: Added new patterns ---
    patterns = [
        # S01E01, S01E01-E05
        re.compile(r'(.+?)[ ._\[\(-][sS](\d{1,2})[ ._]?[eE](\d{1,3})(?:-[eE]?(\d{1,3}))?', re.IGNORECASE),
        # 1x01, 2x05
        re.compile(r'(.+?)[ ._\[\(](\d{1,2})[xX](\d{1,3})', re.IGNORECASE),
    ]

    for pattern in patterns:
        match = pattern.search(text)
        if match:
            groups = match.groups()
            title = re.sub(r'[\._]', ' ', groups[0]).strip().title()
            season = int(groups[1])
            start_ep = int(groups[2])
            end_ep = int(groups[3]) if len(groups) > 3 and groups[3] else None
            episodes = list(range(start_ep, end_ep + 1)) if end_ep else [start_ep]
            return {'title': title, 'season': season, 'episodes': episodes, 'type': 'series'}

    # Fallback for episode-only formats
    ep_only_patterns = [
        re.compile(r'(.+?)[ ._][eE](\d{1,3})', re.IGNORECASE),
        re.compile(r'(.+?)[ ._]Episode[ ._](\d{1,3})', re.IGNORECASE),
    ]

    for pattern in ep_only_patterns:
        match = pattern.search(text)
        if match:
            title_part, episode_str = match.groups()
            title = re.sub(r'[\._]', ' ', title_part).strip().title()
            episode = int(episode_str)
            
            # Try to find a season number in the title, otherwise default to 1
            season_match = re.search(r'\b[sS]eason[ ._](\d{1,2})\b|\b[sS](\d{1,2})\b', title, re.IGNORECASE)
            season = int(season_match.group(1) or season_match.group(2)) if season_match else 1
            
            # Clean season info from title if found
            if season_match:
                title = re.sub(r'\b[sS]eason[ ._]\d{1,2}\b|\b[sS]\d{1,2}\b', '', title, flags=re.IGNORECASE).strip()

            return {'title': title, 'season': season, 'episodes': [episode], 'type': 'series'}
            
    return None


def get_base_name(filename):
    """Identifies split files and returns their base name."""
    match = re.search(r'^(.*)\.(mkv|mp4|avi|mov)\.(\d{3})$', filename, re.IGNORECASE)
    if match:
        return f"{match.group(1)}.{match.group(2)}", True
    return filename, False

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
    """Finds an encoder only if it's in the known list."""
    for word in re.split(r'[\s\._\-]', text):
        if word.upper() in KNOWN_ENCODERS:
            return word.upper()
    return 'Unknown'
