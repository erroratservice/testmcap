"""
TVMaze API integration for fetching series and movie data with caching.
"""

import logging
from tvmaze.api import Api
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

class TVMaze:
    """A helper class for interacting with the TVMaze API with MongoDB caching."""
    
    def __init__(self):
        self.api = Api()

    async def search_show(self, title):
        """
        Search for a show by its title, using a cache to avoid redundant API calls.

        :param title: The title of the show to search for.
        :return: A dictionary with the show's data, or None if not found.
        """
        # 1. Check the cache first
        cached_result = await MongoDB.get_tvmaze_cache(title)
        if cached_result:
            LOGGER.info(f"Found '{title}' in TVMaze cache.")
            return cached_result.get('data')

        # 2. If not in cache, query the API
        LOGGER.info(f"'{title}' not in cache. Querying TVMaze API.")
        try:
            shows = self.api.search.shows(title)
            if shows:
                # 3. Save the first result to the cache and return it
                first_show = shows[0]
                await MongoDB.set_tvmaze_cache(title, first_show)
                return first_show
        except Exception as e:
            LOGGER.error(f"TVMaze API error while searching for '{title}': {e}")
        
        return None

    def get_show_details(self, show_id):
        """
        Get detailed information for a specific show by its ID.
        (Note: Caching for this method could also be implemented if needed)
        """
        try:
            return self.api.show.get(show_id)
        except Exception as e:
            LOGGER.error(f"TVMaze API error while getting details for show ID {show_id}: {e}")
        return None

# You can initialize a single instance to be used across the application
tvmaze_api = TVMaze()
