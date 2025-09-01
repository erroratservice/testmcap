"""
Formatting helpers to generate the text for index posts.
"""
from datetime import datetime
from collections import defaultdict
import logging

LOGGER = logging.getLogger(__name__)

def format_series_post(title, data, total_episodes_map):
    text = f"**{title}**\n\n"
    if 'seasons' in data:
        for season_num_str in sorted(data['seasons'].keys(), key=int):
            season_num = int(season_num_str)
            season_data = data['seasons'][season_num_str]
            expected_eps = total_episodes_map.get(title, {}).get(season_num, len(season_data.get('episodes', [])))
            text += f"**Season {season_num}** ({expected_eps} Episodes)\n"
            qualities = season_data.get('qualities', {})
            for i, (quality_key, quality_data) in enumerate(qualities.items()):
                prefix = "└─" if i == len(qualities) - 1 else "├─"
                episodes_by_encoder = quality_data.get('episodes_by_encoder', {})
                if not episodes_by_encoder: continue
                details_parts = []
                known_encoder_names = [enc for enc in episodes_by_encoder.keys() if enc != 'Unknown']
                known_encoder_names.sort()
                for encoder in known_encoder_names:
                    ep_range = get_episode_range(sorted(episodes_by_encoder[encoder]))
                    if ep_range: details_parts.append(f"({encoder}): {ep_range}")
                if 'Unknown' in episodes_by_encoder:
                    ep_range = get_episode_range(sorted(episodes_by_encoder['Unknown']))
                    if ep_range: details_parts.append(ep_range)
                if not details_parts: continue
                full_details_line = " | ".join(details_parts)
                text += f"{prefix} **{quality_key}** {full_details_line}\n"
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
