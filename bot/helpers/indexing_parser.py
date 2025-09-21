"""
Advanced parser for media filenames and captions with improved movie/series detection.
"""
import re
import logging
from bot.core.config import Config
from bot.helpers.tvmaze_utils import tvmaze_api

LOGGER = logging.getLogger(__name__)

# --- FIX: Updated Encoder and Ignore Lists ---
KNOWN_ENCODERS = {
    '30NAMA', '4KiNGS', 'AEW', 'AFG', 'AOC', 'AMBER', 'AnimeRG', 'BAE', 'BaoBao',
    'BBL', 'BETA', 'BHDStudio', 'BigJ0554', 'BMF', 'BON', 'BONE', 'BTN', 'budgetbits',
    'CBFM', 'CELDRA', 'CKlicious', 'CMRG', 'CODSWALLOP', 'CRiMSON', 'D-Z0N3', 'D3G',
    'DaddyCooL', 'DARKFLIX', 'dAV1nci', 'DEFLATE', 'DHD', 'DiMEPiECE', 'DiRT',
    'DOLORES', 'DON', 'DpR', 'DRONES', 'DS4K', 'DUST', 'EDITH', 'ELEANOR', 'ELITE',
    'EMBER', 'ETHEL', 'ETRG', 'EVO', 'EzzRips', 'FASM', 'Fenix', 'FGT', 'FLUXXED',
    'FraMeSToR', 'FUM', 'FUSiON', 'G66', 'GalaxyR', 'GalaxyRG', 'GalaxyRG265',
    'GalaxyTV', 'GHOST', 'ggez', 'glhf', 'GOSSIP', 'HANDJOB', 'HashMiner', 'HDX',
    'HEEL', 'HETeam', 'heTOrico', 'HEVCBay', 'HiQVE', 'HOMELANDER', 'HQMUX', 'ImE',
    'INFINITY', 'iON10', 'ION265', 'ivy', 'JFF', 'Joy', 'KaKa', 'KiNGDOM', 'KiNGS',
    'KITSUNE', 'KOGi', 'KOMPOST', 'KONTRAST', 'Me7alh', 'MeGusta', 'MiNX', 'MkvCage',
    'MONOLITH', 'MOSTBET', 'MoviesFD', 'MRN', 'MSD', 'mSD', 'MVGroup', 'NGP',
    'NOVA', 'NoGroup', 'NORDiC', 'NTb', 'NTG', 'NWCHD', 'PAHE', 'Panda', 'PGW',
    'PHOCIS', 'PMTP', 'PRIMEFIX', 'PROTON', 'PSA', 'pseudo', 'PTP', 'PTer', 'PTNX',
    'QOQ', 'QxR', 'RARBG', 'RARBGx', 'RAWR', 'RCVR', 'REALiTYTV', 'RGXT', 'rmteam',
    'r00t', 'ROKiT', 'ROPATA', 'RxB', 'S4KK', 'SAiNT', 'SAON', 'SC4R', 'SDH',
    'Silence', 'SKG', 'skorpion', 'skyanime', 'Skylane77', 'SMILEY', 'SMURF',
    'SPARKS', 'spamneggs', 'STAR', 'STC', 'SWAXX', 'SWAXXON', 'SWTYBLZ', 'SYNCOPY',
    'syncopy', 't3nzin', 'TEPES', 'TERMiNAL', 'TGx', 'TheMoviesBoss', 'Tigole',
    'TIPEX', 'T0M', 'T0PAZ', 'TombDoc', 'TRUFFLE', 'TURG', 'ULTRAS', 'UnAV1Chain',
    'UTR', 'V3SP4EV3R', 'ViruseProject', 'VXT', 'Vyndros', 'vyndros', 'W4NK3R',
    'Walter', 'XoXo', 'XWT', 'y2flix', 'YIFY', 'YSTeam', 'YTS', 'Zero00', 'ZiGZaG',
    'ZMNT', 'ZTR', 'Černá', 'afm72'
}

