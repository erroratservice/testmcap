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

def _get_canonical_title(title):
    """Creates a normalized title for consistent grouping."""
    # Remove year in parentheses, e.g., (2020)
    title = re.sub(r'\s*\(\d{4}\)\s*', '', title)
    # Remove trailing hyphens or spaces
    return title.strip().rstrip('-').strip()

def parse_media_info(filename, caption=None):
    """
    Intelligently parses media info and enriches it with TVMaze data.
    """
    base_name, is_split = get_base_name(filename)
    
    # --- Step 1: Initial Parsing ---
    filename_info = extract_info_from_text(base_name)
    caption_info = extract_info_from_text(caption or "")

    if not filename_info:
        return None

    final_info = filename_info.copy()
    
    # --- Step 2: Merge Quality and Codec ---
    final_info['quality'] = caption_info.get('quality', final_info.get('quality', 'Unknown'))
    final_info['codec'] = caption_info.get('codec', final_info.get('codec', 'Unknown'))

    # --- Step 3: TVMaze Enrichment and Cleaning ---
    episode_title_for_cleaning = None
    show_title_for_cleaning = set()

    if 'title' in final_info:
        show_data = tvmaze_api.get_minimal_info(final_info['title'])
        if show_data:
            official_title = show_data.get('name', final_info['title'])
            final_info['title'] = official_title
            
            # Create a set of words from the official title to remove later
            show_title_for_cleaning = set(re.split(r'[\s._-]+', official_title.upper()))

            if not final_info.get('year') and show_data.get('premiered'):
                final_info['year'] = int(show_data['premiered'][:4])

            if final_info.get('type') == 'series' and 'episodes' in show_data:
                for episode_info in show_data['episodes']:
                    if (episode_info.get('season_number') == final_info.get('season') and
                        episode_info.get('episode_number') in final_info.get('episodes', [])):
                        episode_title_for_cleaning = episode_info.get('title')
                        break
    
    # --- Step 4: Robust Encoder Detection ---
    text_for_encoder = base_name
    # Remove the episode title from the text
    if episode_title_for_cleaning:
        safe_pattern = re.escape(episode_title_for_cleaning)
        text_for_encoder = re.sub(safe_pattern, '', text_for_encoder, flags=re.IGNORECASE)
    
    # Get encoder from the cleaned filename first
    filename_encoder = get_encoder(text_for_encoder, show_title_for_cleaning)
    caption_encoder = caption_info.get('encoder', 'Unknown')
    
    # Prioritize the filename's encoder. Use caption's only if filename's is unknown.
    final_info['encoder'] = filename_encoder if filename_encoder != 'Unknown' else caption_encoder

    # --- Step 5: Finalize and Add Canonical Title ---
    if 'title' in final_info:
        final_info['canonical_title'] = _get_canonical_title(final_info['title'])
    
    final_info['is_split'] = is_split
    final_info['base_name'] = base_name

    return final_info

def get_base_name(filename):
    match = re.search(r'^(.*)\.(mkv|mp4|avi|mov)\.(\d{3})$', filename, re.IGNORECASE)
    if match:
        return f"{match.group(1)}.{match.group(2)}", True
    return filename, False

def extract_info_from_text(text):
    if not text:
        return None

    series_pattern = re.compile(r'(.+?)[ ._\[\(-][sS](\d{1,2})[ ._]?[eE](\d{1,3})(?:-[eE]?(\d{1,3}))?', re.IGNORECASE)
    movie_pattern = re.compile(r'(.+?)[ ._\[\(](\d{4})[ ._\]\)]', re.IGNORECASE)

    series_match = series_pattern.search(text)
    movie_match = movie_pattern.search(text)
    
    quality = get_quality(text)
    codec = get_codec(text)
    encoder = get_encoder(text) # Initial pass

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

def get_encoder(text, words_to_exclude=None):
    if words_to_exclude is None:
        words_to_exclude = set()

    text_without_ext = re.sub(r'\.\w+$', '', text)
    potential_tags = re.split(r'[ ._\[\]()\-]+', text_without_ext)
    
    for tag in reversed(potential_tags):
        if not tag: continue
        tag_upper = tag.upper()
        # CRITICAL FIX: Do not identify a word as an encoder if it's part of the show's title
        if tag_upper in KNOWN_ENCODERS and tag_upper not in words_to_exclude:
            return tag_upper
            
    return 'Unknown'
