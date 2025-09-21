"""
Formatting helpers to generate the text for index posts.
"""
from datetime import datetime
from collections import defaultdict
import logging

LOGGER = logging.getLogger(__name__)

def format_season_post(title, season_num, season_data, total_episodes_map):
    """Formats the text for a single season post."""
    expected_eps = total_episodes_map.get(title, {}).get(season_num, len(season_data.get('episodes', [])))
    text = f"**{title} - Season {season_num}** ({expected_eps} Episodes)\n\n"
    
    qualities = season_data.get('qualities', {})
    sorted_qualities = sorted(qualities.keys())

    for i, quality_key in enumerate(sorted_qualities):
        quality_data = qualities[quality_key]
        episodes_by_encoder = quality_data.get('episodes_by_encoder', {})
        if not episodes_by_encoder: continue
        
        # Sort encoders, putting 'Unknown' last
        sorted_encoders = sorted([enc for enc in episodes_by_encoder.keys() if enc != 'Unknown'])
        if 'Unknown' in episodes_by_encoder:
            sorted_encoders.append('Unknown')

        for j, encoder in enumerate(sorted_encoders):
            # Determine the prefix for the line
            is_last_quality = (i == len(sorted_qualities) - 1)
            is_last_encoder = (j == len(sorted_encoders) - 1)
            prefix = "└─" if is_last_quality and is_last_encoder else "├─"
            
            ep_range = get_episode_range(sorted(episodes_by_encoder[encoder]))
            
            if encoder == 'Unknown':
                details_line = f"**{quality_key}**: {ep_range}\n"
            else:
                details_line = f"**{quality_key}** ({encoder}): {ep_range}\n"

            text += f"{prefix} {details_line}"

    text += f"\nLast Updated: {datetime.now().strftime('%b %d, %Y %I:%M %p IST')}"
    return text


def format_movie_post(title, data):
    text = f"**{title}**\n\n"
    if 'versions' in data:
        for i, version_data in enumerate(data['versions']):
            prefix = "└─" if i == len(data['versions']) - 1 else "├─"
            quality_line = f"**{version_data['quality']} {version_data['codec']}**"
            if version_data['encoder'] != 'Unknown': quality_line += f" ({version_data['encoder']})"
            size_gb = version_data.get('size', 0) / (1024**3)
            text += f"{prefix} {quality_line} ({size_gb:.1f}GB)\n"
    text += f"\nLast Updated: {datetime.now().strftime('%b %d, %Y %I:%M %p IST')}"
    return text

def get_episode_range(episodes):
    if not episodes: return ""
    episodes = sorted(list(set(episodes)))
    ranges = []
    start = end = episodes[0]
    for ep in episodes[1:]:
        if ep == end + 1:
            end = ep
        else:
            ranges.append(f"E{start:02d}" if start == end else f"E{start:02d}-E{end:02d}")
            start = end = ep
    ranges.append(f"E{start:02d}" if start == end else f"E{start:02d}-E{end:02d}")
    return ', '.join(ranges)