IGNORED_TAGS = {
    'WEB-DL', 'WEBDL', 'WEBRIP', 'WEB', 'BRRIP', 'BLURAY', 'BD', 'BDRIP',
    'DVDRIP', 'DVD', 'HDTV', 'PDTV', 'SDTV', 'REMUX', 'UNTOUCHED', 'REPACK',
    'AMZN', 'NF', 'NETFLIX', 'HULU', 'ATVP', 'DSNP', 'MAX', 'CRAV', 'PCOCK', 'HMAX',
    'RTE', 'EZTV', 'ETTV', 'HDR', 'HDR10', 'DV', 'DOLBY', 'VISION', 'ATMOS',
    'DTS', 'AAC', 'AAC2', 'AAC5', 'DD5', 'DD+2', 'OPUS2', 'Opus51', 'AC3', 'EAC3', '2CH', '6CH',
    '10BIT', '10Bits', 'UHD', 'PROPER', 'COMPLETE', 'FULL SERIES', 'INT', 'RIP', 'MULTI', 'GB', 'XVID',
    'EXTENDED', 'UNCUT', 'UNRATED', 'REMASTERED', 'UPSCALED', 'Upscale', 'Uncensored',
    'HINDI', 'SPANISH', 'JAPANESE', 'FRENCH', 'GERMAN', 'ITALIAN', 'iTALiAN', 'PORTUGUESE',
    'POLISH', 'TURKISH', 'Tagalog', 'Subs', 'AMZ', 'PCOK', 'ALL4', 'STAN', 'SONY', 'SONYLIV',
    'ZEE5', 'ROKU', 'WEBTUBE', 'SXM', 'HDCAM', 'HDRip', 'Sample',
    # File sizes
    '150MB', '300MB', '350MB', '400MB', '800MB', '900MB', '1400MB', '1600MB', '3500MB', '3999MB',
    # User additions
    'AMZNWebDL', 'DS4K', 'SDR', 'DDP5.1', '[EZTVx.to]'
}


def _get_canonical_title(title):
    """Creates a normalized title for consistent grouping."""
    # FIX: More aggressive cleaning to remove year and special characters
    title = re.sub(r'[\s._-]*\(\d{4}\)[\s._-]*', ' ', title)
    title = re.sub(r'[:()]', '', title)
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
    safe_caption_info = caption_info or {}
    final_info['quality'] = safe_caption_info.get('quality', final_info.get('quality', 'Unknown'))
    final_info['codec'] = safe_caption_info.get('codec', final_info.get('codec', 'Unknown'))

    # --- Step 3: TVMaze Enrichment and Cleaning (Rewritten Logic) ---
    words_to_exclude = set()

    if 'title' in final_info:
        show_data = tvmaze_api.get_minimal_info(final_info['title'])
        if show_data:
            # FIX: Use TVMaze title only if the config allows it
            if Config.USE_TVMAZE_TITLES:
                official_title = show_data.get('name', final_info['title'])
                final_info['title'] = official_title
            else:
                official_title = final_info['title']

            # FIX: Add all words from the official title to an exclusion list
            for word in re.split(r'[\s._-]+', official_title.upper()):
                words_to_exclude.add(word)

            if not final_info.get('year') and show_data.get('premiered'):
                final_info['year'] = int(show_data['premiered'][:4])

            if final_info.get('type') == 'series' and 'episodes' in show_data:
                for episode_info in show_data['episodes']:
                    if (episode_info.get('season_number') == final_info.get('season') and
                        episode_info.get('episode_number') in final_info.get('episodes', [])):
                        episode_title = episode_info.get('title')
                        if episode_title:
                            # Also add all words from the episode title to the exclusion list
                            for word in re.split(r'[\s._-]+', episode_title.upper()):
                                words_to_exclude.add(word)
                        break

    # --- Step 4: Robust Encoder Detection ---
    filename_encoder = get_encoder(base_name, words_to_exclude)
    caption_encoder = safe_caption_info.get('encoder', 'Unknown')
    final_info['encoder'] = filename_encoder if filename_encoder != 'Unknown' else caption_encoder

    # --- Step 5: Finalize and Add Canonical Title ---
    if 'title' in final_info:
        final_info['canonical_title'] = _get_canonical_title(final_info['title'])

    final_info['is_split'] = is_split
    final_info['base_name'] = base_name

    return final_info

