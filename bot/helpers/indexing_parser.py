"""
Advanced parser for media filenames and captions with improved movie/series detection.
"""
import re
import logging
from bot.helpers.tvmaze_utils import tvmaze_api

LOGGER = logging.getLogger(__name__)

KNOWN_ENCODERS = {
    'GHOST', 'AMBER', 'ELITE', 'BONE', 'CELDRA', 'MEGUSTA', 'EDGE2020', 'SIX',
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
    
    filename_info = extract_info_from_text(base_name)
    
    if not filename_info:
        return None

    caption_info = extract_info_from_text(caption or "")
    
    final_info = filename_info.copy()
    
    filename_quality = filename_info.get('quality', 'Unknown')
    caption_quality = caption_info.get('quality', 'Unknown') if caption_info else 'Unknown'
    final_info['quality'] = caption_quality if caption_quality != 'Unknown' else filename_quality

    filename_codec = filename_info.get('codec', 'Unknown')
    caption_codec = caption_info.get('codec', 'Unknown') if caption_info else 'Unknown'
    final_info['codec'] = caption_codec if caption_codec != 'Unknown' else filename_codec
    
    filename_encoder = filename_info.get('encoder', 'Unknown')
    caption_encoder = caption_info.get('encoder', 'Unknown') if caption_info else 'Unknown'
    final_info['encoder'] = caption_encoder if caption_encoder != 'Unknown' else filename_encoder

    # TVMaze API Integration
    if 'title' in final_info:
        show_data = tvmaze_api.search_show(final_info['title'])
        if show_data:
            final_info['title'] = show_data.get('name')
            if not final_info.get('year') and show_data.get('premiered'):
                final_info['year'] = int(show_data['premiered'][:4])
            
            # Refine encoder detection by removing words from the title
            title_words = set(final_info['title'].upper().split())
            if final_info['encoder'] in title_words:
                final_info['encoder'] = 'Unknown'

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

    series_pattern = re.compile(r'(.+?)[ ._\[\(-][sS](\d{1,2})[ ._]?[eE](\d{1,3})(?:-[eE]?(\d{1,3}))?', re.IGNORECASE)
    movie_pattern = re.compile(r'(.+?)[ ._\[\(](\d{4})[ ._\]\)]', re.IGNORECASE)

    series_match = series_pattern.search(text)
    movie_match = movie_pattern.search(text)
    
    quality = get_quality(text)
    codec = get_codec(text)
    encoder = get_encoder(text)

    if series_match:
        title_part, season_str, start_ep_str, end_ep_str = series_match.groups()
        title = re.sub(r'[\._]', ' ', title_part).strip().title()
        season = int(season_str)
        start_ep = int(start_ep_str)
        episodes = list(range(start_ep, int(end_ep_str) + 1)) if end_ep_str else [start_ep]
        return {'title': title, 'season': season, 'episodes': episodes, 'quality': quality, 'codec': codec, 'encoder': encoder, 'type': 'series'}

    if movie_match:
        title, year = movie_match.groups()
        return {'title': title.replace('.', ' ').strip().title(), 'year': int(year), 'quality': quality, 'codec': codec, 'encoder': encoder, 'type': 'movie'}
    
    if any(val != 'Unknown' for val in [quality, codec, encoder]):
        return {'quality': quality, 'codec': codec, 'encoder': encoder}

    return None

def get_quality(text):
    match = re.search(r'\b(4K|2160p|1080p|960p|720p|576p|540p|480p|404p)\b', text, re.IGNORECASE)
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
    """A more robust encoder detection method that is strictly based on the known list."""
    text_without_ext = re.sub(r'\.\w+$', '', text)
    potential_tags = re.split(r'[ ._\[\]()\-]+', text_without_ext)
    
    for tag in reversed(potential_tags):
        if not tag: continue
        tag_upper = tag.upper()
        if tag_upper in KNOWN_ENCODERS:
            return tag_upper
            
    return 'Unknown'
