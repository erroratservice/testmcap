"""
TVMaze API integration for fetching series and movie data with caching.
"""

import logging
from pytvmaze.tvmaze import TVMaze as PyTVMaze, ShowNotFound
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

def _to_dict(obj):
    """
    Recursively convert pytvmaze objects to dictionaries.
    This makes the data safe to store in MongoDB and prevents encoding errors.
    """
    if hasattr(obj, '__dict__'):
        # Convert object to dictionary
        data = vars(obj)
        # Recursively process all items in the dictionary
        return {key: _to_dict(value) for key, value in data.items()}
    elif isinstance(obj, list):
        # If it's a list, process each item in the list
        return [_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        # If it's already a dict, process its values
        return {key: _to_dict(value) for key, value in obj.items()}
    else:
        # Return the value if it's a primitive type (string, int, etc.)
        return obj

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
                # Convert the show object and all its nested objects to a clean dictionary
                show_data = _to_dict(show)
                
                # Extract only the data we absolutely need to store
                minimal_data = {
                    'maze_id': show_data.get('maze_id'),
                    'name': show_data.get('name'),
                    'type': 'series' if show_data.get('type') == 'Scripted' else 'movie',
                    'premiered': show_data.get('premiered'),
                    'episodes': show_data.get('_Show__episodes', [])
                }
                
                MongoDB.set_tvmaze_cache(title, minimal_data)
                return minimal_data
        except ShowNotFound:
            LOGGER.warning(f"Show '{title}' not found on TVMaze.")
        except Exception as e:
            LOGGER.error(f"TVMaze API error while searching for '{title}': {e}", exc_info=True)

        return None

# Initialize a single instance to be used across the application
tvmaze_api = TVMaze()
