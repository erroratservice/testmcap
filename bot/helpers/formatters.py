"""
Formatting helpers to generate the text for index posts.
"""
from datetime import datetime

def format_series_post(title, data, total_episodes_map):
    """Formats the final text for a TV series post."""
    text = f"🎬 **{title}**\n"
    text += f"📊 **Status**: {'Complete' if data['is_complete'] else 'Incomplete'} Collection\n"
    text += f"🔄 **Last Updated**: {datetime.now().strftime('%b %d, %Y %I:%M %p IST')}\n\n"
    
    total_found = 0
    total_expected = 0

    for season_num in sorted(data['seasons'].keys()):
        season_data = data['seasons'][season_num]
        expected_eps = total_episodes_map.get(title, {}).get(season_num, len(season_data['episodes']))
        total_expected += expected_eps
        
        text += f"**Season {season_num}** ({expected_eps} Episodes)\n"
        
        for i, (quality_key, quality_data) in enumerate(season_data['qualities'].items()):
            prefix = "└─" if i == len(season_data['qualities']) - 1 else "├─"
            
            ep_list = sorted(quality_data['episodes'])
            total_found += len(ep_list)
            
            ep_range = get_episode_range(ep_list)
            is_season_complete = len(ep_list) == expected_eps
            status_icon = "✅ Complete" if is_season_complete else f"⚠️ Missing: {get_missing_episodes(ep_list, expected_eps)}"
            
            size_gb = quality_data['size'] / (1024**3)
            
            text += f"{prefix} 🎥 **{quality_key}**: {ep_range} {status_icon} ({size_gb:.1f}GB)\n"
    
    text += f"\n📈 **Series Total**: {total_found}/{total_expected} Episodes | {data['total_size'] / (1024**3):.1f}GB\n"
    
    # Add hashtags
    hashtags = f"#{''.join(title.split())} #{'Complete' if data['is_complete'] else 'Incomplete'}"
    text += hashtags
    
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

def get_missing_episodes(episodes, total_expected):
    """Finds missing episode numbers in a sequence."""
    expected = set(range(1, total_expected + 1))
    found = set(episodes)
    missing = sorted(list(expected - found))
    return ', '.join([f"E{m:02d}" for m in missing[:3]]) + ("..." if len(missing) > 3 else "")
