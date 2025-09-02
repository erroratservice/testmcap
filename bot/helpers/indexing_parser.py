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
    Intelligently parses media info from the filename and enriches it with TVMaze data.
    """
    base_name, is_split = get_base_name(filename)
    filename_info = extract_info_from_text(base_name)

    if not filename_info:
        return None

    final_info = filename_info.copy()
    episode_title_for_cleaning = None

    # TVMaze API Integration
    if 'title' in final_info:
        show_data = tvmaze_api.search_show(final_info['title'])
        if show_data:
            maze_id = show_data.get('maze_id')
            final_info['title'] = show_data.get('name', final_info['title'])
            if not final_info.get('year') and show_data.get('premiered'):
                final_info['year'] = int(show_data['premiered'][:4])

            # If it's a series, fetch episode title for cleaning purposes
            if final_info.get('type') == 'series' and maze_id:
                episodes = tvmaze_api.get_episodes(maze_id)
                if episodes:
                    for episode_info in episodes:
                        if (episode_info.get('season_number') == final_info.get('season') and
                            episode_info.get('episode_number') in final_info.get('episodes', [])):
                            episode_title_for_cleaning = episode_info.get('title')
                            if len(final_info.get('episodes', [])) == 1:
                                break
    
    # Encoder detection after potentially removing episode title
    remaining_text_for_encoder = base_name
    if episode_title_for_cleaning:
        # Remove the episode title from the filename to avoid misidentifying encoders
        # Use regex for case-insensitive replacement
        remaining_text_for_encoder = re.sub(re.escape(episode_title_for_cleaning), '', remaining_text_for_encoder, flags=re.IGNORECASE)

    final_info['encoder'] = get_encoder(remaining_text_for_encoder)
    
    # Add other details from caption if available
    caption_info = extract_info_from_text(caption or "")
    if caption_info:
        final_info['quality'] = caption_info.get('quality', final_info.get('quality', 'Unknown'))
        final_info['codec'] = caption_info.get('codec', final_info.get('codec', 'Unknown'))
        # Prioritize encoder from filename unless it's unknown
        if final_info['encoder'] == 'Unknown':
            final_info['encoder'] = caption_info.get('encoder', 'Unknown')


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

    if series_match:
        title_part, season_str, start_ep_str, end_ep_str = series_match.groups()
        title = re.sub(r'[\._]', ' ', title_part).strip().title()
        season = int(season_str)
        start_ep = int(start_ep_str)
        episodes = list(range(start_ep, int(end_ep_str) + 1)) if end_ep_str else [start_ep]
        return {'title': title, 'season': season, 'episodes': episodes, 'quality': quality, 'codec': codec, 'type': 'series'}

    if movie_match:
        title, year = movie_match.groups()
        return {'title': title.replace('.', ' ').strip().title(), 'year': int(year), 'quality': quality, 'codec': codec, 'type': 'movie'}
    
    if any(val != 'Unknown' for val in [quality, codec]):
        return {'quality': quality, 'codec': codec}

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
        # Ensure the tag is not purely numeric to avoid matching years etc.
        if tag_upper in KNOWN_ENCODERS and not tag_upper.isdigit():
            return tag_upper
            
    return 'Unknown'
