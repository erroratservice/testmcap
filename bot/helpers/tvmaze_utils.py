"""
TVMaze API integration for fetching series and movie data with caching.
"""

import logging
from pytvmaze.tvmaze import TVMaze as PyTVMaze, ShowNotFound
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

def _get_minimal_show_data(show_obj):
    """
    Safely converts a pytvmaze show object into the minimal dictionary we need.
    This is not recursive and explicitly extracts fields to avoid errors.
    """
    if not show_obj:
        return None
    
    # Safely determine the show type
    show_type = 'series' if getattr(show_obj, 'type', '') == 'Scripted' else 'movie'
    
    # Safely extract episode details into a clean list of dicts
    episodes = []
    if hasattr(show_obj, 'episodes'):
        for ep in show_obj.episodes:
            episodes.append({
                'season_number': getattr(ep, 'season_number', None),
                'episode_number': getattr(ep, 'episode_number', None),
                'title': getattr(ep, 'title', 'Unknown')
            })
            
    # Build the final, clean dictionary
    minimal_data = {
        'maze_id': getattr(show_obj, 'maze_id', None),
        'name': getattr(show_obj, 'name', 'Unknown'),
        'type': show_type,
        'premiered': getattr(show_obj, 'premiered', None),
        'episodes': episodes
    }
    return minimal_data

class TVMaze:
    """A helper class for interacting with the TVMaze API with MongoDB caching."""

    def __init__(self):
        self.api = PyTVMaze()

    def get_minimal_info(self, title):
        """
        Fetches minimal show info (type and episodes) for a given title, using a cache.
        """
        cached_result = MongoDB.get_tvmaze_cache(title)
        if cached_result:
            LOGGER.info(f"Found '{title}' in TVMaze cache.")
            return cached_result.get('data')

        LOGGER.info(f"'{title}' not in cache. Querying TVMaze API.")
        try:
            show = self.api.get_show(show_name=title, embed='episodes')
            if show:
                # Use the new safe function to get a clean dictionary
                minimal_data = _get_minimal_show_data(show)
                if minimal_data:
                    MongoDB.set_tvmaze_cache(title, minimal_data)
                return minimal_data
        except ShowNotFound:
            LOGGER.warning(f"Show '{title}' not found on TVMaze.")
        except Exception as e:
            # Log the full traceback for better debugging
            LOGGER.error(f"TVMaze API error while searching for '{title}': {e}", exc_info=True)

        return None

# Initialize a single instance to be used across the application
tvmaze_api = TVMaze()