def get_base_name(filename):
    # Match format like .mkv.001
    match_ext_first = re.search(r'^(.*)\.(mkv|mp4|avi|mov)\.(\d{3})$', filename, re.IGNORECASE)
    if match_ext_first:
        return f"{match_ext_first.group(1)}.{match_ext_first.group(2)}", True
        
    # Match format like .001.mkv
    match_num_first = re.search(r'^(.*)\.(\d{3})\.(mkv|mp4|avi|mov)$', filename, re.IGNORECASE)
    if match_num_first:
        return f"{match_num_first.group(1)}.{match_num_first.group(3)}", True
        
    # Match format like ...part001.mkv
    match_part_num = re.search(r'^(.*)\.part(\d+)\.(mkv|mp4|avi|mov)$', filename, re.IGNORECASE)
    if match_part_num:
        return f"{match_part_num.group(1)}.{match_part_num.group(3)}", True
        
    return filename, False

def extract_info_from_text(text):
    if not text:
        return None

    # FIX: Remove decorative tags like "Vol. 01" before parsing
    cleaned_text = re.sub(r'[._\s]Vol[\s._]\d+', ' ', text, flags=re.IGNORECASE)

    # FIX: More robust series patterns to handle multiple formats
    patterns = [
        # S01E01, S01.E01, S01-E01
        re.compile(r'(.+?)[ ._\[\(-][sS](\d{1,2})[ ._]?[eE](\d{1,3})(?:-[eE]?(\d{1,3}))?', re.IGNORECASE),
        # EP01 (with season)
        re.compile(r'(.+?)[ ._\[\(-][sS](\d{1,2})[ ._]?EP(\d{1,3})', re.IGNORECASE),
        # EP01 (without season - assumes S01)
        re.compile(r'(.+?)[ ._\[\(]EP(\d{1,3})', re.IGNORECASE)
    ]

    series_match = None
    is_seasonless = False
    for pattern in patterns:
        series_match = pattern.search(cleaned_text)
        if series_match:
            if 'EP' in pattern.pattern and 'sS' not in pattern.pattern:
                is_seasonless = True
            break
            
    movie_pattern = re.compile(r'(.+?)[ ._\[\(](\d{4})[ ._\]\)]', re.IGNORECASE)
    movie_match = movie_pattern.search(cleaned_text)
    
    quality = get_quality(cleaned_text)
    codec = get_codec(cleaned_text)
    encoder = get_encoder(cleaned_text)

    if series_match:
        if is_seasonless:
            title_part, start_ep_str = series_match.groups()
            season_str = "1" # Assume Season 1
            end_ep_str = None
        elif 'EP' in series_match.re.pattern:
            title_part, season_str, start_ep_str = series_match.groups()
            end_ep_str = None
        else:
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
    # FIX: More flexible regex for H.265/x265
    if re.search(r'\b(HEVC|x265|H[\s._]?265)\b', text, re.IGNORECASE): return 'X265'
    if re.search(r'\b(AVC|x264|H[\s._]?264)\b', text, re.IGNORECASE): return 'X264'
    return 'Unknown'

def get_encoder(text, words_to_exclude=None):
    if words_to_exclude is None:
        words_to_exclude = set()

    text_without_ext = re.sub(r'\.\w+$', '', text)
    potential_tags = re.split(r'[ ._\[\]()\-]+', text_without_ext)
    
    for tag in reversed(potential_tags):
        if not tag: continue
        tag_upper = tag.upper()
        # CRITICAL FIX: Do not identify a word as an encoder if it's part of the show/episode title
        if tag_upper in KNOWN_ENCODERS and tag_upper not in words_to_exclude:
            return tag_upper
            
    return 'Unknown'
