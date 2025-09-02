"""
TVMaze API integration for fetching series and movie data with caching.
"""

import logging
from pytvmaze.tvmaze import TVMaze as PyTVMaze, ShowNotFound
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

class TVMaze:
    """A helper class for interacting with the TVMaze API with MongoDB caching."""
    
    def __init__(self):
        self.api = PyTVMaze()

    def search_show(self, title):
        """
        Search for a show by its title, using a cache to avoid redundant API calls.

        :param title: The title of the show to search for.
        :return: A Show object, or None if not found.
        """
        # 1. Check the cache first
        cached_result = MongoDB.get_tvmaze_cache(title)
        if cached_result:
            LOGGER.info(f"Found '{title}' in TVMaze cache.")
            # The library returns objects, but we can cache the dict representation
            return cached_result.get('data')

        # 2. If not in cache, query the API
        LOGGER.info(f"'{title}' not in cache. Querying TVMaze API.")
        try:
            # get_show is the primary method for searching by name
            show = self.api.get_show(show_name=title)
            if show:
                # 3. Save the show's dictionary representation to the cache
                show_data = vars(show) # Convert object to dict for caching
                MongoDB.set_tvmaze_cache(title, show_data)
                return show_data
        except ShowNotFound:
            LOGGER.warning(f"Show '{title}' not found on TVMaze.")
        except Exception as e:
            LOGGER.error(f"TVMaze API error while searching for '{title}': {e}")
        
        return None

# Initialize a single instance to be used across the application
tvmaze_api = TVMaze()
