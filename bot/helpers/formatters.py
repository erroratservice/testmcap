"""
Formatting helpers to generate a clean, minimalist index post.
"""
from datetime import datetime

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
                
                ep_list = sorted(quality_data.get('episodes', []))
                ep_range = get_episode_range(ep_list)
                
                quality_parts = quality_key.split()
                quality_line = f"**{quality_parts[0]} {quality_parts[1]}**"
                if len(quality_parts) > 2 and quality_parts[2] != '(Unknown)':
                    quality_line += f" {quality_parts[2]}"

                text += f"{prefix} {quality_line}: {ep_range}\n"
    
    text += f"\nLast Updated: {datetime.now().strftime('%b %d, %Y %I:%M %p IST')}"
    
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
