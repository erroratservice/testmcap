"""
Formatting helpers to generate the text for index posts with a clean, professional format.
"""
from datetime import datetime

def format_series_post(title, data, total_episodes_map):
    """Formats the final text for a TV series post."""
    text = f"**{title}**\n"
    text += f"Status: {'Complete' if data.get('is_complete', False) else 'Incomplete'} Collection\n"
    text += f"Last Updated: {datetime.now().strftime('%b %d, %Y %I:%M %p IST')}\n\n"
    
    if 'seasons' in data:
        for season_num_str in sorted(data['seasons'].keys(), key=int):
            season_num = int(season_num_str)
            season_data = data['seasons'][season_num_str]
            expected_eps = total_episodes_map.get(title, {}).get(season_num, len(season_data.get('episodes', [])))
            
            text += f"**Season {season_num}** ({expected_eps} Episodes)\n"
            
            qualities = season_data.get('qualities', {})
            for i, (quality_key, quality_data) in enumerate(qualities.items()):
                prefix = "└─" if i == len(qualities) - 1 else "├─"
                
                ep_list = sorted(quality_data.get('episodes', []))
                ep_range = get_episode_range(ep_list)
                
                size_gb = quality_data.get('size', 0) / (1024**3)
                
                quality_parts = quality_key.split()
                quality_val = quality_parts[0]
                codec_val = quality_parts[1]
                encoder_val = quality_parts[2].strip('()') if len(quality_parts) > 2 else 'Unknown'

                quality_line = f"**{quality_val} {codec_val}**"
                if encoder_val != 'Unknown':
                    quality_line += f" ({encoder_val})"

                text += f"{prefix} {quality_line}: {ep_range} ({size_gb:.1f}GB)\n"
    
    return text

def get_episode_range(episodes):
    """Converts a list of episode numbers into a compact range string."""
    if not episodes: return "No episodes found"
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
