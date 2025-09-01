"""
Formatting helpers to generate the text for index posts.
"""
from datetime import datetime
from collections import defaultdict

def format_series_post(title, data, total_episodes_map):
    """Formats the final text for a TV series post with a clean, minimalist style."""
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
                if not episodes_by_encoder:
                    continue

                all_details = []
                
                # Process known encoders first, sorted alphabetically
                known_encoders = {enc: eps for enc, eps in episodes_by_encoder.items() if enc != 'Unknown'}
                for encoder, ep_list in sorted(known_encoders.items()):
                    ep_range = get_episode_range(sorted(ep_list))
                    if ep_range:
                        all_details.append(f"({encoder}): {ep_range}")

                # Process the 'Unknown' encoder group if it exists, adding it to the end
                if 'Unknown' in episodes_by_encoder:
                    ep_list = episodes_by_encoder['Unknown']
                    ep_range = get_episode_range(sorted(ep_list))
                    if ep_range:
                        all_details.append(ep_range)

                if not all_details:
                    continue
                    
                full_details_line = " | ".join(all_details)
                text += f"{prefix} **{quality_key}**: {full_details_line}\n"
    
    text += f"\nLast Updated: {datetime.now().strftime('%b %d, %Y %I:%M %p IST')}"
    
    return text

def format_movie_post(title, data):
    """Formats the final text for a single movie post, listing all available versions."""
    text = f"**{title}**\n\n"
    
    if 'versions' in data:
        for i, version_data in enumerate(data['versions']):
            prefix = "└─" if i == len(data['versions']) - 1 else "├─"
            
            quality_line = f"**{version_data['quality']} {version_data['codec']}**"
            if version_data['encoder'] != 'Unknown':
                quality_line += f" ({version_data['encoder']})"
            
            size_gb = version_data.get('size', 0) / (1024**3)
            
            text += f"{prefix} {quality_line} ({size_gb:.1f}GB)\n"

    text += f"\nLast Updated: {datetime.now().strftime('%b %d, %Y %I:%M %p IST')}"
    return text

def get_episode_range(episodes):
    """Converts a list of episode numbers into a compact range string."""
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
